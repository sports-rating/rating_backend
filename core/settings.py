import os
import sys
import redis
import sentry_sdk

from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from decouple import config
from firebase_admin import initialize_app, credentials

from django.utils.translation import gettext_lazy as _

load_dotenv()

IS_LOCAL: bool = os.getenv("IS_LOCAL", "true").lower() == "true"

if not IS_LOCAL:
    SENTRY_DSN = os.getenv(
        "SENTRY_DSN",
        default="https://021b8769467f3571f152007e3aa870ac@o924416.ingest.us.sentry.io/4509486310883328",
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", default="development"),
        traces_sample_rate=1.0,
        send_default_pii=True,
        # Enable logs to be sent to Sentry
        enable_logs=True,
    )


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(os.path.join(BASE_DIR, "apps"))

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=True, cast=bool)
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

ALLOWED_HOSTS = ["*"]


PACKAGES = [
    "health_check",
    "health_check.db",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "phonenumbers",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "fcm_django",
    "django_celery_beat",
    "storages",
]

BACKEND_APPS = [
    "user",
    "shared",
    "dashboard",
    "sport",
    "education",
    "payment",
    "federation",
    "career",
    "review",
]

INTERNAL_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
INSTALLED_APPS = PACKAGES + BACKEND_APPS + INTERNAL_APPS

MIDDLEWARE = [
    'core.middleware.AdminBasicAuthMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "querycount.middleware.QueryCountMiddleware",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Secutiry headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 3600


CORS_ALLOW_HEADERS = ["*"]
CORS_ORIGIN_ALLOW_ALL = False


CORS_ALLOWED_HEADERS = [
    "content-type",
    "authorization",
    "x-requested-with",
    "accept",
    "origin",
    "accept-language",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5500",
    "https://7srating.uz",
    "https://www.7srating.uz",
    "https://admin.7srating.uz",
    "https://api.7srating.uz",
    "https://dev.7srating.uz",
    "https://dev-admin.7srating.uz",
    "https://dev-api.7srating.uz",
]

CORS_ALLOWED_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "access-control-allow-origin",
    "access-control-allow-credentials",
]

CSRF_TRUSTED_ORIGINS = [
    "https://7srating.uz",
    "https://www.7srating.uz",
    "https://admin.7srating.uz",
    "https://api.7srating.uz",
    "https://dev.7srating.uz",
    "https://dev-admin.7srating.uz",
    "https://dev-api.7srating.uz",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://localhost:5174",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
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
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USERNAME"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST", default="127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", default=5432),
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
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]

LANGUAGES = [
    ("en", _("English")),
    ("uz", _("Uzbek")),
    ("ru", _("Russian")),
]


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
# Directory for static files after collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]


AUTH_USER_MODEL = "user.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # "DEFAULT_PERMISSION_CLASSES": [
    #     "rest_framework.permissions.IsAuthenticated",
    # ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
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

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_HOST = os.getenv("REDIS_HOST", default="localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
redis_connection = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD if REDIS_PASSWORD else None,
    db=0,
)

# Celery settings
CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Tashkent"
CELERY_ENABLE_UTC = False
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_DEFAULT_RATE_LIMIT = "10/m"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# if not IS_LOCAL:
#     S3_MEDIA_BUCKET = os.getenv("S3_MEDIA_BUCKET")
#     S3_STATIC_BUCKET = os.getenv("S3_STATIC_BUCKET")
#     S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
#     S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
#     S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
#     S3_MEDIA_LOCATION = "media"
#     S3_STATIC_LOCATION = "static"

#     STORAGES = {
#         "default": {
#             "BACKEND": "apps.shared.utils.storage_backends.CustomMediaStorage",
#             "OPTIONS": {
#                 "bucket_name": S3_MEDIA_BUCKET,
#                 "location": S3_MEDIA_LOCATION,
#                 "endpoint_url": S3_ENDPOINT_URL,
#                 "access_key": S3_ACCESS_KEY,
#                 "secret_key": S3_SECRET_KEY,
#                 "addressing_style": "path", # virtual",
#                 "default_acl": None,
#             },
#         },
#         "staticfiles": {
#             "BACKEND": "apps.shared.utils.storage_backends.CustomStaticStorage",
#             "OPTIONS": {
#                 "bucket_name": S3_STATIC_BUCKET,
#                 "location": S3_STATIC_LOCATION,
#                 "endpoint_url": S3_ENDPOINT_URL,
#                 "access_key": S3_ACCESS_KEY,
#                 "secret_key": S3_SECRET_KEY,
#                 "addressing_style": "path", # "virtual",
#                 "default_acl": None,
#             },
#         },
#     }
# else:
# Media files (user-uploaded content)
MEDIA_URL = "/media/"  # URL for serving media files
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # Directory for storing media files


# Jazzmin settings for Django Admin
JAZZMIN_SETTINGS = {
    "site_title": "7srating.uz - Admin Panel",
    "site_header": "7srating.uz management",
    "site_brand": "7srating.uz",
    "site_icon": "images/favicon.png",
    # Add your own branding here
    "site_logo": None,
    "welcome_sign": "Welcome to the 7srating.uz",
    # Copyright on the footer
    "copyright": "7srating.uz",
    "user_avatar": None,
    ############
    # Top Menu #
    ############
    # Links to put along the top menu
    "topmenu_links": [
        # Url that gets reversed (Permissions can be added)
        {"name": "receipt.ai", "url": "home", "permissions": ["auth.view_user"]},
        # model admin to link to (Permissions checked against model)
        {"model": "auth.User"},
    ],
    #############
    # Side Menu #
    #############
    # Whether to display the side menu
    "show_sidebar": True,
    # Whether to aut expand the menu
    "navigation_expanded": True,
    # for the full list of 5.13.0 free icon classes
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "users.User": "fas fa-user",
        "auth.Group": "fas fa-users",
        "admin.LogEntry": "fas fa-file",
    },
    # # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-arrow-circle-right",
    #################
    # Related Modal #
    #################
    # Use modals instead of popups
    "related_modal_active": False,
    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    # Uncomment this line once you create the bootstrap-dark.css file
    # "custom_css": "css/bootstrap-dark.css",
    "custom_js": None,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,
    ###############
    # Change view #
    ###############
    "changeform_format": "horizontal_tabs",
    # override change forms on a per modeladmin basis
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-teal",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-info",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "cosmo",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

SUPER_ADMIN_PHONE_NUMBER = os.getenv("SUPER_ADMIN_PHONE_NUMBER")

# SMS configuration via Playmobile
PLAY_MOBILE_URL = os.getenv("PLAY_MOBILE_URL")
PLAY_MOBILE_LOGIN = os.getenv("PLAY_MOBILE_LOGIN")
PLAY_MOBILE_PASSWORD = os.getenv("PLAY_MOBILE_PASSWORD")
VERIFICATION_CODE_EXPIRE = 1 * 60  # 2 minute
SMS_ID_PREFIX = os.getenv("SMS_ID_PREFIX", default="PulseEv")
PLAY_MOBILE_ORIGINATOR = os.getenv("PLAY_MOBILE_ORIGINATOR", default=3700)
VERIFICATION_CODE_MESSAGE_TEMPLATE = (
    "7srating.uz! \n" "Sizning tasdiqlash kodingiz - {verification_code} \n"
)
VERIFICATION_CODE_LENGTH: int = 6


# IMAGE configuration
IMAGE_DIMENSION = (500, 500)
IMAGE_TYPES = [".heic", ".heif", ".jpeg", ".jpg", ".png"]
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Video configuration
VIDEO_TYPES = [".mp4", ".mov", ".avi", ".wmv"]
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

# Document configuration
DOCUMENT_TYPES = [".pdf", ".doc", ".docx", ".txt"]
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB


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
            "propagate": False,  # prevents double logging
        },
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {  # 👈 root logger override
        "handlers": ["console"],
        "level": "WARNING",  # root will only log WARNING+ messages
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

# Firebase
FCM_DJANGO_SETTINGS = {
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": True,
}

cred = credentials.Certificate(BASE_DIR / "sportsrating-firebase.json")

FIREBASE_APP = initialize_app(cred, {"projectId": "sportsrating"})


# Payme
PAYME_ID = os.getenv("PAYME_ID")
PAYME_KEY = os.getenv("PAYME_KEY")
PAYME_TEST_KEY = os.getenv("PAYME_TEST_KEY")
PAYME_ACCOUNT_FIELD = os.getenv("PAYME_ACCOUNT_FIELD")
PAYME_AMOUNT_FIELD = os.getenv("PAYME_AMOUNT_FIELD")
PAYME_ONE_TIME_PAYMENT = os.getenv("PAYME_ONE_TIME_PAYMENT", default="False") == "True"
PAYME_IS_TEST_MODE = os.getenv("PAYME_IS_TEST_MODE", default="False") == "True"
PAYME_RETURN_URL = os.getenv("PAYME_RETURN_URL", default="https://relieved-pika-perfect.ngrok-free.app")

# CLICK
CLICK_SERVICE_ID = int(os.getenv("CLICK_SERVICE_ID"))
CLICK_MERCHANT_ID = int(os.getenv("CLICK_MERCHANT_ID"))
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY")
CLICK_MERCHANT_USER_ID = int(os.getenv("CLICK_MERCHANT_USER_ID"))

# Payment amounts
RESULT_REQUEST_AMOUNT = 2  # sum

# URLs
BACKEND_URL = os.environ.get("BACKEND_URL", default="http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", default="http://localhost:5173")
