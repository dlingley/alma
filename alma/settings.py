import os
from fnmatch import fnmatch
from django.core.urlresolvers import reverse_lazy
from django.contrib.messages import constants as messages
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP, AUTHENTICATION_BACKENDS
from varlet import variable


#
# Path constructors
#

DJANGO_DIR = lambda *path: os.path.normpath(os.path.join(os.path.dirname(__file__), *path))
BASE_DIR = lambda *path: DJANGO_DIR("../", *path)

#
# System and Debugging
#

# SECURITY WARNING: don't run with debug turned on in production!
# make this True in dev
DEBUG = variable("DEBUG", default=False)
TEMPLATE_DEBUG = DEBUG
DEFAULT_FROM_EMAIL = SERVER_EMAIL = 'no-reply@pdx.edu'
# allow the use of wildcards in the INTERAL_IPS setting
class IPList(list):
    # do a unix-like glob match
    # E.g. '192.168.1.100' would match '192.*'
    def __contains__(self, ip):
        return any(fnmatch(ip, ip_pattern) for ip_pattern in self)
INTERNAL_IPS = IPList(['10.*', '192.168.*'])
ADMINS = variable("ADMINS", default=[("Matt", "foo@example.com")])
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = variable("SECRET_KEY", os.urandom(64).decode("latin1"))

#
# Host info
#

# This hostname is used to construct URLs. It would be something like
# "example.com" in production. This is used to construct the
# SESSION_COOKIE_DOMAIN and ALLOWED_HOSTS, so make sure it is correct
HOSTNAME = variable("HOSTNAME", default="10.0.0.10.xip.io:8000")
# we construct the SESSION_COOKIE_DOMAIN based on the hostname. We prepend a
# dot so the cookie is set for all subdomains
SESSION_COOKIE_DOMAIN = HOSTNAME.split(":")[0]
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN]

#
# Test Stuff
#

# we use a custom test runner to set some custom settings
TEST_RUNNER = 'alma.testrunner.TestRunner'
# are we in test mode? This gets overridden in the test runnner
TEST = False

#
# Auth Stuff
#

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = reverse_lazy("login")
LOGIN_REDIRECT_URL = reverse_lazy("users-home")
# uncomment to use CAS. You need to update requirements.txt too
CAS_SERVER_URL = 'https://sso.pdx.edu/cas/'
AUTHENTICATION_BACKENDS += ('alma.users.backends.PSUBackend',)

LDAP = {
    'default': {
        'host': "ldap://ldap-login.oit.pdx.edu",
        'search_dn': 'dc=pdx,dc=edu'
    }
}

#
# Celery
#

# CELERY_ACKS_LATE = True
# CELERY_RESULT_BACKEND = 'amqp'
# The celery broker URL 'amqp://guest:guest@localhost//'
# BROKER_URL = variable("BROKER_URL", default='amqp://guest:guest@localhost//')


#
# Email
#

# In production, use something like 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = variable("EMAIL_BACKEND", default='django.core.mail.backends.console.EmailBackend')

#
# DB
#

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'alma',
        # the default is fine for dev
        'USER': variable("DB_USER", default='root'),
        # the default is fine for dev
        'PASSWORD': variable("DB_PASSWORD", default=''),
        # the default is fine for dev
        'HOST': variable("DB_HOST", default=''),
        'PORT': '',
        'ATOMIC_REQUESTS': True,
    },
}

LOGGING_CONFIG = 'arcutils.logging.basic'

#
# UI
#

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

ITEMS_PER_PAGE = 100


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    # auth doesn't have to be installed to use the django auth stuff. It adds a
    # bunch of annoying group and permission tables
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'permissions',
    'arcutils',
    'alma.users',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cloak.middleware.CloakMiddleware',
    # 'djangocas.middleware.CASMiddleware',
)

ROOT_URLCONF = 'alma.urls'

WSGI_APPLICATION = 'alma.wsgi.application'

#
# I18n and Time
#

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = False
USE_L10N = False
USE_TZ = True


#
# Static files and media
#

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    DJANGO_DIR("static"),
)
STATIC_ROOT = BASE_DIR("static")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR("media")


#
# Templates
#

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    DJANGO_DIR("templates"),
)
