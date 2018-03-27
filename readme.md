# minsible

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

  * Upstream fetching/decryptiion of artifacts (e.g., host vars, certs)
  * Integration with a workflow system such as Celery Canvas
  * Integration of multiple tools (e.g., terraform, fabric/fybre) in a single process 
  * Use Ansible in support of a stateful, immutable infrastructure model

### Design Rationale

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

## Getting Started

For development and testing purposes, follow these steps to get minsible up and 
running on your local machine:

### Prerequisites

- Install python 3.5+ if it is not installed, or create a python 3.5+ virtual envirnment.
  Feel free to choose a more inspired name, here we are using 'env.'

    `python3 -m venv env`

- Enter the root directory of your python virtual environment.

    `cd env`

- Activate your virtual environment.

    `source env/bin/activate`

- Upgrade packaging tools.

    `pip install --upgrade pip setuptools`

- Install the latest Ansible, along with the wheel package for MarkupSafe:

    `pip install wheel ansible`
    
  In a fresh venv, this will likely install a number of Ansible dependencies.
  
### Installing

- Clone or download the minsible source directory from git, you may need to install git if not already installed. 
  To install directly using pip:
  
    `pip install -e git+https://github.com/rosey99/minsible.git#egg=minsible`

## Running the Sample Playbook

- Run the test playbook.

    `python minsible/minsible_playbook.py localhost minsible/testpb.py`

- Or, run it against a real host, using extra vars:

    ```
    python minsible/minsible_playbook.py REAL_HOST -e"{'ansible_ssh_pass':'MY_SSH_PASSWORD', 'ansible_become_pass':'MY_BECOME_PASSWORD'}" minsible/testpb.yml
    ```
    
- Or, update minsible/testvars.yml with your creds, and use a file for variables:

    ```python minsible/minsible_playbook.py REAL_HOST -e"@minsible/testvars.yml" minsible/testpb.yml```


ansible-playbook supports a large number of arguments when invoked from the command line, and the 
test playbook included with minsible is a simple one with only one play, and two tasks:
    
  1. ping
  2. setup (gather facts) 

By default, the '__main__' hook will save the results to a json file, in the directory where 
the command is run. Successive runs overwrite the results by host and playbook name. 
When run inside celery, results are typically persisted to a data store where 
they can be evaluated by a human or used in a callback.

Run from the command line, as in above, the output should look like this:

```
    Host:  dbn11
    Task count:  2
    Fail count:  0
    Changed count:  0
    Results in file:  dbn11_testpb.yml_.json
```

## Built With

* Ansible, obviously ;)

## Authors

* **Richard Rosenberg**

## License

This project is licensed under GNU GPL V3, as this matches the Ansible license. Please see the LICENSE file for details.

## Acknowledgments

* Michael DeHaan, the original author of Ansible
* The Ansible devs and their numerous contributors mean there's a module for everything. . .

