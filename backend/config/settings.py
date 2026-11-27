import os
import sys
from datetime import time
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

from .env import env_bool, env_int, env_list, env_str, load_dotenv, parse_app_urls, secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# One .env in the repository root, for native development and docker compose alike.
# Values already in the environment (docker compose, CI) win.
load_dotenv(BASE_DIR.parent / ".env")

# Off unless set: native development sets it in .env (docs/development.md), docker
# compose switches it off explicitly.
DEBUG = env_bool("DEBUG", False)
SECRET_KEY = secret_key(DEBUG)  # >= 40 chars, else refuse to start (DEBUG: fixed dev key)
REGISTRATION_ENABLED = env_bool("REGISTRATION_ENABLED", False)
# The Django admin at /django-admin (staff users). Off by default.
ADMIN_ENABLED = env_bool("ADMIN_ENABLED", False)

# Every URL users open the app under. Hosts, CSRF origins and the https-only cookies
# are derived from it.
APP_URLS = parse_app_urls(env_list("APP_URLS"))
if not APP_URLS and not DEBUG:
    raise ImproperlyConfigured("APP_URLS is empty, see .env.example.")
# The first entry is the public address, by definition: links that leave the browser
# (mails, documents) use it, whatever address a request came in under.
PUBLIC_URL = APP_URLS[0].origin if APP_URLS else "http://localhost:8000"
APP_HTTPS_ONLY = bool(APP_URLS) and all(url.scheme == "https" for url in APP_URLS)
if DEBUG:
    # runserver and Vite on localhost besides whatever APP_URLS lists (e.g. the Docker
    # stack). The Vite proxy rewrites Origin to the backend host (see vite.config.ts);
    # Django compares the port too, so :8000 is listed explicitly.
    APP_URLS += parse_app_urls(["http://localhost:8000", "http://127.0.0.1:8000"])
ALLOWED_HOSTS = list(dict.fromkeys(url.hostname for url in APP_URLS))
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(url.origin for url in APP_URLS))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.PermissionsPolicyMiddleware",
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

# PostgreSQL when DB_HOST is set (docker compose sets db, CI localhost); natively SQLite in
# backend/db.sqlite3.
if env_str("DB_HOST", ""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env_str("DB_NAME", "corvin"),
            "USER": env_str("DB_USER", "corvin"),
            "PASSWORD": env_str("DB_PASSWORD", ""),
            "HOST": env_str("DB_HOST"),
            "PORT": env_int("DB_PORT", 5432),
        }
    }
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

# Background jobs (core/tasks.py, deferred through core.jobs.defer): with PostgreSQL a
# procrastinate queue in the database, worked off by the "worker" container. SQLite has no
# queue: jobs then run in-process right after the transaction commits, and the periodic
# jobs (recurring invoices, backups) don't run at all.
JOB_QUEUE = DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
if JOB_QUEUE:
    INSTALLED_APPS.append("procrastinate.contrib.django")

# Daily jobs of the worker, as times of day in TIME_ZONE. Not between 02:00 and 03:00:
# daylight saving time skips that hour once a year and repeats it once.
RECURRING_TIME = time.fromisoformat(env_str("RECURRING_TIME", "06:00"))
# Nightly pg_dump + tarball of MEDIA_ROOT into BACKUP_DIR (the "backups" volume, /backups in
# the image). Empty switches the nightly backup off.
BACKUP_DIR = env_str("BACKUP_DIR", "")
BACKUP_TIME = time.fromisoformat(env_str("BACKUP_TIME", "01:30"))
BACKUP_KEEP_DAYS = env_int("BACKUP_KEEP_DAYS", 14)

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

# Usernames are case-insensitive at login: "Admin" and "admin" are the same account.
AUTHENTICATION_BACKENDS = ["core.auth_backends.CaseInsensitiveModelBackend"]

# Name authenticator apps show next to the TOTP code.
OTP_TOTP_ISSUER = "Corvin"

LANGUAGE_CODE = env_str("LANGUAGE_CODE", "de")
# API messages follow the UI language (Accept-Language); documents stay in LANGUAGE_CODE.
LANGUAGES = [("de", "Deutsch"), ("en", "English")]
TIME_ZONE = env_str("TIME_ZONE", "Europe/Berlin")
USE_I18N = True
USE_TZ = True

# Admin assets only; the SPA is served by nginx / Vite. Not "/static/", so it can't collide
# with the SPA's own files.
STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
# Everything the app writes at runtime lives below DATA_DIR (/data in the image, the only
# writable place besides /backups and /tmp). Uploads are served only through the API.
DATA_DIR = Path(env_str("DATA_DIR", str(BASE_DIR / "data")))
MEDIA_ROOT = DATA_DIR / "media"

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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
    # Django sits behind exactly one nginx, which sets X-Forwarded-For to the real
    # client address (see frontend/nginx.conf), so throttling can't be dodged by
    # sending a forged header.
    "NUM_PROXIES": 1,
}

# OpenAPI schema for the frontend's generated types (`just api-types`); not served.
SPECTACULAR_SETTINGS = {
    "TITLE": "Corvin API",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # One choice set used by two fields gets one name instead of a field-derived one each.
    "ENUM_NAME_OVERRIDES": {
        "TimeRoundingDirectionEnum": "core.models.CompanySettings.TimeRoundingDirection",
        "MailKindEnum": "core.models.MailTemplate.Kind",
        "InvoiceMailStatusEnum": "core.models.InvoiceMail.Status",
        "TravelRateKindEnum": "core.models.TravelRate.Kind",
    },
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

# Secure cookies once every APP_URLS entry is https, i.e. a TLS proxy is in front.
# nginx forwards the proxy's X-Forwarded-Proto only from TRUSTED_PROXIES and sets it
# itself otherwise, so clients can't fake it.
_HTTPS_ONLY = APP_HTTPS_ONLY and not DEBUG
SESSION_COOKIE_SECURE = _HTTPS_ONLY
CSRF_COOKIE_SECURE = _HTTPS_ONLY
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# No side effects beyond our own responses: TLS, the http -> https redirect and HSTS belong
# to the TLS proxy in front. HSTS changes how browsers treat the whole host (for a year,
# for every app on it) and a permanent redirect is cached by them, so the app sets neither;
# the deploy check's warnings about them are silenced on purpose.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SILENCED_SYSTEM_CHECKS = ["security.W004", "security.W008"]
# Browser features the app never uses stay off for it and anything it embeds
# (core.middleware.PermissionsPolicyMiddleware; nginx sends the same for the SPA).
PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=(), "
    "hid=(), midi=(), magnetometer=(), gyroscope=(), accelerometer=(), browsing-topics=()"
)

# Email — Django 6.x MAILERS setting (SMTP options in OPTIONS dict). Natively the
# console backend prints mails instead of sending them.
MAILERS = {
    "default": {
        "BACKEND": env_str(
            "EMAIL_BACKEND",
            "django.core.mail.backends.console.EmailBackend"
            if DEBUG
            else "django.core.mail.backends.smtp.EmailBackend",
        ),
        "OPTIONS": {
            "host": env_str("EMAIL_HOST", "localhost"),
            "port": env_int("EMAIL_PORT", 587),
            "username": env_str("EMAIL_USER", ""),
            "password": env_str("EMAIL_PASSWORD", ""),
            "use_tls": env_bool("EMAIL_USE_TLS", True),
        },
    }
}
DEFAULT_FROM_EMAIL = env_str("EMAIL_FROM", "noreply@example.com")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env_str("LOG_LEVEL", "INFO").upper()},
    # Every manage.py command would list each registered job otherwise.
    "loggers": {
        "procrastinate.blueprints": {"level": "WARNING"},
        "procrastinate.periodic": {"level": "WARNING"},
    },
}

# WeasyPrint on Windows needs the GTK/Pango runtime (installed via MSYS2).
# Registers the DLL directory for this process only — no global PATH change.
if sys.platform == "win32":
    for _dll_dir in (
        env_str("MSYS2_BIN_DIR", ""),
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
    ):
        if _dll_dir and os.path.isdir(_dll_dir):
            os.add_dll_directory(_dll_dir)
            break
