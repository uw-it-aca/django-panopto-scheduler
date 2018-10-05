#!/usr/bin/env python

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='scheduler',
    version='0.6',
    packages=['scheduler'],
    include_package_data=True,
    install_requires = [
        'Django==1.11.10',
        'django-compressor',
        'django-templatetag-handlebars',
        'django_mobileesp',
        'django-blti>=1.2.5<2.0',
        'django-userservice>=2.0.1',
        'UW-RestClients-SWS>=1.5.1,<2.0',
        'UW-RestClients-PWS>=1.0.1,<2.0',
        'UW-RestClients-GWS>=1.0,<2.0',
        'UW-RestClients-Canvas>=0.7.2,<1.0',
        'UW-RestClients-R25>=0.1,<1.0',
        'UW-Panopto-Client>=0.1.3,<1.0',
        'UW-RestClients-Django-Utils>=1.1,<2.0',
        'Django-SupportTools>=2.0.3,<3.0',
        'UW-Django-SAML2>=0.4.2',
    ],
    license='Apache License, Version 2.0',
    description='Django app to aid in the scheduling of Panopto recordings in the context of an CollegeNet R25',
    long_description=README,
    url='https://github.com/uw-it-aca/django-panopto-scheduler',
    author = "UW-IT AXDD",
    author_email = "aca-it@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
)
