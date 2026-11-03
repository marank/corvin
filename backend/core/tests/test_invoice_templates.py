import pytest
from rest_framework.test import APIClient

from core.models import DocumentTemplate


@pytest.mark.django_db
def test_template_export_import_round_trip(user, invoice_template):
    client = APIClient()
    client.force_authenticate(user)
    invoice_template.primary_color = "#123456"
    invoice_template.header_html = "<header>{{ company.company_name }}</header>"
    invoice_template.save(update_fields=["primary_color", "header_html"])

    exported = client.get(f"/api/v1/document-templates/{invoice_template.id}/export/")

    assert exported.status_code == 200
    assert exported["Content-Disposition"].endswith('.json"')
    payload = exported.json()
    assert payload["format"] == "projectmanager.document-template"
    assert payload["version"] == 1
    assert payload["template"]["primary_color"] == "#123456"
    assert "id" not in payload["template"]
    assert "created_at" not in payload["template"]

    imported = client.post("/api/v1/document-templates/import/", payload, format="json")

    assert imported.status_code == 201
    imported_template = DocumentTemplate.objects.get(pk=imported.json()["id"])
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
        "/api/v1/document-templates/import/",
        {"format": "unknown", "version": 1, "template": {}},
        format="json",
    )

    assert response.status_code == 400
    assert DocumentTemplate.objects.filter(owner=user).count() == 0


@pytest.mark.django_db
def test_preview_without_any_template_seeds_default(user, customer):
    client = APIClient()
    client.force_authenticate(user)
    r = client.post(
        "/api/v1/invoices/consolidate/",
        {
            "customer_id": str(customer.id),
            "extra_lines": [
                {"description": "Setup", "quantity": "1", "unit": "flat", "unit_price": "100"}
            ],
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert not DocumentTemplate.objects.filter(owner=user).exists()

    preview = client.get(f"/api/v1/invoices/{r.json()['id']}/preview/")

    assert preview.status_code == 200
    html = preview.content.decode()
    assert "Industrieweg 5" in html  # customer address
    assert "Rechnungsdatum" in html
    assert DocumentTemplate.objects.filter(owner=user).count() == 1
