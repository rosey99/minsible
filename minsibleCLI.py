# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

########################################################

import os
import stat
import logging

from ansible.cli import CLI
from ansible.errors import AnsibleError, AnsibleOptionsError

logger = logging.getLogger(__name__)

class MinsibleCLI(CLI):
    ''' 
        This is a minimal CLI implementation that draws on (and inherits from) the
        stock Ansible CLI class. Note that this object is intantiated only to perform
        parsing of arguments and initialization of the base Ansible runtime 
        environment. It has no real "run" method as the playbook(s) are parsed separately
        prior to submittal directly to task_executor. 
        Furthermore, this class instantiates CLI options related to running one 
        Ansible playbook for a single host only, as the calling application is meant 
        to handle processes/threads, gathering results, and firing callbacks. 
        The idea here is that we no longer wish our configuration tool to 
        handle orchestration, inventory, and process execution (among other things), but instead to
        handle task execution only.
        Called with a single list of ansible arguments, and 
        will format the required host argument for ansible if
        it is not already in the required format, e.g.:
            mcli = MinsibleCLI(['localhost'])
        is the same as:
            mcli = MinsibleCLI(['-ilocalhost,'])
        Note that additional args are passed on as is, and this allows for the
        use of --extra-vars, and so on but not all args are supported and 
        the supported args could change. 
    '''
    
    def __init__(self, args: list):

        # We need to look at args, as we can call this with formatted
        #  host args. We may get other args which we don't care about
        #  but to allow for execution via CL with either two positional 
        # args only (hostname, playbook.yml) or with many combinations 
        # of ansible args, or a bit of both, we check here
        args = list(args) 
        hostargs = [ arg for arg in args if arg.startswith('-i') or arg.startswith('--inventory') ]
        if args and not hostargs:
            # No host args from CL, the first arg should be the hostname.
            # If args is empty for some reason, let ansible's cli deal
            # with it below, same if it is --help
            if args[0] in ('-h', '--help'):
                pass # do nothing and pass it to CLI
            else:
                logger.debug('Formatting host arg for host: %s', args[0])
                args[0] = '-i{},'.format(args[0])
        # As ansible CLI expects to be called with a script 
        #  name, this has already been removed by the caller in our case
        #  so we add it back in here. Makes it a little more natural
        #  to instantiate the MinsibleCLI in other code
        args.insert(0, '') # ansible cli hardcodes args=args[1:]
        logger.debug('Initializing with ansible args: %s', args)
        super().__init__(args)

    def parse(self):

        # create parser for CLI options
        parser = CLI.base_parser(
            usage="%prog hostname [options ] playbook.yml",
            connect_opts=True,
            meta_opts=True,
            runas_opts=True,
            subset_opts=False,
            check_opts=True,
            inventory_opts=True,
            runtask_opts=True,
            vault_opts=True,
            fork_opts=False, #changed from stock
            module_opts=True,
            desc="Runs a single Ansible playbook, executing the defined tasks on the single targeted host.",
        )

        self.parser = parser
        super().parse()
        # ansible playbook specific opts, we leave this in for testing
        #parser.remove_option('--list-tasks')
        self.validate_conflicts(runas_opts=True, vault_opts=True, fork_opts=False)
        logger.debug('Parsed CLI options: %s', self.options)

    def run(self):
        """
        Abstract method in base class, we don't use it for minsible.
        """
        pass
        

