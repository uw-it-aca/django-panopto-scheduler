from .base_settings import *

ALLOWED_HOSTS = ['*']

if os.getenv('AUTH', 'NONE') == 'SAML_MOCK':
    MOCK_SAML_ATTRIBUTES = {
        'uwnetid': ['jfaculty'],
        'affiliations': ['faculty', 'employee', 'member'],
        'eppn': ['jfacult@washington.edu'],
        'scopedAffiliations': [
            'employee@washington.edu', 'member@washington.edu'],
        'isMemberOf': ['u_test_group', 'u_test_another_group',
                       'u_acadev_panopto_support'],
    }

INSTALLED_APPS += [
    'django_prometheus',
    'compressor',
    'django.contrib.humanize',
    'userservice',
    'scheduler.apps.SchedulerConfig',
    'blti',
    'supporttools',
]

MIDDLEWARE = ['django_prometheus.middleware.PrometheusBeforeMiddleware'] +\
             MIDDLEWARE +\
             ['userservice.user.UserServiceMiddleware',
              'django_prometheus.middleware.PrometheusAfterMiddleware']

if not os.getenv("ENV") == "localdev":
    DATABASES['default']['ENGINE'] = 'django_prometheus.db.backends.postgresql'

COMPRESS_ENABLED = True
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

USERSERVICE_VALIDATION_MODULE = "scheduler.userservice_validation.validate"

PANOPTO_ADMIN_GROUP = 'u_acadev_panopto_support'
RESTCLIENTS_ADMIN_GROUP = PANOPTO_ADMIN_GROUP
USERSERVICE_ADMIN_GROUP = PANOPTO_ADMIN_GROUP

AUTHZ_GROUP_BACKEND = 'authz_group.authz_implementation.uw_group_service.UWGroupService'

#if not os.getenv("ENV") == "localdev":
#    INSTALLED_APPS += ['rc_django',]
#    RESTCLIENTS_DAO_CACHE_CLASS = 'scheduler.cache.RestClientsCache'

RESTCLIENTS_DEFAULT_TIMEOUT = 3

SUPPORTTOOLS_PARENT_APP = 'Panopto'

#USERSERVICE_OVERRIDE_AUTH_MODULE = "scheduler.authorization.can_override_user"
#RESTCLIENTS_ADMIN_AUTH_MODULE = "scheduler.authorization.can_proxy_restclient"

DETECT_USER_AGENTS = {
    'is_tablet': False,
    'is_mobile': False,
    'is_desktop': True,
}

if not os.getenv("ENV", "localdev") == "localdev":
    PANOPTO_API_USER = os.getenv('PANOPTO_API_USER')
    PANOPTO_API_APP_ID = os.getenv('PANOPTO_API_APP_ID')
    PANOPTO_API_TOKEN = os.getenv('PANOPTO_API_TOKEN')
    PANOPTO_SERVER = os.getenv('PANOPTO_SERVER')

# BLTI consumer key:secret pairs
LTI_CONSUMERS = {k: v for k, v in [s.split('=') for s in os.getenv(
    "LTI_CONSUMERS", "").split(',') if len(s)]}

# BLTI session object encryption values
BLTI_AES_KEY = os.getenv('BLTI_AES_KEY', '').encode()
BLTI_AES_IV = os.getenv('BLTI_AES_IV', '').encode()


DEBUG = True if os.getenv('ENV', 'localdev') == "localdev" else False
