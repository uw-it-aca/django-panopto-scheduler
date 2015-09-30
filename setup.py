#!/usr/bin/env python

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-panopto-scheduler',
    version='0.5',
    packages=['scheduler'],
    include_package_data=True,
    install_requires = [
        'setuptools',
        'django',
        'django-compressor',
        'django-templatetag-handlebars'
    ],
    dependency_links = [
        'http://github.com/uw-it-aca/django-panopto-client#egg=django_panopto_client',
        'http://github.com/uw-it-aca/django-blti#egg=django_blti',
        'http://github.com/uw-it-aca/uw-restclients#egg=RestClients'
    ],
    license='Apache License, Version 2.0',  # example license
    description='Django app to aid in the scheduling of Panopto recordings in the context of an CollegeNet R25',
    long_description=README,
    url='https://github.com/uw-it-aca/django-panopto-scheduler',
    author = "UW-IT ACA",
    author_email = "mikes@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License', # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
