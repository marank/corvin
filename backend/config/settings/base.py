from pathlib import Path
from urllib.parse import urlsplit

import environ
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    SECRET_KEY=(str, "change-me"),
    APP_URLS=(list, []),
    REGISTRATION_ENABLED=(bool, False),
    TIME_ZONE=(str, "Europe/Berlin"),
    LANGUAGE_CODE=(str, "de"),
    LOG_LEVEL=(str, "INFO"),
)
# One .env in the repository root, for native development and docker compose alike.
# Values already in the environment (docker compose, CI) win.
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = False  # development.py turns it on
REGISTRATION_ENABLED = env("REGISTRATION_ENABLED")

# Every URL users open the app under. Hosts, CSRF origins and (production) the
# https-only cookies, redirect and HSTS are derived from it.
APP_URLS = [url.rstrip("/") for url in env("APP_URLS")]
ALLOWED_HOSTS = [urlsplit(url).hostname for url in APP_URLS if urlsplit(url).hostname]
CSRF_TRUSTED_ORIGINS = [f"{urlsplit(url).scheme}://{urlsplit(url).netloc}" for url in APP_URLS]
APP_HTTPS_ONLY = bool(APP_URLS) and all(urlsplit(url).scheme == "https" for url in APP_URLS)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "builtins": ["core.templatetags.invoice_helpers"],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# sqlite (backend/db.sqlite3) or postgres. docker compose sets DB_TYPE=postgres and DB_HOST=db.
if env("DB_TYPE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="corvin"),
            "USER": env("DB_USER", default="corvin"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env.int("DB_PORT", default=5432),
        }
    }
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

# Argon2 first (Django's recommendation); the others stay so existing hashes keep
# working and get upgraded on the next login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{v}"}
    for v in (
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    )
]

# Name authenticator apps show next to the TOTP code.
OTP_TOTP_ISSUER = "Corvin"

LANGUAGE_CODE = env("LANGUAGE_CODE")
# API messages follow the UI language (Accept-Language); documents stay in LANGUAGE_CODE.
LANGUAGES = [("de", "Deutsch"), ("en", "English")]
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
    # Django sits behind exactly one nginx, which sets X-Forwarded-For to the real
    # client address (see frontend/nginx.conf), so throttling can't be dodged by
    # sending a forged header.
    "NUM_PROXIES": 1,
}

# Content Security Policy for Django's own responses (admin, invoice/template
# previews, PDFs). Inline styles are needed by the user-editable document templates.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:", "blob:"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "font-src": [CSP.SELF, "data:"],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    # The SPA embeds the previews in iframes.
    "frame-ancestors": [CSP.SELF],
}

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # frontend reads the cookie for X-CSRFToken

# Email — Django 6.x MAILERS setting (SMTP options in OPTIONS dict)
MAILERS = {
    "default": {
        "BACKEND": env(
            "EMAIL_BACKEND",
            default="django.core.mail.backends.console.EmailBackend",
        ),
        "OPTIONS": {
            "host": env("EMAIL_HOST", default="localhost"),
            "port": env.int("EMAIL_PORT", default=587),
            "username": env("EMAIL_USER", default=""),
            "password": env("EMAIL_PASSWORD", default=""),
            "use_tls": env.bool("EMAIL_USE_TLS", default=True),
        },
    }
}
DEFAULT_FROM_EMAIL = env("EMAIL_FROM", default="noreply@example.com")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL").upper()},
}
