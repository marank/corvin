from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from PIL import Image
from rest_framework.test import APIClient

from core.models import CompanyImage


def image_file(name="logo.png"):
    value = BytesIO()
    Image.new("RGB", (10, 10), "white").save(value, format="PNG")
    return SimpleUploadedFile(name, value.getvalue(), content_type="image/png")


@pytest.mark.django_db
def test_company_image_upload_and_owner_scope(user):
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1/company-images/",
        {
            "kind": "logo_light",
            "key": "logo_light",
            "name": "Light logo",
            "image": image_file(),
        },
        format="multipart",
    )
    assert response.status_code == 201
    assert response.json()["key"] == "logo_light"
    assert CompanyImage.objects.filter(owner=user, kind="logo_light").exists()


@pytest.mark.django_db
def test_additional_image_requires_key(user):
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1/company-images/",
        {
            "kind": "additional",
            "name": "Stamp",
            "image": image_file(),
        },
        format="multipart",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_invoice_template_formatting_helpers(user):
    company = user.company_settings
    company.decimal_separator = ","
    company.thousands_separator = "."
    company.currency = "EUR"
    company.save()
    rendered = Template("{% display_number amount 2 2 %}|{% display_money amount %}").render(
        Context({"amount": "1234.5", "company": company})
    )
    assert rendered == "1.234,50|1.234,50 €"


@pytest.mark.django_db
def test_image_url_is_relative_so_it_works_behind_a_proxy(user, settings):
    # nginx passes Host without the port (corvin.example for corvin.example:8012); an absolute
    # URL built from it would point to port 80 and the image would not load.
    settings.ALLOWED_HOSTS = ["corvin.example"]
    client = APIClient(HTTP_HOST="corvin.example")
    client.force_authenticate(user)
    created = client.post(
        "/api/v1/company-images/",
        {"kind": "logo_light", "key": "logo_light", "name": "Logo", "image": image_file()},
        format="multipart",
    ).json()

    listed = client.get("/api/v1/company-images/").json()["results"]

    assert created["url"] == f"/api/v1/company-images/{created['id']}/file/"
    assert [image["url"] for image in listed] == [created["url"]]
    assert client.get(created["url"]).status_code == 200


@pytest.mark.django_db
def test_designer_preview_loads_images_from_relative_urls(user, invoice_template):
    image = CompanyImage.objects.create(owner=user, kind="logo_light", image=image_file())
    invoice_template.header_html = '<img src="{{ images.logo_light }}">'
    invoice_template.save(update_fields=["header_html"])
    client = APIClient()
    client.force_authenticate(user)

    html = client.get(f"/api/v1/document-templates/{invoice_template.id}/preview/").content

    assert f'<img src="/api/v1/company-images/{image.id}/file/">'.encode() in html
