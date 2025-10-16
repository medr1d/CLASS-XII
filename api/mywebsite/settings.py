import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR.parent, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-this')

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [ 'www.themedium.in', 'pycomp.tech', 'www.pycomp.tech' ]

allowed_hosts_env = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
if allowed_hosts_env:
    ALLOWED_HOSTS.extend([host.strip() for host in allowed_hosts_env.split(',') if host.strip()])

if os.getenv('VERCEL'):
    ALLOWED_HOSTS.extend([
        '.vercel.app',
        'localhost',
        '127.0.0.1',
    ])

if not ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS = ['*']
INSTALLED_APPS = [
    'daphne',  # Must be before django.contrib.staticfiles
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'homepage',
    'auth_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'homepage.ide_middleware.IDEAccessMiddleware',  # IDE access control
]

ROOT_URLCONF = 'mywebsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mywebsite.wsgi.application'
ASGI_APPLICATION = 'mywebsite.asgi.application'

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'  # Use Redis in production
    }
}

# For production, use Redis:
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [os.getenv('REDIS_URL', 'redis://localhost:6379')],
#         },
#     },
# }

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'django_auth'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'disable',  # Changed from 'require' to 'disable' for local development
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')

USE_I18N = True

USE_TZ = True

STATIC_URL = os.getenv('STATIC_URL', '/static/')
STATIC_ROOT = os.path.join(BASE_DIR, os.getenv('STATIC_ROOT', 'staticfiles'))

# STATICFILES_DIRS not needed - Django automatically finds static files in each app's static/ folder

MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
MEDIA_ROOT = os.path.join(BASE_DIR, os.getenv('MEDIA_ROOT', 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 86400))
SESSION_SAVE_EVERY_REQUEST = os.getenv('SESSION_SAVE_EVERY_REQUEST', 'True').lower() == 'true'

# Email Configuration for Zoho Mail with Custom Domain (SSL)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtppro.zoho.in')  # Use smtppro for custom domains
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))  # SSL port
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'  # Disable TLS for SSL
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True').lower() == 'true'   # Enable SSL
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'noreply@themedium.in')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
SERVER_EMAIL = EMAIL_HOST_USER

# Additional email timeout settings for Zoho
EMAIL_TIMEOUT = 30

SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 0))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True

CSRF_TRUSTED_ORIGINS = ['https://www.themedium.in', 'https://pycomp.tech', 'https://www.pycomp.tech']
if os.getenv('VERCEL'):
    CSRF_TRUSTED_ORIGINS.extend([
        'https://*.vercel.app',
        'https://*.themedium.in',
        'https://*.pycomp.tech'
    ])

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
        },
        'auth_app.email_utils': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN', '')

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/django_auth')
