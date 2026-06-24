from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = os.getenv("DEBUG", "True").lower() in {"true", "1", "yes"}

CORS_ALLOW_ALL_ORIGINS = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "src.Infrastructure.Identity",
    "src.Infrastructure.History",
    "src.Presentation",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "src.Presentation.root_urls"

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

WSGI_APPLICATION = "src.Presentation.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "wslny"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "identity.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "60/minute",
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

AI_GRPC_HOST = os.getenv("AI_GRPC_HOST", "ai-service")
AI_GRPC_PORT = int(os.getenv("AI_GRPC_PORT", "50052"))
AI_GRPC_TIMEOUT_SECONDS = float(os.getenv("AI_GRPC_TIMEOUT_SECONDS", "120.0"))

ROUTING_GRPC_HOST = os.getenv("ROUTING_GRPC_HOST", "routing-engine")
ROUTING_GRPC_PORT = int(os.getenv("ROUTING_GRPC_PORT", "50051"))
ROUTING_GRPC_TIMEOUT_SECONDS = float(os.getenv("ROUTING_GRPC_TIMEOUT_SECONDS", "120.0"))

ROUTE_BUS_FARE_PER_RIDE = float(os.getenv("FARE_BUS_PER_RIDE", "20"))
ROUTE_MICROBUS_FARE_PER_RIDE = float(os.getenv("FARE_MICROBUS_PER_RIDE", "10"))
ROUTE_METRO_FARE_TIERS = [
    (9, float(os.getenv("FARE_METRO_UP_TO_9", "8"))),
    (16, float(os.getenv("FARE_METRO_UP_TO_16", "10"))),
    (23, float(os.getenv("FARE_METRO_UP_TO_23", "15"))),
    (39, float(os.getenv("FARE_METRO_UP_TO_39", "20"))),
    (10**9, float(os.getenv("FARE_METRO_ABOVE_39", "20"))),
]
ROUTE_LONG_WALK_THRESHOLD_METERS = float(
    os.getenv("ROUTE_LONG_WALK_THRESHOLD_METERS", "1500")
)

GTFS_PATH = os.getenv("GTFS_PATH", "")

CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
    }
}

GTFS_CACHE_TIMEOUT = int(os.getenv("GTFS_CACHE_TIMEOUT", "86400"))
ROUTE_CACHE_TIMEOUT = int(os.getenv("ROUTE_CACHE_TIMEOUT", "300"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "src.Presentation.logging_formatter.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "src": {
            "handlers": ["console"],
            "level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Wslny API",
    "DESCRIPTION": "API documentation for Wslny orchestration and admin endpoints.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "PREPROCESSING_HOOKS": [
        "src.Presentation.urls_preprocessing.prepend_v1_prefix",
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    "SECURITY": [
        {"BearerAuth": []},
    ],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}
