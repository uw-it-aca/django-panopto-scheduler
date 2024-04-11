# Panopto Scheduler
A django application to aid in the scheduling of Panopto recordings in the context of an CollegeNet R25

[![Build Status](https://github.com/uw-it-aca/django-panopto-scheduler/workflows/Build%2C%20Test%20and%20Deploy/badge.svg?branch=main)](https://github.com/uw-it-aca/django-panopto-scheduler/actions)
[![Coverage Status](https://coveralls.io/repos/github/uw-it-aca/django-panopto-scheduler/badge.svg?branch=main)](https://coveralls.io/github/uw-it-aca/django-panopto-scheduler?branch=main)

Installation
------------

**Project directory**

Scheduling Interfaces
---------------------

The app supports two scheduling interfaces.

One interface is accessed as an IMS BLTI tool provider. Acccessed via the BLTI, the interface offers scheduling for only the course presented in the BLTI context.

The second interface allows searching for courses and events in R25 within the UW Canvas Support Tools <https://github.com/uw-it-aca/django-supporttools> structure.


Project settings.py
------------------

Below are the settings specific to the scheduler.  Note, though, additional settings will be required for access to student information system as well as Panopto API settings required by the dependent [Panopto Client](https://github.com/uw-it-aca/uw-panopto-client "Panopto Client").

**R25 settings**

    RESTCLIENTS_R25_DAO_CLASS = 'restclients.dao_implementation.r25.Live'
    RESTCLIENTS_R25_HOST = '<R25 Server Name>'
