import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

import config.env

VARIABLES = (
    "DEBUG",
    "APP_URLS",
    "SECRET_KEY",
    "REGISTRATION_ENABLED",
    "EMAIL_BACKEND",
)


@pytest.fixture
def load_settings(monkeypatch):
    """Imports config.settings with exactly the given environment (no .env)."""

    def load(**environment):
        monkeypatch.setattr(config.env, "load_dotenv", lambda *paths: None)
        for name in VARIABLES:
            monkeypatch.delenv(name, raising=False)
        for name, value in environment.items():
            monkeypatch.setenv(name, value)
        sys.modules.pop("config.settings", None)
        return importlib.import_module("config.settings")

    yield load
    monkeypatch.undo()
    sys.modules.pop("config.settings", None)


KEY = "x" * 50


def test_https_urls_enable_secure_cookies_but_no_redirect_or_hsts(load_settings):
    settings = load_settings(
        APP_URLS="https://pay.example.com,https://alt.example.com:8443/", SECRET_KEY=KEY
    )

    assert not settings.DEBUG
    assert settings.ALLOWED_HOSTS == ["pay.example.com", "alt.example.com"]
    assert settings.CSRF_TRUSTED_ORIGINS == [
        "https://pay.example.com",
        "https://alt.example.com:8443",
    ]
    # The first URL is the public one.
    assert settings.PUBLIC_URL == "https://pay.example.com"
    assert settings.SESSION_COOKIE_SECURE
    assert settings.CSRF_COOKIE_SECURE
    # TLS, redirect and HSTS are the TLS proxy's job.
    assert not settings.SECURE_SSL_REDIRECT
    assert settings.SECURE_HSTS_SECONDS == 0
    assert settings.MAILERS["default"]["BACKEND"].endswith("smtp.EmailBackend")


def test_plain_http_url_keeps_cookies_insecure(load_settings):
    settings = load_settings(APP_URLS="http://localhost:8080", SECRET_KEY=KEY)

    assert settings.ALLOWED_HOSTS == ["localhost"]
    assert not settings.SESSION_COOKIE_SECURE


@pytest.mark.parametrize("key", ["change-me", "too-short"])
def test_weak_secret_key_is_refused(load_settings, key):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        load_settings(APP_URLS="https://pay.example.com", SECRET_KEY=key)


def test_missing_app_urls_is_refused(load_settings):
    with pytest.raises(ImproperlyConfigured, match="APP_URLS"):
        load_settings(SECRET_KEY=KEY)


def test_debug_runs_without_secrets_and_allows_localhost(load_settings):
    settings = load_settings(DEBUG="true", APP_URLS="https://pay.example.com")

    assert settings.DEBUG
    # The configured URL stays the public one; the localhost ones only come after it.
    assert settings.PUBLIC_URL == "https://pay.example.com"
    assert settings.SECRET_KEY.startswith("django-insecure-dev-only-")
    assert "localhost" in settings.ALLOWED_HOSTS
    assert "http://localhost:8000" in settings.CSRF_TRUSTED_ORIGINS
    assert not settings.SECURE_SSL_REDIRECT
    assert settings.MAILERS["default"]["BACKEND"].endswith("console.EmailBackend")


@pytest.mark.parametrize("value", ["ture", "2", "maybe"])
def test_invalid_boolean_is_refused(load_settings, value):
    with pytest.raises(ImproperlyConfigured, match="REGISTRATION_ENABLED"):
        load_settings(DEBUG="true", REGISTRATION_ENABLED=value)


def test_invalid_app_url_is_refused(load_settings):
    with pytest.raises(ImproperlyConfigured, match="APP_URLS"):
        load_settings(DEBUG="true", APP_URLS="pay.example.com")
