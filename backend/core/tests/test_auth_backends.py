import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.test import APIClient

PASSWORD = "testpass123"


@pytest.mark.django_db
def test_login_ignores_case_of_username():
    User.objects.create_user("alice", password=PASSWORD)

    user = authenticate(username="ALICE", password=PASSWORD)
    assert user is not None
    assert user.username == "alice"


@pytest.mark.django_db
def test_wrong_password_or_unknown_user_is_refused():
    User.objects.create_user("alice", password=PASSWORD)

    assert authenticate(username="Alice", password="wrong") is None
    assert authenticate(username="nobody", password=PASSWORD) is None
    assert authenticate(username=None, password=PASSWORD) is None


@pytest.mark.django_db
def test_inactive_user_is_refused():
    User.objects.create_user("alice", password=PASSWORD, is_active=False)

    assert authenticate(username="alice", password=PASSWORD) is None


@pytest.mark.django_db
def test_registration_refuses_name_differing_only_in_case(settings):
    settings.REGISTRATION_ENABLED = True
    User.objects.create_user("alice", password=PASSWORD)

    response = APIClient().post(
        "/api/v1/auth/register", {"username": "Alice", "password": PASSWORD}, format="json"
    )

    assert response.status_code == 400
    assert "username" in response.json()
