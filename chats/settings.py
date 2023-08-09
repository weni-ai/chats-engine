"""
Django settings for chats project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
from pathlib import Path

import environ
import sentry_sdk
from django.utils.log import DEFAULT_LOGGING
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environ settings
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    environ.Env.read_env(env_file=ENV_PATH)

env = environ.Env()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


# Application definition

INSTALLED_APPS = [
    # django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # chats apps
    "chats.apps.accounts",
    "chats.apps.contacts",
    "chats.apps.quickmessages",
    "chats.apps.msgs",
    "chats.apps.rooms",
    "chats.apps.sectors",
    "chats.apps.queues",
    "chats.apps.projects",
    "chats.apps.api",
    "chats.apps.dashboard",
    "chats.apps.event_driven",
    "chats.core",
    # third party apps
    "channels",
    "drf_yasg",
    "django_filters",
    "storages",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chats.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "chats.wsgi.application"

ASGI_APPLICATION = "chats.asgi.application"

REDIS_URL = env.str("CHANNEL_LAYERS_REDIS", default="redis://localhost:6379/1")

# channels

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = dict(default=env.db(var="DATABASE_URL"))

# User

AUTH_USER_MODEL = "accounts.User"

ADMIN_USER_EMAIL = env("ADMIN_USER_EMAIL", default="admin@weni.ai")


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="en-us")

TIME_ZONE = env.str("TIME_ZONE", default="America/Maceio")

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")


# Media files

USE_S3 = env.bool("USE_S3", default=False)

MEDIA_ROOT = env.str("MEDIA_ROOT", default="media/")

if USE_S3:
    """
    Upload files to S3 bucket
    """

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")

    AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")

    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

else:
    MEDIA_URL = "/media/"


ENGINE_BASE_URL = env.str(
    "ENGINE_BASE_URL", default="http://localhost:8000"
)  # without '/'


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django Rest Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination." + "LimitOffsetPagination",
    "PAGE_SIZE": env.int("REST_PAGINATION_SIZE", default=20),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_METADATA_CLASS": "chats.apps.api.v1.metadata.Metadata",
}

# Logging

LOGGING = DEFAULT_LOGGING
LOGGING["formatters"]["verbose"] = {
    "format": "%(levelname)s  %(asctime)s  %(module)s "
    "%(process)d  %(thread)d  %(message)s"
}
LOGGING["handlers"]["console"] = {
    "level": "DEBUG",
    "class": "logging.StreamHandler",
    "formatter": "verbose",
}


# Elastic APM

USE_APM = env.bool("USE_APM", default=False)

if USE_APM:
    INSTALLED_APPS.append("elasticapm.contrib.django")

    ELASTIC_APM = {
        "SERVICE_NAME": env("APM_SERVICE_NAME", default="chats-production"),
        "SECRET_TOKEN": env("APM_SECRET_TOKEN"),
        "SERVER_URL": env("APM_SERVER_URL"),
        "ENVIRONMENT": env("APM_SERVICE_ENVIRONMENT", default="production"),
        "DEBUG": env.bool("APM_SERVICE_DEBUG", default=False),
    }

# mozilla-django-oidc

OIDC_ENABLED = env.bool("OIDC_ENABLED", default=False)
if OIDC_ENABLED:
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"].append(
        "mozilla_django_oidc.contrib.drf.OIDCAuthentication"
    )
    INSTALLED_APPS = (*INSTALLED_APPS, "mozilla_django_oidc")
    LOGGING["loggers"]["mozilla_django_oidc"] = {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }
    LOGGING["loggers"]["weni_django_oidc"] = {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }

    OIDC_RP_CLIENT_ID = env.str("OIDC_RP_CLIENT_ID")
    OIDC_RP_CLIENT_SECRET = env.str("OIDC_RP_CLIENT_SECRET")
    OIDC_OP_AUTHORIZATION_ENDPOINT = env.str("OIDC_OP_AUTHORIZATION_ENDPOINT")
    OIDC_OP_TOKEN_ENDPOINT = env.str("OIDC_OP_TOKEN_ENDPOINT")
    OIDC_OP_USER_ENDPOINT = env.str("OIDC_OP_USER_ENDPOINT")
    OIDC_OP_USERS_DATA_ENDPOINT = env.str("OIDC_OP_USERS_DATA_ENDPOINT")
    OIDC_OP_JWKS_ENDPOINT = env.str("OIDC_OP_JWKS_ENDPOINT")
    OIDC_RP_SIGN_ALGO = env.str("OIDC_RP_SIGN_ALGO", default="RS256")
    OIDC_DRF_AUTH_BACKEND = env.str(
        "OIDC_DRF_AUTH_BACKEND",
        default="chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend",
    )
    OIDC_RP_SCOPES = env.str("OIDC_RP_SCOPES", default="openid email")

    # TODO: Set admin permission to Chats client and remove the follow variables
    OIDC_ADMIN_CLIENT_ID = env.str("OIDC_ADMIN_CLIENT_ID")
    OIDC_ADMIN_CLIENT_SECRET = env.str("OIDC_ADMIN_CLIENT_SECRET")


CONNECT_API_URL = env.str("CONNECT_API_URL", default="")
USE_CONNECT_V2 = env.bool("USE_CONNECT_V2", default=False)

FLOWS_API_URL = env.str("FLOWS_API_URL", default="")
USE_WENI_FLOWS = env.bool("USE_WENI_FLOWS", default=False)
FLOWS_TICKETER_TYPE = env.str("FLOWS_TICKETER_TYPE", default="wenichats")
FLOWS_AUTH_TOKEN_RETRIES = env.int(
    "FLOWS_AUTH_TOKEN_RETRIES", default=2
)  # How many times to refresh the flows project auth token and retry the request

# Swagger

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "api_key": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

# CORS CONFIG

CORS_ORIGIN_ALLOW_ALL = True


# Sentry configuration

USE_SENTRY = env.bool("USE_SENTRY", default=False)

if USE_SENTRY:
    sentry_sdk.init(
        dsn=env.str("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        environment=env.str("ENVIRONMENT", default="develop"),
    )


# Query Limiters

PROMETHEUS_AUTH_TOKEN = env.str("PROMETHEUS_AUTH_TOKEN")

ACTIVATE_CALC_METRICS = env.bool("ACTIVATE_CALC_METRICS", default=True)

USE_PROMETHEUS_METRICS = env.bool("USE_PROMETHEUS_METRICS", default=False)

FILE_CHECK_CONTENT_TYPE = env.str(
    "FILE_CHECK_CONTENT_TYPE", default="application/octet-stream"
)
AUDIO_TYPE_TO_CONVERT = env.str("AUDIO_TYPE_TO_CONVERT", default="ogg")
AUDIO_EXTENSION_TO_CONVERT = env.str("AUDIO_EXTENSION_TO_CONVERT", default="ogg")
AUDIO_CODEC_TO_CONVERT = env.str("AUDIO_CODEC_TO_CONVERT", default="libopus")
UNPERMITTED_AUDIO_TYPES = env.list(
    "UNPERMITTED_AUDIO_TYPES",
    default=[
        "webm",
    ],
)

CHATS_FLOWS_TAG = env.str("CHATS_FLOWS_TAG", default="chats")
CHATS_CACHE_TIME = env.int("CHATS_CACHE_TIME", default=1 * 60 * 60)

# Celery

METRICS_CUSTOM_QUEUE = env("METRICS_CUSTOM_QUEUE", default="celery")

USE_CELERY = env.bool("USE_CELERY", default=False)
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Event Driven Architecture configurations

USE_EDA = env.bool("USE_EDA", default=False)

if USE_EDA:
    EDA_CONNECTION_BACKEND = "chats.apps.event_driven.backends.PyAMQPConnectionBackend"
    EDA_CONSUMERS_HANDLE = "chats.apps.event_driven.handle.handle_consumers"

    EDA_BROKER_HOST = env("EDA_BROKER_HOST", default="localhost")
    EDA_VIRTUAL_HOST = env("EDA_VIRTUAL_HOST", default="/")
    EDA_BROKER_PORT = env.int("EDA_BROKER_PORT", default=5672)
    EDA_BROKER_USER = env("EDA_BROKER_USER", default="guest")
    EDA_BROKER_PASSWORD = env("EDA_BROKER_PASSWORD", default="guest")
