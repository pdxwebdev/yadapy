from distutils.core import setup
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES
from distutils.sysconfig import get_python_lib
import os
import sys

setup(
    name = "Yada Project",
    packages=['yadapy'],
    version = '0.1',
    url = 'http://www.yadaproject.com/',
    author = 'Matthew Reynold Vogel',
    author_email = 'matt@yadaproject.com',
    description = 'A high-level Python Web framework that encourages rapid development of distributed social networks.',
    download_url = 'https://github.com/pdxwebdev/yadapy/zipball/master',
    classifiers = [
        'Environment :: Web Environment',
        'Framework :: yadapy',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License',
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
