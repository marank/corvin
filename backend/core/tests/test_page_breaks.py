import re
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.utils.translation import override
from pypdf import PdfReader

from core.models import Invoice, InvoiceLineItem
from core.services.pdf import default_template_context, write_document_pdf
from core.services.templates import ensure_default_template


@pytest.fixture
def long_invoice(user, customer):
    invoice = Invoice.objects.create(
        owner=user, customer=customer, number="RE-1", issue_date=date(2026, 11, 24), vat_rate=0
    )
    for position in range(1, 61):
        InvoiceLineItem.objects.create(
            owner=user,
            invoice=invoice,
            position=position,
            description=f"Leistung {position}",
            quantity=1,
            unit="hours",
            unit_price=Decimal(position),
        )
    invoice.recalc_totals()
    return invoice


@pytest.mark.django_db
@override("de")
def test_long_invoice_numbers_its_pages(user, long_invoice):
    data = default_template_context(long_invoice, for_pdf=True)

    pdf = write_document_pdf(ensure_default_template(user), data, user)
    pages = [page.extract_text() for page in PdfReader(BytesIO(pdf)).pages]

    assert len(pages) > 1
    assert data["page_count"] == len(pages)
    for number, text in enumerate(pages, 1):
        assert f"Seite {number} von {len(pages)}" in text
    # Every item made it into the document, none twice.
    lines = [line for text in pages for line in text.splitlines()]
    assert sum(1 for line in lines if re.match(r"\d+ Leistung \d+ ", line)) == 60


@pytest.mark.django_db
@override("de")
def test_single_page_invoice_has_no_page_number(user, long_invoice):
    long_invoice.items.filter(position__gt=3).delete()
    data = default_template_context(long_invoice, for_pdf=True)

    pdf = write_document_pdf(ensure_default_template(user), data, user)
    [page] = PdfReader(BytesIO(pdf)).pages

    assert data["page_count"] == 1
    assert "Seite" not in page.extract_text()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("footer", "text_block", "layouts"),
    [
        ('Seite <span class="page-number"></span>', "", 1),
        ("{% if page_count > 1 %}Seite x von {{ page_count }}{% endif %}", "", 2),
        ("{{ text_blocks.pages }}", "von {{ page_count }}", 2),
    ],
)
def test_second_layout_only_when_page_count_is_used(
    user, long_invoice, monkeypatch, footer, text_block, layouts
):
    from core.models import TextBlock
    from core.services import pdf

    if text_block:
        TextBlock.objects.create(owner=user, key="pages", name="Seiten", content=text_block)
    template = ensure_default_template(user)
    template.footer_html = footer
    calls = []
    render = pdf.render_document_html

    def counting_render(*args):
        calls.append(args)
        return render(*args)

    monkeypatch.setattr(pdf, "render_document_html", counting_render)

    write_document_pdf(template, default_template_context(long_invoice, for_pdf=True), user)

    assert len(calls) == layouts
