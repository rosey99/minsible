minsible
========

Minsible is a python 3.5+ version of Ansible, which is designed to 
run "along side" Ansible as an addon. A such, it depends on Ansible.

This is an effort to make Ansible more usable in the context of an
external automation framework, by making the code thread-safe(r), and 
by doing away with CLI dependence. By default Ansible
wants to create processes/threads, and interact with stdin and stdout.
This presents a set of problems for those of us who wish to automate
Ansible itself, whether using native python threads, concurrent.futures, 
or asyncio. One can still spawn processes instead using stock Ansible, 
but as these are largely IO bound operations, one should get greater 
density of workers using a threaded approach. Other potential benefits
might include:

    *Upstream fetching/decryptiion of artifacts (e.g., host vars, certs)
    *Integration with a workflow system such as Celery Canvas
    *Integration of multiple tools (e.g., terraform, fabric/fybre) in a single process 
    *Use Ansible in support of a stateful, immutable infrastructure model

By default Ansible (much like fabric) will spawn processes, which in 
turn spawn threads for IO wait operations. Additionally, Ansible (short of 
Tower?) wants to run interactively and return results to stdout. Ansible's 
heritage as a command-line tool makes it a challenge to implement via anything 
resembling API access. Minsible is an attempt to address these issues 
and others:

    1. Remove process/thread management and delegate this to the caller
    2. Python 3 only, smaller and more readable, and its been only ten years or so?
    3. Return results to the caller (as json), possibly handled by a callback

No more orchestration or process management, as (IMHO) this should occur 
upstream, and our configuration directives should be just that. Think small.

Similar to another automation project based on Fabric3, I decided that I 
needed/wanted a tool that does only one thing, and to a single host only.
Conceptually, this could be combined with terraform and/or Fabric/Fybre as part 
of state-driven workflow, regardless of where the target systems reside. 
A related project includes the celery runtime configuration and tasks 
required to run Minsible inside a celery worker, which itself can run in a 
docker container.

As far as thread-safety goes, using gevent means that the caller (celery 
in this case) automatically patches the python environment on worker start, 
so at least for now there is no monkey-patching of the stock Ansible 
objects that maintain internal application state. This could change in the 
future. This does not affect operation when run inside a process-pool as opposed 
to a thread-pool. Works both ways. 


Getting Started
---------------

- Install python 3.5+ if it is not installed, or create a python 3.5+ virtual envirnment.

    python3 -m venv env

- Clone or download source directory from git, you may need to install git if not already installed.  

- Activate your virtual environment.

    source env/bin/activate

- Upgrade packaging tools.

    env/bin/pip install --upgrade pip setuptools

- Install the project in editable mode.

    env/bin/pip install -e PATH_TO_MINSIBLE_DIR

- Enter the root directory of your python virtual environment.

    cd env

- Run the test playbook.

    python minsible/minsible_playbook.py localhost minsible/testpb.py

