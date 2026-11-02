from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# nginx forwards the TLS proxy's X-Forwarded-Proto only from TRUSTED_PROXIES and
# sets it itself otherwise, so clients can't fake it.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# Docker's healthcheck talks plain http to gunicorn directly.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
# HSTS preload is a decision for the domain owner, not the app.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
MAILERS["default"]["BACKEND"] = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
