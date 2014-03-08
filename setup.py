from distutils.core import setup
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES
from distutils.sysconfig import get_python_lib
from setuptools import setup, find_packages
import os
import sys

setup(
    name = "yadapy",
    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*', 'pymongo', 'pycrypto',]),
    version = '0.1.1.1',
    url = 'http://www.yadaproject.com/',
    author = 'Matthew Reynold Vogel',
    author_email = 'matt@yadaproject.com',
    description = 'A framework for building distributed social networking applications and mobile-centric single sign-on.',
    download_url = 'https://github.com/pdxwebdev/yadapy/zipball/master',
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
   ],
)
