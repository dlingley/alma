# SECURITY WARNING: don't run with debug turned on in production!
# make this True in dev
DEBUG = True

ADMINS = [('Matt', 'foo@example.com')]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "hi"

# This hostname is used to construct URLs. It would be something like
# "example.com" in production. This is used to construct the
# SESSION_COOKIE_DOMAIN and ALLOWED_HOSTS, so make sure it is correct
HOSTNAME = '10.0.0.5:8000'

# In production, use something like 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# the default is fine for dev
DB_USER = 'root'

# the default is fine for dev
DB_PASSWORD = ''

# the default is fine for dev
DB_HOST = ''
