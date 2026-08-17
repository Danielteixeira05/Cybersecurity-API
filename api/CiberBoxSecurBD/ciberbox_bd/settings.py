from pathlib import Path
import os
import re

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    _env_path = BASE_DIR / '.env'
    if _env_path.is_file():
        load_dotenv(_env_path)
except Exception:
    pass

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


def _parse_pg_url(url):
    m = re.match(
        r'^postgres(?:ql)?://(?P<user>[^:@]+)(?::(?P<pass>[^@]*))?@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<db>[^?]+)',
        url,
    )
    if not m:
        raise ValueError('DATABASE_URL invalida')
    d = m.groupdict()
    return {
        'NAME': d['db'],
        'USER': d['user'],
        'PASSWORD': d['pass'] or '',
        'HOST': d['host'],
        'PORT': d['port'] or '5432',
    }


_estamos_no_vercel = any(os.getenv(v) for v in _vercel_vars)
_SECURE = (
    os.getenv('DJANGO_SECURE_COOKIES', 'False').lower() == 'true'
    or (_estamos_no_vercel and not DEBUG)
)


class VercelCorsMiddleware:
    """Middleware CORS minimo custom (sem dependencias). Suporta wildcard *.vercel.app"""

    def __init__(self, get_response):
        self.get_response = get_response

    def _origin_allowed(self, origin):
        if not origin:
            return False
        if origin in (
            'http://localhost:5173',
            'http://localhost:8443',
            'http://127.0.0.1:5173',
            'http://127.0.0.1:8443',
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost',
            'capacitor://localhost',
            'https://cybersecurity-interface.vercel.app',
            'https://cybersecurity-interface-nu.vercel.app',
            'https://cybersecurity-frontend.vercel.app',
            'https://ciberboxsecur.vercel.app',
            'https://ciberboxsecur-interface.vercel.app',
        ):
            return True
        if origin.endswith('.vercel.app') and (not DEBUG or os.getenv('DJANGO_CORS_ALLOW_VERCEL_WILDCARD', 'True').lower() == 'true'):
            return True
        extra = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS', '')
        if extra and origin in [x.strip() for x in extra.split(',') if x.strip()]:
            return True
        return False

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN')
        allowed = self._origin_allowed(origin)

        if request.method == 'OPTIONS' and allowed:
            from django.http import HttpResponse
            response = HttpResponse(status=204)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD'
            response['Access-Control-Allow-Headers'] = 'Content-Type,X-CSRFToken,Authorization,Accept,Origin,X-Requested-With'
            response['Access-Control-Expose-Headers'] = 'Content-Type,X-CSRFToken'
            response['Access-Control-Max-Age'] = '86400'
            response['Vary'] = 'Origin'
            return response

        response = self.get_response(request)
        if allowed:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Expose-Headers'] = 'Content-Type,X-CSRFToken'
            response['Vary'] = 'Origin'
        return response


INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ciberbox',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'ciberbox_bd.settings.VercelCorsMiddleware',
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

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = _SECURE
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = _SECURE
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_NAME = 'csrftoken'


def _parse_list(raw):
    if not raw:
        return []
    return [x.strip() for x in raw.split(',') if x.strip()]


CSRF_TRUSTED_ORIGINS = _parse_list(os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', ''))

_csrf_defaults = [
    'http://localhost:5173',
    'http://localhost:8443',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:8443',
    'https://cybersecurity-interface.vercel.app',
    'https://cybersecurity-interface-nu.vercel.app',
    'https://cybersecurity-frontend.vercel.app',
    'https://ciberboxsecur.vercel.app',
    'https://ciberboxsecur-interface.vercel.app',
]
for _x in _csrf_defaults:
    if _x not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_x)

if not DEBUG or _SECURE:
    for _wild in ('.vercel.app', '*.vercel.app'):
        if _wild not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_wild)
    for _v in _vercel_vars:
        _val = os.getenv(_v)
        if _val:
            for _proto in ('https://', 'http://'):
                _url = _proto + _val.rstrip('/')
                if _url not in CSRF_TRUSTED_ORIGINS:
                    CSRF_TRUSTED_ORIGINS.append(_url)
    SESSION_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    if os.getenv('DJANGO_CSRF_COOKIE_DOMAIN'):
        CSRF_COOKIE_DOMAIN = os.getenv('DJANGO_CSRF_COOKIE_DOMAIN')
        SESSION_COOKIE_DOMAIN = CSRF_COOKIE_DOMAIN

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

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
