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
