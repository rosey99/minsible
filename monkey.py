import threading
import sys
import logging 

# Assumes logging is conigured elsewhere, e.g., celery
logger = logging.getLogger(__name__)

THREAD_CHECK = False #duped, for keeping internal state

from collections import UserDict
import importlib

class LocalDict(UserDict, threading.local):
    """
    A helper class for thread local caching
    """
    pass
    
MODULE_CACHE = LocalDict()
PATH_CACHE = LocalDict()
PLUGIN_PATH_CACHE = LocalDict()

def thread_monkey():
    """
    Ansible monkey-patching for thread safe environment and plugin cache.
    S/B called first, possibly conditionally, returns True on success
    or False on failure/error. 
    We probably only need the module cache, but we will create
    local dicts for all globally (module level) cached state
    variables.
    """
    #now we set the lock 
    LCK = threading.Lock()
    logger.debug('In thread monkey')
    try:
        LCK.acquire(blocking=True, timeout=1)
        global THREAD_CHECK
        if THREAD_CHECK: #first thread through will reset global
            # state first then thread handling
            m = importlib.import_module('ansible.plugins')
            mc = m.MODULE_CACHE
            # we only want to do this once, so check just in case
            # since global state can be modifed externally
            if mc is not MODULE_CACHE: 
                logger.info('Swapping out stock ansible plugins for thread-safety hack/test')
                m.MODULE_CACHE = MODULE_CACHE
                m.PATH_CACHE = PATH_CACHE
                m.PLUGIN_PATH_CACHE = PLUGIN_PATH_CACHE
            else:
                logger.info('Monkeys are already set up, you should never see this!')
        else:
            logger.info('Not swapping out stock ansible plugins :)')   
        THREAD_CHECK = False
        LCK.release()
        return True

    except Exception as e:
        # may want to just abort here as we should not fail here, and
        # we should not even get here unless we are running in a thread
        # other than the main thread
        logger.warn('Exception acquiring ansible (thread) plugins:\n', str(e))
        return False

