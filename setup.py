# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import os
from setuptools import setup

README = """
See the README on `GitHub
<https://github.com/uw-it-aca/django-panopto-scheduler/>`_.
"""

# The VERSION file is created by travis-ci, based on the tag name
version_path = 'scheduler/VERSION'
VERSION = open(os.path.join(os.path.dirname(__file__), version_path)).read()
VERSION = VERSION.replace("\n", "")


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='scheduler',
    version='0.6',
    packages=['scheduler'],
    include_package_data=True,
    install_requires=[
        'Django~=4.2',
        'django-compressor',
        'django-blti~=3.0',
        'django-userservice~=3.2',
        'lxml<5',
        'xmlsec==1.3.13',
        'uw-memcached-clients~=1.0',
        'UW-RestClients-Core~=1.4',
        'UW-RestClients-SWS~=2.4',
        'UW-Restclients-PWS~=2.1',
        'UW-RestClients-GWS~=2.3',
        'UW-RestClients-Canvas~=1.2',
        'UW-RestClients-R25~=0.5',
        'UW-Panopto-Client~=0.3',
        'UW-Django-SAML2~=1.8',
        'Django-SupportTools~=3.6',
        'UW-RestClients-Django-Utils~=2.3',
    ],
    license='Apache License, Version 2.0',
    description='Django app to aid in the scheduling of Panopto recordings in the context of an CollegeNet R25',
    long_description=README,
    url='https://github.com/uw-it-aca/django-panopto-scheduler',
    author="UW-IT T&LS",
    author_email="aca-it@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
