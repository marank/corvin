import pytest
from django.conf import settings


@pytest.mark.django_db
def test_every_django_response_carries_the_permissions_policy(client):
    response = client.get("/api/v1/health")

    assert response.headers["Permissions-Policy"] == settings.PERMISSIONS_POLICY
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
