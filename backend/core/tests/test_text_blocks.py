from datetime import date

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import CompanySettings, Invoice, TextBlock
from core.services.pdf import render_invoice_html


@pytest.mark.django_db
def test_text_blocks_render_in_templates(user, customer, invoice_template):
    TextBlock.objects.create(
        owner=user,
        name="Greeting",
        key="greeting",
        content="<p>Invoice {{ invoice.number }} for {{ customer.name }}</p>",
    )
    invoice_template.body_html = "{{ page.document_type }}|{{ text_blocks.greeting }}"
    invoice_template.save(update_fields=["body_html"])
    invoice = Invoice.objects.create(
        owner=user,
        customer=customer,
        number="RE-1",
        issue_date=date(2026, 1, 1),
        template=invoice_template,
    )

    html = render_invoice_html(invoice)

    assert "invoice|<p>Invoice RE-1 for Acme GmbH</p>" in html


@pytest.mark.django_db
def test_text_block_api_is_owner_scoped(user):
    other = User.objects.create_user("text-block-other")
    CompanySettings.objects.create(user=other)
    TextBlock.objects.create(owner=other, name="Foreign", key="foreign", content="Hidden")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/text-blocks/")

    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_text_block_key_validation(user):
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/text-blocks/",
        {
            "name": "Invalid",
            "key": "Invalid key",
            "content": "Text",
        },
        format="json",
    )

    assert response.status_code == 400

    # Uppercase keys are accepted
    ok = client.post(
        "/api/v1/text-blocks/",
        {"name": "Valid", "key": "INV_PRE_1", "content": "Text"},
        format="json",
    )
    assert ok.status_code == 201
