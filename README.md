# Panopto Scheduler
A django application to aid in the scheduling of Panopto recordings in the context of an CollegeNet R25

[![Build Status](https://travis-ci.com/uw-it-aca/django-panopto-scheduler.svg?branch=master)](https://travis-ci.com/uw-it-aca/django-panopto-scheduler)
[![Coverage Status](https://coveralls.io/repos/github/uw-it-aca/django-panopto-scheduler/badge.svg?branch=master)](https://coveralls.io/github/uw-it-aca/django-panopto-scheduler?branch=master)


Installation
------------

**Project directory**

Install django-panopto-client in your project.

    $ cd [project]
    $ pip install -e git+https://github.com/uw-it-aca/django-panopto-scheduler/#egg=django_panopto_scheduler

Scheduling Interfaces
---------------------

The app supports two scheduling interfaces.

One interface is accessed as an IMS BLTI tool provider. Acccessed via the BLTI, the interface offers scheduling for only the course presented in the BLTI context.

The second interface allows searching for courses and events in R25 within the UW Canvas Support Tools <https://github.com/uw-it-aca/canvas-support-tools> structure.


Project settings.py
------------------

Below are the settings specific to the scheduler.  Note, though, additional settings will be required for access to student information system as well as Panopto API settings required by the dependent [Django Panopto Client](https://github.com/uw-it-aca/django-panopto-client "Panopto Client").

**R25 settings**

    RESTCLIENTS_R25_DAO_CLASS = 'restclients.dao_implementation.r25.Live'
    RESTCLIENTS_R25_HOST = '<R25 Server Name>'
