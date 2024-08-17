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
from google.auth.exceptions import DefaultCredentialsError

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from pytz import UTC

import django
from django.utils.encoding import smart_str

#### TODO: Revert when django-countries has been updated to fix the issue
from django_countries.widgets import LazyChoicesMixin

from log_configuration import LOG_CONFIGURATION

LazyChoicesMixin.get_choices = lambda self: self._choices
LazyChoicesMixin.choices = property(LazyChoicesMixin.get_choices, LazyChoicesMixin.set_choices)
#### End monkey patch

django.utils.encoding.smart_text = smart_str

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
ADMINS = [("admin", "test@test.com")]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "secret")

SERVER_ROOT = "https://airsports.no"
CSRF_TRUSTED_ORIGINS = ["https://*.airsports.no", "http://*.127.0.0.1"]
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("MODE") == "dev"
ALLOWED_HOSTS = ["*"]

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

INFLUX_HOST = os.environ.get("INFLUX_HOST", "influx")
INFLUX_PORT = os.environ.get("INFLUX_PORT", 8086)
INFLUX_USER = os.environ.get("INFLUX_USER", "airsport")
INFLUX_PASSWORD = os.environ.get("INFLUX_PASSWORD", "notsecret")
INFLUX_DB_NAME = os.environ.get("INFLUX_DB_NAME", "airsport")

TRACCAR_HOST = os.environ.get("TRACCAR_HOST", "traccar")
TRACCAR_PORT = os.environ.get("TRACCAR_PORT", 8082)
TRACCAR_PROTOCOL = os.environ.get("TRACCAR_PROTOCOL", "http")
TRACCAR_TOKEN = os.environ.get("TRACCAR_TOKEN", "")
TRACCAR_USERNAME = os.environ.get("TRACCAR_USERNAME", "frankose@ifi.uio.no")
TRACCAR_PASSWORD = os.environ.get("TRACCAR_PASSWORD", "password")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
MYSQL_PORT = os.environ.get("MYSQL_PORT", 3306)
MYSQL_USER = os.environ.get("MYSQL_USER", "tracker")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "tracker")
MYSQL_DB_NAME = os.environ.get("MYSQL_DB_NAME", "tracker")
MBTILES_SERVER_URL = os.environ.get("MBTILES_SERVER_URL", "https://mbtiles.airsports.no/")

BUILD_ID = os.environ.get("BUILD_ID", "latest")

MEDIA_LOCATION = os.environ.get("MEDIA_LOCATION", "")

REMOVE_BG_KEY = os.environ.get("REMOVE_BG_KEY", "")

SLACK_DEVELOPMENT_WEBHOOK = os.environ.get("SLACK_DEVELOPMENT_WEBHOOK", "")
SLACK_COMPETITIONS_WEBHOOK = os.environ.get("SLACK_COMPETITIONS_WEBHOOK", "")
SUPPORT_EMAIL = "support@airsports.no"

REDIS_GLOBAL_POSITIONS_KEY = "global_positions"

PURGE_GLOBAL_MAP_INTERVAL = 60
LIVE_POSITION_TRANSMITTER_CACHE_RESET_INTERVAL = 300

# Application definition


INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework.authtoken",
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
    "channels",
    "display.apps.DisplayConfig",
    "firebase.apps.FirebaseConfig",
    "storages",
    "crispy_bootstrap4",
    "location_field.apps.DefaultConfig",
]
if os.environ.get("MODE") != "dev":
    INSTALLED_APPS.append("drf_firebase_auth")

LOCATION_FIELD = {
    "map.provider": "openstreetmap",
    "provider.openstreetmap.max_zoom": 18,
}
PRODUCTION = os.environ.get("MODE") != "dev"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

CRISPY_TEMPLATE_PACK = "bootstrap4"
GUARDIAN_MONKEY_PATCH = False
AUTH_USER_MODEL = "display.MyUser"

EMAIL_FROM = os.environ.get("AUTHEMAIL_DEFAULT_EMAIL_FROM") or "support@airsports.no"
EMAIL_BCC = os.environ.get("AUTHEMAIL_DEFAULT_EMAIL_BCC") or "support@airsports.no"

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
]

ROOT_URLCONF = "live_tracking_map.urls"

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
        "STATS_FILE": os.path.join(BASE_DIR, "..", "webpack-stats-local.json"),
    }
}

# AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # this is default
    "guardian.backends.ObjectPermissionBackend",
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "EXCEPTION_HANDLER": "live_tracking_map.django_exception_handler.exception_handler",
}
if os.environ.get("MODE") != "dev":
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].insert(
        0, "drf_firebase_auth.authentication.FirebaseAuthentication"
    )
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
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {"bucket_name": "airsports-data", "default_acl": "publicRead"},
    },
    "staticfiles": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {"bucket_name": "airsports-static", "default_acl": None, "querystring_auth": False},
    },
}
MEDIA_ROOT_URL = "https://storage.googleapis.com/airsports-data/"
STATIC_URL = "https://storage.googleapis.com/airsports-static/"
# Serve static files locally when developing
if os.environ.get("MODE") == "dev":
    STORAGES["staticfiles"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": "/static", "base_url": "/static/"},
    }
    STATIC_URL = "/static/"


# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

TEMPORARY_FOLDER = "/tmp"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    "/assets",
]

LOGGING = LOG_CONFIGURATION

# celery
# CELERY_BROKER_URL = "redis+socket:///tmp/docker/redis.sock" if PRODUCTION else "redis://redis:6379"
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
# CELERY_RESULT_BACKEND = "django-db"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CELERY_BROKER_URL,
    }
    # "default": {
    #     "BACKEND": "redis_cache.RedisCache",
    #     "LOCATION": [
    #         f"{REDIS_HOST}:{REDIS_PORT}",
    #         # "/tmp/docker/redis.sock" if PRODUCTION else "redis:6379",
    #     ],
    #     "TIMEOUT": None,
    #     "OPTIONS": {
    #         "DB": 1,
    #         "PASSWORD": REDIS_PASSWORD,
    #         "PARSER_CLASS": "redis.connection.HiredisParser",
    #         "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
    #         "CONNECTION_POOL_CLASS_KWARGS": {
    #             "max_connections": 50,
    #             "timeout": 20,
    #         },
    #         "MAX_CONNECTIONS": 1000,
    #         "PICKLE_VERSION": -1,
    #     },
    # },
}

if any(s in sys.argv for s in ("test",)):
    cache.clear()
# CELERY_ACCEPT_CONTENT = ["application/json"]
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = UTC
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULE = {}

ASGI_APPLICATION = "live_tracking_map.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        # "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            # "hosts": ["unix:/tmp/docker/redis.sock" if PRODUCTION else ("redis", 6379)],
            "hosts": [CELERY_BROKER_URL],
            "capacity": 100,  # default 100
            "expiry": 30,  # default 60
        },
    }
}
