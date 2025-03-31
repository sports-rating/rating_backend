import os
import sys
from pathlib import Path
from datetime import timedelta

from decouple import config

from django.utils.translation import gettext_lazy as _


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(os.path.join(BASE_DIR, "apps"))

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = ["*"]


PACKAGES = [
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "phonenumbers",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "fcm_django",
    "django_celery_beat"
]

BACKEND_APPS = [
    "user",
    "shared",
    "dashboard",
    "sport",
    "education",
    "payment",
]

INTERNAL_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
INSTALLED_APPS = PACKAGES + BACKEND_APPS + INTERNAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "querycount.middleware.QueryCountMiddleware",
]

REDIS_DB: int = config("REDIS_DB", default=0, cast=int)
REDIS_HOST: str = config("REDIS_HOST", default="localhost")
REDIS_PASSWORD: str = config("REDIS_PASSWORD", default=None)
REDIS_PORT: int = config("REDIS_PORT", default=6379, cast=int)

REDIS_CREDENTIALS: dict[str, str] = {
    "db": REDIS_DB,
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "password": REDIS_PASSWORD,
    "decode_responses": True,
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Secutiry headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 3600


CORS_ALLOW_HEADERS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True # extra added

CSRF_TRUSTED_ORIGINS = [
    "https://*.7srating.uz",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "https://*.7srating.uz",
    "https://7srating.uz",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates']
        ,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME"),
        "USER": config("DATABASE_USERNAME"),
        "PASSWORD": config("DATABASE_PASSWORD"),
        "HOST": config("DATABASE_HOST", default="127.0.0.1"),
        "PORT": config("DATABASE_PORT", default=5432, cast=int),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = ["locale"]

LANGUAGES = [
    ("en", _("English")),
    ("uz", _("Uzbek")),
    ("ru", _("Russian")),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
# Directory for static files after collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files (user-uploaded content)
MEDIA_URL = "/media/"  # URL for serving media files
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # Directory for storing media files

AUTH_USER_MODEL = "user.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DEFAULT_THROTTLE_RATES": {"anon": "5/min"},
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sport Rating API",
    "DESCRIPTION": "sport-rating.uz swagger docs (rest api service)",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SCHEMA_PATH_PREFIX": r"/api/",
}

# SMS configuration via Playmobile

PLAY_MOBILE_URL = config("PLAY_MOBILE_URL")
PLAY_MOBILE_LOGIN = config("PLAY_MOBILE_LOGIN")
PLAY_MOBILE_PASSWORD = config("PLAY_MOBILE_PASSWORD")
VERIFICATION_CODE_EXPIRE = 1 * 60  # 2 minute
SMS_ID_PREFIX = config("SMS_ID_PREFIX", default="PulseEv")
SMS_ORIGINATOR = config("SMS_ORIGINATOR", default=3700)
VERIFICATION_CODE_MESSAGE_TEMPLATE = (
    "Gigawat.uz! \n" "Sizning tasdiqlash kodingiz - {verification_code}\ndaORdCftPDL"
)
VERIFICATION_CODE_LENGTH: int = 6


# IMAGE configuration

IMAGE_DIMENSION = (500, 500)
IMAGE_TYPES = ["heic", "heif", "jpeg", "jpg", "png"]

MAX_IMAGE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default-formatter": {
            "format": "[%(levelname)s] %(asctime)s %(filename)s:%(lineno)s:%(funcName)s: %(message)s",
            "datefmt": "%m/%d/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default-formatter",
        },
    },
    "loggers": {
        "api": {
            "level": "DEBUG",
            "handlers": ["console"],
        },
    },
}

# QueryCount
QUERYCOUNT = {
    'THRESHOLDS': {
        'MEDIUM': 50,
        'HIGH': 200,
        'MIN_TIME_TO_LOG':0,
        'MIN_QUERY_COUNT_TO_LOG':1
    },
    'IGNORE_REQUEST_PATTERNS': [r'^/admin/', r'^/favicon.ico'],
    'IGNORE_SQL_PATTERNS': [],
    'DISPLAY_DUPLICATES': 0,
    'RESPONSE_HEADER': 'X-DjangoQueryCount-Count'
}