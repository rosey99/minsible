import sys
import os
import logging
import threading
from multiprocessing import Queue as MPQ
from collections import ChainMap
# Assumes logging is configured upstream, e.g., celery
logger = logging.getLogger(__name__)

from typing import Sequence, Mapping, AnyStr, Any, Union, Callable #generic/abstract types
from typing import Dict, Tuple, List #concrete

# we'll go with a class based approach to 
# wrap the ansible runtime environment
class MinsibleRuntime:
    """
    A simple object to wrap the ansible runtime. It is instantiated for
    each playbook, and contains references to the various ansible objects
    that are required to support playbook execution via the task executor.
    Any passed in args are simply handed off to the ansible CLI class en masse.
    At a minimum, it should be instantiated with a hostname as in:
      minruntime = MinsibleRuntime('hostname')
      ds = open('PATH_TO_PLAYBOOK.yml', 'r').read()
      play_count = minruntime.load_playbook( ds, {'VAR1': 'VAL1', 'VAR2': 'VAL2', ...} ) 
      
    output_map is a dict of callables keyed by ansible module name,
    and will override the default output formatter. See the doc string for
    format_result, below.
    """
    def __init__(self, cliObj: 'minsible.minsibleCLI.MinsibleCLI', output_map: dict={}):
        self.failed = False
        # import all ansible modules here, for late calling/binding
        # we may want to run a thread check and activate gevent
        # or monkey patch before this?
        from ansible.playbook.play_context import PlayContext as PC
        from ansible.plugins.strategy import SharedPluginLoaderObj as SLO
        self.pbcli = cliObj
        ldr, inv, vm = self.pbcli._play_prereqs(self.pbcli.options)
        self.ans_host = inv.get_hosts()[0]
        logger.info('Host: %s', self.ans_host)
        self.ans_loader = ldr #ansible stock loader
        self.ans_inventory = inv #ansible stock inventory mgr
        self.ans_varsmgr = vm #ansible stock variable manager
        #populated in load_playbook
        self.ans_plays = []
        # get a queue instance now, though we don't use it directly
        self.ans_queue = MPQ()
        # get the/a shared plugin/object loader
        self.ans_shared_plugin_loader = SLO()
        # might as well bind to the ansible play context here too
        self.ans_play_context_class = PC
        # initialize variable stack with any ansible parsed values
        self.ans_variables = ChainMap(self.ans_varsmgr.get_vars())
        #set the output callable map
        self.output_map = output_map
    
    def load_playbook(self, playbook: str, varsdict: dict):
        """
        Load the play, this could be from a string, or from a parsed
        json/yaml file. Upstream, this is likely to be fetched from git 
        or some other versioning system.
        """
        if self.ans_plays:
            # out with the old, in with the new - reset the plays
            self.ans_plays = []
        from ansible.playbook.play import Play
        ds = self.ans_loader.load(playbook)
        p = Play()
        for play in ds:
            self.ans_plays.append(p.load(play, self.ans_varsmgr, self.ans_loader))
            logger.debug('Loading play: %s', self.ans_plays[-1].name)
        #update/initialize variable stack - we don't replace these like the plays
        # but simply extend them, at least for the time being as it
        # potentially helps with debugging/testing/auditing the context
        if self.ans_variables:
            self.ans_variables = self.ans_variables.new_child(varsdict)
        else:
            self.ans_variables.update(varsdict)
        return len(self.ans_plays)
    
    def run_all(self, taskvars: dict):
        """
        Run all loaded plays.
        Takes a dict as its sole
        required arg., of the form:
        
        { 'TASK_NAME': {'TASK_VAR1': 'TASK_VAL1', ...}, ... }
        
        During task execution, task variables are stacked
        with the playbook level variables loaded when the playbook is loaded.
        Task level variables temporarily 
        mask play/host level variables and go out of scope 
        immediately following task execution. For the most part, any 
        variables/values used by more than one task should probably
        be passed in when loading the playbook in load_playbook, or 
        passed to run_play for each play.
        """
        reslist = []
        for play in self.ans_plays:
            reslist.extend( self.run_play(play, taskvars) )
        return { self.ans_host.name: reslist }
    
    def run_play(self, play, taskvars: dict):
        """
        Run a play
        To allow for execution of specific plays and
        task variable overrides at the play level.
        Currently not called directly.
        taskvars are described in the docstring for run_all(), 
        above.
        """
        tasklist = play.get_tasks()
        taskvars = self.ans_variables.new_child(taskvars)
        pc = self.ans_play_context_class(play, self.pbcli.options)
        return self.run_tasks(tasklist, taskvars, pc)
        
    def run_tasks(self, tasklist: list, task_vars: dict, ans_play_context):
        """
        Run a list of tasks for a given host and return a dict
        suitable for json serialization of the form:
        [ 
                {
                'modname': modulename, 
                'taskname': taskname, 
                'invocation': ansible_invocation1, 
                'result': ansible_result1
                }, 
                {
                'modname': modulename, 
                'taskname': taskname, 
                'invocation': ansible_invocation2, 
                'result': ansible_result2
                },
                ...
        ]
            
        ansible_result is a dict, and the format is determined by the 
        related module. Handlers are to be invoked in callbacks based
        on the module name.
        
        Stops on task failure, and the result would typically be
        sent to a callback, which may/may not retry or update the system
        state, etc.
        """
        hstname = self.ans_host.name
        #get the task executor
        from ansible.executor.task_executor import TaskExecutor as TE
        reslist = [] 
        rq = self.ans_queue
        slo = self.ans_shared_plugin_loader
        for block in tasklist:
            for task in block:
                modname = task.action
                taskname = task.name
                tr = {} # result
                invocd = {} #invocation or error, we use/replace this to track setup/call errs
                try:
                    logger.info('Executing task: %s --> %s ON HOST: %s', taskname, modname, hstname)
                    tr = TE(self.ans_host, task, task_vars, ans_play_context, None, self.ans_loader, slo, rq).run()
                    # we always use the 'invocation' dict, even when task
                     # setup fails, but we may not make it here
                     # if TE throws an error, so it is initialized outside
                     # this try block, and we simply add it to the result
                    invocd = tr.setdefault('invocation', {})
                except Exception as e: #just grab any exception and mark task as failed
                    logger.warn('Task execution raised an error: %s', str(e))
                    tr['failed'] = True
                    invocd['error'] = str(e) #add a traceback?
                    tr['invocation'] = invocd
                if tr.get('unreachable'):
                    tr['failed'] = True
                #update results list
                reslist.append( self.format_result(task, tr) )
                # stop on failure
                if tr.get('failed'):
                    logger.warn('Task: <%s> using module -->%s failed, exiting.', taskname, modname)
                    break
        return reslist
        
    def format_result(self, task, result):
        """
        Will look for a result formatter by module name, or use
        the default. The default result formatter, does not differentiate
        based on ansible module, and therefore only relies on 
        result data common to all ansible modules. This function will
        be invoked on results where no more specific formatter is
        available based on module/task. 
        Note when defining/calling external
        formatting callables, they must accept the following three
        args: 
              MinsibleRuntime instance,
              the current task instance, 
              the current result as a dict 
        This allows the user defined callable access to the entire
        runtime environment and task attributes along with results 
        during formatting.
        """
        modname = task.action
        taskname = task.name
        form_func = self.output_map.get(modname)
        if form_func:
            return form_func(self, task, result)
        # by default, we move the invocation dict to the top
        # for easier access in our callback
        invocd = result.pop('invocation') #this should always be here
        invocd['modname'] = modname
        invocd['taskname'] = taskname
        return {'invocation': invocd, 'result': result }
            
def runMinsible(host: str, ansvars: Mapping, playbooks: Sequence[str], *opts):
    """
    Automation hook
    """
    from minsible.minsibleCLI import MinsibleCLI as mCLI
    # a bit of a pita, but we need to reconstruct the args 
    # for ansible in a specific way, host, opts, playbooks
    res = {}
    args = [host] + list(opts)
    if playbooks:
        args.extend(playbooks)
    else:
        logger.warn('No playbooks to play, exiting.')
        return {'invocation': {'failed': True, 'errs': ['Missing playbooks arg']}}
    pbcli = mCLI(args)
    pbcli.parse()
    # get the runtime wrapper/instrumentation
    mruntime = MinsibleRuntime(pbcli)
    for playbook in playbooks:
        mruntime.load_playbook(playbook, {})
        r = mruntime.run_all(ansvars)
        for k, v in r.items():
            l = res.setdefault(k, [])
            l.extend(v)
    return res

if __name__ == '__main__':
    ## Really for testing ansible args from the command line
    ##  simple and no real parsing here, we strip off
    ##  the first arg, as typically we instantiate the
    ##  minsibleCLI from a python app
    ## calling from CLI, executes only one playbook
    args = sys.argv[1:]
    pbpath = args[-1] 
    if len(args) > 1:
        try:
            #try and open the file, no parsing/modifying path
            f = open(pbpath, 'r')
            ds = f.read()
        except Exception as e:
            sys.exit('Opening/Reading playbook at <{}> raised an error: {}'.format(pbpath, str(e)))
        finally:
            try:
                f.close()
            except:
                pass
    else:
        sys.exit('You must supply at least a host and playbook path as args:\n  HOSTNAME [ansible_options] path_to_playbook.yml')
    r = runMinsible(args[0], {}, [ds], *args[1:-1])
    # returns a dict, with a single entry as this
    # handles a single host only, writes to a file
    # in the current directory (or tries to)
    import json
    #stime = str(time.time())
    #make a file name with the host, filename, and time
    fname = '_'.join([args[0], pbpath.split('/')[-1], '.json'])
    try:
        f = open(fname, 'w')
        f.write(json.dumps(r, indent=True))
        f.flush()
    except Exception as e:
        # ignore this
        fname = 'File <{}> write failed with error: {}'.format(fname, e)
    finally:
        try:
            f.close()
        except:
            pass
            
    fcount = 0
    ccount = 0
    for k,v in r.items():
        for result in v:
            rd = result['result'] # this is a dict
            if rd.get('failed'):
                fcount += 1
            if rd.get('changed'):
                ccount += 1
        # just print a summary     
        print('Host: ', k)
        print('Task count: ', len(v) )
        print('Fail count: ', fcount )
        print('Changed count: ', ccount)
        print('Results in file: ', fname)
    
