from pathlib import Path
import os
import re
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'alterar-esta-chave-em-producao')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

_vercel_vars = ['VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL', 'NEXT_PUBLIC_VERCEL_URL']
for _v in _vercel_vars:
    _val = os.getenv(_v)
    if _val:
        _clean = _val.replace('https://', '').replace('http://', '').split('/')[0]
        if _clean and _clean not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_clean)

if os.getenv('DJANGO_ALLOW_VERCEL_WILDCARD', str(not DEBUG)).lower() == 'true':
    ALLOWED_HOSTS.extend([h for h in ['.vercel.app'] if h not in ALLOWED_HOSTS])

if DEBUG:
    ALLOWED_HOSTS = list(set(ALLOWED_HOSTS + ['*']))

def _parse_pg_url(url: str) -> dict:
    m = re.match(
        r'^postgres(?:ql)?://(?P<user>[^:@]+)(?::(?P<pass>[^@]*))?@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<db>[^?]+)',
        url,
    )
    if not m:
        raise ValueError(f'DATABASE_URL invalida: {url[:30]}...')
    d = m.groupdict()
    return {
        'NAME': d['db'],
        'USER': d['user'],
        'PASSWORD': d['pass'] or '',
        'HOST': d['host'],
        'PORT': d['port'] or '5432',
    }
    
INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ciberbox',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ciberbox_bd.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'ciberbox' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'ciberbox.context_processors.utilizador_atual',
            ],
        },
    },
]

WSGI_APPLICATION = 'ciberbox_bd.wsgi.application'


_db_url = os.getenv('DATABASE_URL')
if _db_url:
    _p = _parse_pg_url(_db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _p['NAME'],
            'USER': _p['USER'],
            'PASSWORD': _p['PASSWORD'],
            'HOST': _p['HOST'],
            'PORT': _p['PORT'],
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
                'sslmode': os.getenv('POSTGRES_SSLMODE', 'require'),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'ciberbox_bd'),
            'USER': os.getenv('POSTGRES_USER', 'ciberbox_user'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'ciberbox_password'),
            'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
                'sslmode': os.getenv('POSTGRES_SSLMODE', 'prefer'),
            },
        }
    }

LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Europe/Lisbon'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'ciberbox' / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# As sessoes ficam num cookie assinado e nao exigem tabelas do ORM.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.getenv('DJANGO_SECURE_COOKIES', 'False').lower() == 'true'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

LOGIN_URL = '/login/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {asctime} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
}
