from pathlib import Path
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import environ

env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "djoser",
    "user",
    "apps.permissions_api",
    "apps.category",
    "apps.product",
    "apps.about_us",
    "apps.contact_us",
    "apps.section",
    "apps.order",
    "apps.printer",

]

# email settings for mailhog
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "127.0.0.1"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'admin@example.com'  # Default from email
# # email settings for production
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = 'khalmagback.xyz'
# EMAIL_PORT = 465
# EMAIL_HOST_USER = "info@khalmagback.xyz"
# EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
# # EMAIL_USE_TLS = True
# EMAIL_USE_SSL = True
# DEFAULT_FROM_EMAIL = 'info@khalmagback.xyz'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'django_debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# djoser settings
DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": "#/password/reset/confirm/{uid}/{token}",
    "SET_PASSWORD_RETYPE ": True,
    "ACTIVATION_URL": "#/activate/{uid}/{token}",
    "SEND_CONFIRMATION_EMAIL": True,
    "SEND_ACTIVATION_EMAIL": True,
    # "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "LOGOUT_ON_PASSWORD_CHANGE": True,
    "TOKEN_MODEL": None,
    "SERIALIZERS": {
        "user_create": "user.serializers.UserSerializer",
        # "token_create": "djoser.serializers.TokenCreateSerializer",
    },
    "EMAIL": {
        "activation": "djoser.email.ActivationEmail",
        "confirmation": "djoser.email.ConfirmationEmail",
        "password_reset": "djoser.email.PasswordResetEmail",
        "password_changed_confirmation": "djoser.email.PasswordChangedConfirmationEmail",
    },

}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        # "cafe.custom_permissions.CustomerPermission",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=43500),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": settings.SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",  # modified
    "USER_ID_CLAIM": "id",  # modified
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "cafe.middlewares.CustomErrorMiddleware",#added by me
]

ROOT_URLCONF = "cafe.urls"

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

WSGI_APPLICATION = "cafe.wsgi.application"


#payPal Settings
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = 'sandbox'  # or 'live' for production
PAYPAL_BASE_URL=env('PAYPAL_BASE_URL')

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql_psycopg2",
#         "NAME": env("DB_NAME"),
#         "USER": env("DB_USER"),
#         "PASSWORD": env("DB_PASSWORD"),
#         "HOST": env("DB_HOST"),
#         "PORT": env("DB_PORT"),
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

# Enable internationalization and localization
USE_I18N = True
USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ("ar", ("Arabic")),
    ("en", ("English")),
]
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]
ALLOW_UNICODE_SLUGS = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "user.User"


CORS_ORIGIN_WHITELIST = [
    "http://localhost:243",
    "http://localhost:24327",
    "http://localhost:2459",
    "https://localhost:2459",
    "http://localhost:24530",
    "https://localhost:24530",
    "http://admins-score-demo.vercel.app",
    "https://admins-score-demo.vercel.app",
    "https://music-score-pi.vercel.app",
]
CORS_ALLOW_ALL_ORIGINS: True


CORS_ALLOW_CREDENTIALS: True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
