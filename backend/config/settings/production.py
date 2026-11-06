from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import APP_HTTPS_ONLY, APP_URLS, SECRET_KEY, env

DEBUG = False

if SECRET_KEY == "change-me" or len(SECRET_KEY) < 40:
    raise ImproperlyConfigured(
        "SECRET_KEY must be a long random string (at least 40 characters), see .env.example."
    )
if not APP_URLS:
    raise ImproperlyConfigured("APP_URLS is empty, see .env.example.")

# https-only (secure cookies, redirect, HSTS) once every APP_URLS entry is https,
# i.e. a TLS proxy is in front. nginx forwards the proxy's X-Forwarded-Proto only
# from TRUSTED_PROXIES and sets it itself otherwise, so clients can't fake it.
SESSION_COOKIE_SECURE = APP_HTTPS_ONLY
CSRF_COOKIE_SECURE = APP_HTTPS_ONLY
SECURE_SSL_REDIRECT = APP_HTTPS_ONLY
SECURE_HSTS_SECONDS = 31536000 if APP_HTTPS_ONLY else 0
# Subdomains and the preload list are a decision for the domain owner, not the app.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Docker's healthcheck talks plain http to gunicorn directly.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
SILENCED_SYSTEM_CHECKS = ["security.W021"]
if not SECURE_HSTS_INCLUDE_SUBDOMAINS:
    SILENCED_SYSTEM_CHECKS.append("security.W005")

MAILERS["default"]["BACKEND"] = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
