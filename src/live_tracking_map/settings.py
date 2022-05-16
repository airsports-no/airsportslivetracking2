"""
Django settings for live_tracking_map project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import os
import sys
from pathlib import Path
from django.core.cache import cache

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from pytz import UTC

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
ADMINS = [("admin", "test@test.com")]
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
#
# sentry_sdk.init(
#     dsn="https://de23c507c2c14ccba388a15e5dbe1df6@o568590.ingest.sentry.io/5713793",
#     integrations=[DjangoIntegration()],
#     # Set traces_sample_rate to 1.0 to capture 100%
#     # of transactions for performance monitoring.
#     # We recommend adjusting this value in production.
#     traces_sample_rate=1.0,
#     # If you wish to associate users to errors (assuming you are using
#     # django.contrib.auth) you may enable sending PII data.
#     send_default_pii=True,
# )
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "a()!xe(&n4@i(hrd=w*xs&v4f^t&7rw4z4(uz&8&2tuy9216j9"

SERVER_ROOT = "https://airsports.no"
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("MODE") == "dev"
ALLOWED_HOSTS = ["*"]

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

INFLUX_HOST = os.environ.get("INFLUX_HOST", "influx")
INFLUX_PORT = os.environ.get("INFLUX_PORT", 8086)
INFLUX_USER = os.environ.get("INFLUX_USER", "airsport")
INFLUX_PASSWORD = os.environ.get("INFLUX_PASSWORD", "notsecret")
INFLUX_DB_NAME = os.environ.get("INFLUX_DB_NAME", "airsport")

TRACCAR_HOST = os.environ.get("TRACCAR_HOST", "traccar")
TRACCAR_PORT = os.environ.get("TRACCAR_PORT", 8082)
TRACCAR_PROTOCOL = os.environ.get("TRACCAR_PROTOCOL", "http")
TRACCAR_TOKEN = os.environ.get("TRACCAR_TOKEN", "")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
MYSQL_PORT = os.environ.get("MYSQL_PORT", 3306)
MYSQL_USER = os.environ.get("MYSQL_USER", "tracker")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "tracker")
MYSQL_DB_NAME = os.environ.get("MYSQL_DB_NAME", "tracker")

STORAGE_ACCOUNT_KEY = os.environ.get("STORAGE_ACCOUNT_KEY", "")
STORAGE_ACCOUNT_SECRET = os.environ.get("STORAGE_ACCOUNT_SECRET", "")
AZURE_ACCOUNT_NAME = os.environ.get("AZURE_ACCOUNT_NAME", "")
MEDIA_LOCATION = os.environ.get("MEDIA_LOCATION", "")

REMOVE_BG_KEY = os.environ.get("REMOVE_BG_KEY", "")

SLACK_DEVELOPMENT_WEBHOOK = os.environ.get("SLACK_DEVELOPMENT_WEBHOOK", "")

REDIS_GLOBAL_POSITIONS_KEY = "global_positions"
# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework.authtoken",
    # "django_celery_beat",
    "django_celery_results",
    "timezone_field",
    "webpack_loader",
    "bootstrap4",
    "drf_yasg",
    "solo",
    "guardian",
    "django_countries",
    "formtools",
    "phonenumber_field",
    "qr_code",
    "crispy_forms",
    'django_jenkins',
    "google_analytics",
    "channels",
    "display.apps.DisplayConfig",
    "firebase.apps.FirebaseConfig",
    "multiselectfield",
    'storages',
    #### Wagtail
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail.core',
    'wagtail.api.v2',
    'modelcluster',
    'taggit',
    ####
    'wiki',
]
if os.environ.get("MODE") != "dev":
    INSTALLED_APPS.append("drf_firebase_auth")

PRODUCTION = os.environ.get("MODE") != "dev"

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

CRISPY_TEMPLATE_PACK = "bootstrap4"
GUARDIAN_MONKEY_PATCH = False
AUTH_USER_MODEL = "display.MyUser"

EMAIL_FROM = os.environ.get("AUTHEMAIL_DEFAULT_EMAIL_FROM") or "tracking@airsports.no"
EMAIL_BCC = os.environ.get("AUTHEMAIL_DEFAULT_EMAIL_BCC") or "tracking@airsports.no"

EMAIL_HOST = os.environ.get("AUTHEMAIL_EMAIL_HOST") or ""
EMAIL_PORT = os.environ.get("AUTHEMAIL_EMAIL_PORT") or 587
EMAIL_HOST_USER = os.environ.get("AUTHEMAIL_EMAIL_HOST_USER") or "<YOUR EMAIL_HOST_USER HERE>"
EMAIL_HOST_PASSWORD = os.environ.get("AUTHEMAIL_EMAIL_HOST_PASSWORD") or "<YOUR EMAIL_HOST_PASSWORD HERE>"
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = EMAIL_FROM

DRF_FIREBASE_AUTH = {
    "FIREBASE_SERVICE_ACCOUNT_KEY": "/secret/airsports-firebase-admin.json",
    "FIREBASE_AUTH_EMAIL_VERIFICATION": True,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "live_tracking_map.middleware.HandleKnownExceptionsMiddleware",
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
    # 'google_analytics.middleware.GoogleAnalyticsMiddleware',
]
JENKINS_TASKS = [  # executed on the apps in PROJECT_APPS
    'django_jenkins.tasks.run_pep8'
]

WAGTAIL_SITE_NAME = 'Airsports Live Tracking'

WAGTAILSEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'wagtail.search.backends.database',
    }
}

ROOT_URLCONF = "live_tracking_map.urls"

CELERY_IMPORTS = "google_analytics.tasks"
LOGOUT_REDIRECT_URL = "/"
LOGIN_REDIRECT_URL = "/"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "live_tracking_map.wsgi.application"

WEBPACK_LOADER = {
    "DEFAULT": {
        "BUNDLE_DIR_NAME": "bundles/local/",  # end with slash
        "STATS_FILE": "/webpack-stats-local.json",
    }
}

# AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # this is default
    "guardian.backends.ObjectPermissionBackend",
)

GOOGLE_ANALYTICS = {
    "google_analytics_id": "UA-12923426-5",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "EXCEPTION_HANDLER": "live_tracking_map.django_exception_handler.exception_handler",
}
if os.environ.get("MODE") != "dev":
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].insert(0,
                                                            "drf_firebase_auth.authentication.FirebaseAuthentication")
# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

IS_UNIT_TESTING = any(s in sys.argv for s in ("test", "jenkins"))

# if IS_UNIT_TESTING:  # Use sqlite3 when running tests
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#         }
#     }
# else:
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": MYSQL_DB_NAME,
        "USER": MYSQL_USER,
        "PASSWORD": MYSQL_PASSWORD,
        "HOST": MYSQL_HOST,
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
# MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/'
AZURE_ACCOUNT_KEY = STORAGE_ACCOUNT_SECRET
AZURE_CONTAINER = MEDIA_LOCATION

TEMPORARY_FOLDER = "/tmp"

STATIC_URL = "/static/"
STATIC_ROOT = "/static"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    "/assets",
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(name)-15s: %(funcName)-15s %(levelname)-8s %(message)s",
            "datefmt": "%d/%m/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "standard"},
        # "file": {
        #     "level": "DEBUG",
        #     "class": "logging.handlers.WatchedFileHandler",
        #     "filename": "/logs/airsports.log",
        #     "formatter": "standard",
        # },
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "": {"handlers": ["console"], "level": "DEBUG"},
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "websocket": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "asyncio": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "aioredis": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "channels_redis": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "daphne": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "matplotlib": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "shapely": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "PIL": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# celery
# CELERY_BROKER_URL = "redis+socket:///tmp/docker/redis.sock" if PRODUCTION else "redis://redis:6379"
CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
CELERY_RESULT_BACKEND = "django-db"

CACHES = {
    "default": {
        "BACKEND": "redis_cache.RedisCache",
        "LOCATION": [
            f"{REDIS_HOST}:{REDIS_PORT}",
            # "/tmp/docker/redis.sock" if PRODUCTION else "redis:6379",
        ],
        "TIMEOUT": None,
        "OPTIONS": {
            "DB": 1,
            "PASSWORD": REDIS_PASSWORD,
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "timeout": 20,
            },
            "MAX_CONNECTIONS": 1000,
            "PICKLE_VERSION": -1,
        },
    },
}

if any(s in sys.argv for s in ("test",)):
    cache.clear()
# CELERY_ACCEPT_CONTENT = ["application/json"]
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = UTC
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = False
CELERY_BEAT_SCHEDULE = {}

ASGI_APPLICATION = "live_tracking_map.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # "hosts": ["unix:/tmp/docker/redis.sock" if PRODUCTION else ("redis", 6379)],
            "hosts": [CELERY_BROKER_URL],
            "capacity": 100,  # default 100
            "expiry": 30,  # default 60
        },
    }
}
