from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.request import Request
from rest_framework.test import APIClient

from core.models import Attachment, CompanyImage


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def png(name="logo.png"):
    value = BytesIO()
    Image.new("RGB", (10, 10), "white").save(value, format="PNG")
    return SimpleUploadedFile(name, value.getvalue(), content_type="image/png")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def other_user(db):
    return User.objects.create_user("mallory", password="testpass123")


def attach(user, customer, name, content=b"data"):
    return Attachment.objects.create(
        owner=user,
        file=SimpleUploadedFile(name, content),
        content_type=ContentType.objects.get_for_model(customer),
        object_id=customer.id,
    )


@pytest.mark.django_db
def test_company_image_served_inline_to_owner_only(user, other_user):
    image = CompanyImage.objects.create(owner=user, kind="logo_light", name="Logo", image=png())
    url = f"/api/v1/company-images/{image.id}/file/"

    response = client_for(user).get(url)
    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("inline")
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")

    listed = client_for(user).get("/api/v1/company-images/").json()["results"]
    assert listed[0]["url"].endswith(url)

    assert client_for(other_user).get(url).status_code == 404
    assert APIClient().get(url).status_code == 403


@pytest.mark.django_db
def test_attachment_pdf_inline_html_forced_download(user, customer, other_user):
    pdf = attach(user, customer, "report.pdf", b"%PDF-1.7")
    html = attach(user, customer, "page.html", b"<script>alert(1)</script>")

    response = client_for(user).get(f"/api/v1/attachments/{pdf.id}/file/")
    assert response["Content-Disposition"].startswith("inline")

    response = client_for(user).get(f"/api/v1/attachments/{html.id}/file/")
    assert response["Content-Disposition"].startswith("attachment")

    assert client_for(other_user).get(f"/api/v1/attachments/{pdf.id}/file/").status_code == 404


@pytest.mark.django_db
def test_attachment_url_is_relative(user, customer):
    attach(user, customer, "report.pdf", b"%PDF-1.7")

    response = client_for(user).get(f"/api/v1/attachments/?model=customer&object_id={customer.id}")

    [attachment] = response.json()["results"]
    assert attachment["url"] == f"/api/v1/attachments/{attachment['id']}/file/"


@pytest.mark.django_db
def test_login_requires_csrf_token(user):
    client = APIClient(enforce_csrf_checks=True)
    credentials = {"username": "alice", "password": "testpass123"}

    assert client.post("/api/v1/auth/login", credentials).status_code == 403

    client.get("/api/v1/auth/me")
    token = client.cookies["csrftoken"].value
    response = client.post("/api/v1/auth/login", credentials, HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_is_public_and_responses_carry_csp():
    response = APIClient().get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "frame-ancestors 'self'" in response["Content-Security-Policy"]


@pytest.mark.django_db
def test_throttle_uses_last_forwarded_address(user):
    from core.views.auth import LoginThrottle

    request = (
        APIClient().get("/api/v1/health", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.7").wsgi_request
    )
    assert LoginThrottle().get_ident(Request(request)) == "203.0.113.7"


@pytest.mark.django_db
def test_attachment_preview_only_for_safe_types(user, customer):
    attach(user, customer, "notes.MD", b"# Hi")
    attach(user, customer, "log.txt", b"line")
    attach(user, customer, "scan.png", b"png")
    attach(user, customer, "page.html", b"<script></script>")
    attach(user, customer, "image.svg", b"<svg/>")

    results = client_for(user).get("/api/v1/attachments/").json()["results"]

    previews = {a["name"]: a["preview"] for a in results}
    assert previews == {
        "notes.MD": "markdown",
        "log.txt": "text",
        "scan.png": "image",
        "page.html": None,
        "image.svg": None,
    }
    assert {a["name"]: a["size"] for a in results}["notes.MD"] == 4


@pytest.mark.django_db
def test_large_text_attachment_has_no_preview():
    from core.services.file_preview import TEXT_PREVIEW_LIMIT, preview_kind

    assert preview_kind("big.txt", TEXT_PREVIEW_LIMIT + 1) is None
    assert preview_kind("big.pdf", TEXT_PREVIEW_LIMIT + 1) == "pdf"
    assert preview_kind("README", 10) is None


@pytest.mark.django_db
def test_attachment_with_missing_file_has_no_preview(user, customer):
    attachment = attach(user, customer, "notes.md", b"# Hi")
    attachment.file.storage.delete(attachment.file.name)

    [listed] = client_for(user).get("/api/v1/attachments/").json()["results"]
    assert (listed["size"], listed["preview"]) == (None, None)
