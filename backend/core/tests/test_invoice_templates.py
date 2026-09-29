import pytest
from rest_framework.test import APIClient

from core.models import InvoiceTemplate


@pytest.mark.django_db
def test_template_export_import_round_trip(user, invoice_template):
    client = APIClient()
    client.force_authenticate(user)
    invoice_template.primary_color = "#123456"
    invoice_template.header_html = "<header>{{ company.company_name }}</header>"
    invoice_template.save(update_fields=["primary_color", "header_html"])

    exported = client.get(
        f"/api/v1/invoice-templates/{invoice_template.id}/export/"
    )

    assert exported.status_code == 200
    assert exported["Content-Disposition"].endswith('.json"')
    payload = exported.json()
    assert payload["format"] == "projectmanager.invoice-template"
    assert payload["version"] == 1
    assert payload["template"]["primary_color"] == "#123456"
    assert "id" not in payload["template"]
    assert "created_at" not in payload["template"]

    imported = client.post(
        "/api/v1/invoice-templates/import/", payload, format="json"
    )

    assert imported.status_code == 201
    imported_template = InvoiceTemplate.objects.get(pk=imported.json()["id"])
    assert imported_template.owner == user
    assert imported_template.id != invoice_template.id
    assert imported_template.header_html == invoice_template.header_html
    assert imported_template.primary_color == "#123456"
    assert imported_template.pk != invoice_template.pk


@pytest.mark.django_db
def test_template_import_rejects_unknown_format(user):
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/invoice-templates/import/",
        {"format": "unknown", "version": 1, "template": {}},
        format="json",
    )

    assert response.status_code == 400
    assert InvoiceTemplate.objects.filter(owner=user).count() == 0
