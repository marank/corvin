import importlib
import sys

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

import config.settings.base


@pytest.fixture
def production(monkeypatch):
    """Imports the production settings with exactly the given environment (no .env)."""

    def load(**environment):
        monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
        for name in ("APP_URLS", "SECRET_KEY", "SECURE_HSTS_INCLUDE_SUBDOMAINS"):
            monkeypatch.delenv(name, raising=False)
        for name, value in environment.items():
            monkeypatch.setenv(name, value)
        importlib.reload(config.settings.base)
        sys.modules.pop("config.settings.production", None)
        return importlib.import_module("config.settings.production")

    yield load
    monkeypatch.undo()
    sys.modules.pop("config.settings.production", None)
    importlib.reload(config.settings.base)


KEY = "x" * 50


def test_https_urls_enable_secure_cookies_and_redirect(production):
    settings = production(
        APP_URLS="https://pay.example.com,https://alt.example.com:8443/", SECRET_KEY=KEY
    )

    assert settings.ALLOWED_HOSTS == ["pay.example.com", "alt.example.com"]
    assert settings.CSRF_TRUSTED_ORIGINS == [
        "https://pay.example.com",
        "https://alt.example.com:8443",
    ]
    assert settings.SESSION_COOKIE_SECURE and settings.SECURE_SSL_REDIRECT
    assert settings.SECURE_HSTS_SECONDS > 0
    assert not settings.SECURE_HSTS_INCLUDE_SUBDOMAINS


def test_plain_http_url_keeps_cookies_and_redirect_off(production):
    settings = production(APP_URLS="http://localhost:8080", SECRET_KEY=KEY)

    assert settings.ALLOWED_HOSTS == ["localhost"]
    assert not settings.SESSION_COOKIE_SECURE
    assert not settings.SECURE_SSL_REDIRECT
    assert settings.SECURE_HSTS_SECONDS == 0


@pytest.mark.parametrize("key", ["change-me", "too-short"])
def test_weak_secret_key_is_refused(production, key):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        production(APP_URLS="https://pay.example.com", SECRET_KEY=key)


def test_missing_app_urls_is_refused(production):
    with pytest.raises(ImproperlyConfigured, match="APP_URLS"):
        production(SECRET_KEY=KEY)
