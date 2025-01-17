# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from .base_settings import *
import json

ALLOWED_HOSTS = ['*']

if 'SAML_MOCK' in os.getenv('AUTH', '').split(' '):
    MOCK_SAML_ATTRIBUTES = {
        'uwnetid': ['jfaculty'],
        'affiliations': ['faculty', 'employee', 'member'],
        'eppn': ['jfaculty@washington.edu'],
        'scopedAffiliations': [
            'employee@washington.edu', 'member@washington.edu',
            'faculty@washington.edu'],
        'isMemberOf': ['u_test_group', 'u_test_another_group',
                       'u_acadev_panopto_support'],
    }

INSTALLED_APPS += [
    'compressor',
    'django.contrib.humanize',
    'rc_django',
    'userservice',
    'scheduler.apps.SchedulerConfig',
    'supporttools',
]

MIDDLEWARE += ['userservice.user.UserServiceMiddleware',]

COMPRESS_ENABLED = False if os.getenv("ENV") == "localdev" else True
COMPRESS_OFFLINE = True
COMPRESS_ROOT = '/static/'

COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)

STATICFILES_FINDERS += (
    'compressor.finders.CompressorFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

COMPRESS_PRECOMPILERS += (
    ('text/x-sass', 'pyscss {infile} > {outfile}'),
    ('text/x-scss', 'pyscss {infile} > {outfile}'),
)

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter',
]

TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'supporttools.context_processors.supportools_globals',
    'scheduler.context_processors.event_schedule_buffers',
    'scheduler.context_processors.localdev_mode',
]

SCHEDULER_TIMEZONE = "America/Los_Angeles"

USER_MODULE = 'scheduler.org.uw.user'
COURSES_MODULE = 'scheduler.org.uw.course'
RESERVATIONS_MODULE = 'scheduler.org.uw.reservations'

PANOPTO_ADMIN_GROUP = 'u_acadev_panopto_support'
RESTCLIENTS_ADMIN_GROUP = PANOPTO_ADMIN_GROUP
USERSERVICE_ADMIN_GROUP = PANOPTO_ADMIN_GROUP
PANOPTO_MONITOR_GROUP = 'u_acadev_panopto_monitor'
USERSERVICE_VALIDATION_MODULE = "scheduler.authorization.userservice_validate"
RESTCLIENTS_ADMIN_AUTH_MODULE = "scheduler.authorization.can_view_source_data"

#if not os.getenv("ENV") == "localdev":
#    INSTALLED_APPS += ['rc_django',]
#    RESTCLIENTS_DAO_CACHE_CLASS = 'scheduler.cache.RestClientsCache'

SUPPORTTOOLS_PARENT_APP = "Panopto"
SUPPORTTOOLS_PARENT_APP_URL = "/courses"

#USERSERVICE_OVERRIDE_AUTH_MODULE = "scheduler.authorization.can_override_user"
#RESTCLIENTS_ADMIN_AUTH_MODULE = "scheduler.authorization.can_proxy_restclient"

DETECT_USER_AGENTS = {
    'is_tablet': False,
    'is_mobile': False,
    'is_desktop': True,
}

PANOPTO_API_USER = os.getenv('PANOPTO_API_USER', '')
PANOPTO_API_APP_ID = os.getenv('PANOPTO_API_APP_ID', '')

if os.getenv("ENV", "localdev") == "localdev":
    LTI_DEVELOP_APP = os.getenv("LTI_DEVELOP_APP", '')
    DEBUG = True
else:
    PANOPTO_API_TOKEN = os.getenv('PANOPTO_API_TOKEN')
    PANOPTO_SERVER = os.getenv('PANOPTO_SERVER')
    DEBUG = (os.getenv("ENV", "UNSET") == "dev")
    CSRF_TRUSTED_ORIGINS = ['https://' + os.getenv('CLUSTER_CNAME')]

# dial back suds super-verbose telemetry
LOGGING['loggers']['suds'] =  {
    'handlers': ['stdout', 'stderr'],
    'level': 'ERROR'
}
