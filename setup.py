import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'ansible>=2.4' 
]

tests_require = []

setup(
    name='minsible',
    version='0.1',
    description='Minimal thread-safe Ansible implementation. Really minimal.',
    author='Richard Rosenberg',
    author_email='rosey.div@gmail.com',
    maintainer='Richard Rosenberg',
    maintainer_email='rosey.div@gmail.com',
    url='https://github.com/rosey99/minsible/',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Other Environment', 
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Software Development',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Software Distribution',
          'Topic :: System :: Systems Administration',
          'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='ansible automation',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    
)
