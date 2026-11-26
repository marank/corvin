"""The Django admin: off by default, under /django-admin when ADMIN_ENABLED."""

import importlib

import pytest
from django.urls import clear_url_caches

import config.urls


@pytest.fixture
def reload_urls(settings):
    def reload(enabled: bool) -> None:
        settings.ADMIN_ENABLED = enabled
        importlib.reload(config.urls)
        clear_url_caches()

    yield reload
    settings.ADMIN_ENABLED = False
    importlib.reload(config.urls)
    clear_url_caches()


@pytest.mark.django_db
def test_admin_is_off_by_default(client, reload_urls):
    reload_urls(False)
    assert client.get("/django-admin/").status_code == 404
    assert client.get("/admin/").status_code == 404


@pytest.mark.django_db
def test_admin_has_its_own_login_when_enabled(client, reload_urls):
    reload_urls(True)
    assert client.get("/django-admin/login/").status_code == 200


@pytest.mark.django_db
def test_staff_user_gets_into_the_admin(client, django_user_model, reload_urls):
    reload_urls(True)
    client.force_login(django_user_model.objects.create_superuser("boss", password="x" * 20))
    assert client.get("/django-admin/").status_code == 200
