from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from pypdf import PdfReader
from rest_framework.test import APIClient

from core.models import Address, CompanyImage, Customer, DocumentTemplate
from core.services.pdf import build_pdf_html, render_document_html, write_pdf
from core.services.pdf_fetcher import OwnerResourceFetcher
from core.services.templates import DEFAULT_BODY

from .test_company_images import image_file


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def _pdf(user, template, body, header="", footer=""):
    html = build_pdf_html(template, header=header, body=body, footer=footer, css="")
    return PdfReader(BytesIO(write_pdf(html, user)))


@pytest.mark.django_db
def test_pdf_does_not_load_server_files(user, invoice_template, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    client = APIClient()
    client.force_authenticate(user)

    r = client.post(
        f"/api/v1/document-templates/{invoice_template.id}/preview-pdf/",
        {"body_html": f'<link rel="attachment" href="{secret.as_uri()}"><p>x</p>'},
        format="json",
    )

    assert r.status_code == 200
    assert PdfReader(BytesIO(r.content)).attachments == {}


@pytest.mark.django_db
def test_fetcher_allows_only_own_images(user, django_user_model):
    other_user = django_user_model.objects.create_user("bob", password="testpass123")
    own = CompanyImage.objects.create(owner=user, kind="logo_light", key="logo", image=image_file())
    foreign = CompanyImage.objects.create(
        owner=other_user, kind="logo_light", key="logo", image=image_file()
    )
    fetcher = OwnerResourceFetcher(user)

    assert fetcher.fetch(f"file://{own.image.path}").read().startswith(b"\x89PNG")
    for url in (
        f"file://{foreign.image.path}",
        f"file://{own.image.path}/../../{foreign.image.name}",
        "http://127.0.0.1:8000/api/v1/health",
        "file:///etc/hostname",
    ):
        with pytest.raises(ValueError, match="Resource not allowed in documents"):
            fetcher.fetch(url)
    assert fetcher.fetch("data:text/plain,ok").read() == b"ok"


@pytest.mark.django_db
def test_long_document_flows_over_pages_with_header_and_footer(user):
    rows = "".join(f"<p>Position {i}</p>" for i in range(150))

    reader = _pdf(user, DocumentTemplate(), rows, header="KOPF", footer="FUSS")

    assert len(reader.pages) > 1
    texts = [page.extract_text() for page in reader.pages]
    assert all("KOPF" in text and "FUSS" in text for text in texts)
    assert "Position 149" in texts[-1]
    assert sum(text.count("Position ") for text in texts) == 150


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("page_size", "points"),
    [("A4", (595, 842)), ("TABLOID", (792, 1224)), ("LETTER", (612, 792))],
)
def test_pdf_uses_template_page_size(user, page_size, points):
    box = _pdf(user, DocumentTemplate(page_size=page_size), "x").pages[0].mediabox

    assert (round(box.width), round(box.height)) == points


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["body_html", "header_html", "css", "mail_subject"])
def test_template_with_syntax_error_is_rejected(user, invoice_template, field):
    client = APIClient()
    client.force_authenticate(user)

    r = client.patch(
        f"/api/v1/document-templates/{invoice_template.id}/",
        {field: "{% if %}x"},
        format="json",
    )

    assert r.status_code == 400
    assert field in r.json()
    invoice_template.refresh_from_db()
    assert getattr(invoice_template, field) != "{% if %}x"


@pytest.mark.django_db
def test_preview_with_syntax_error_is_a_validation_error(user, invoice_template):
    client = APIClient()
    client.force_authenticate(user)

    r = client.post(
        f"/api/v1/document-templates/{invoice_template.id}/preview/",
        {"body_html": "{% for item in items %}"},
        format="json",
    )

    assert r.status_code == 400


@pytest.mark.django_db
def test_text_block_with_syntax_error_is_rejected(user):
    client = APIClient()
    client.force_authenticate(user)

    r = client.post(
        "/api/v1/text-blocks/",
        {"name": "Gruß", "key": "greeting", "content": "{{ customer.name|nofilter }}"},
        format="json",
    )

    assert r.status_code == 400
    assert "content" in r.json()


@pytest.mark.django_db
def test_preview_offers_the_same_variables_as_an_invoice(user, invoice_template):
    client = APIClient()
    client.force_authenticate(user)
    body = (
        "<p>{{ project.name }}|{{ contract.number }}|{{ customer.vat_id }}|{{ remaining }}"
        "|{% display_time now %}|{% for c in invoice_contacts %}{{ c.role }};{% endfor %}</p>"
    )

    r = client.post(
        f"/api/v1/document-templates/{invoice_template.id}/preview/",
        {"body_html": body},
        format="json",
    )

    assert r.status_code == 200
    html = r.content.decode()
    assert "Netzwerk-Erneuerung|V-2026-003|DE999999999|" in html
    assert "Einkauf;IT-Leitung;" in html
    assert "|—|" not in html  # `now` is set


@pytest.mark.django_db
def test_customer_address_variables_use_the_invoice_address(user, customer):
    Address.objects.create(
        owner=user,
        customer=customer,
        label="Buchhaltung",
        street="Postfach 12",
        postal_code="20001",
        city="Hamburg",
        is_invoice_address=True,
    )
    customer = Customer.objects.get(pk=customer.pk)

    assert (customer.street, customer.postal_code) == ("Postfach 12", "20001")


@pytest.mark.django_db
def test_customer_without_invoice_address_uses_the_primary_one(customer):
    assert Customer.objects.get(pk=customer.pk).street == "Industrieweg 5"


@pytest.mark.django_db
def test_css_variables_are_not_html_escaped(user):
    template = DocumentTemplate(
        primary_font='"Open Sans", sans-serif',
        css="body { font-family: {{ page.primary_font }}; }",
    )

    html = render_document_html(template, {}, user)

    assert 'font-family: "Open Sans", sans-serif;' in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value", "ok"),
    [
        ("primary_color", "#1f2937", True),
        ("primary_color", "rgb(10, 20, 30)", True),
        ("primary_color", "teal", True),
        ("primary_color", "red;}*{color:red", False),
        ("primary_font", '"Open Sans", Arial', True),
        ("primary_font", "Arial; } * { color: red", False),
    ],
)
def test_style_values_are_validated(user, invoice_template, field, value, ok):
    client = APIClient()
    client.force_authenticate(user)

    r = client.patch(
        f"/api/v1/document-templates/{invoice_template.id}/", {field: value}, format="json"
    )

    assert (r.status_code == 200) is ok


@pytest.mark.django_db
def test_deleting_a_template_drops_its_assignments(user, invoice_template):
    other = DocumentTemplate.objects.create(owner=user, name="Andere")
    user.company_settings.template_assignments = {
        "invoice": str(invoice_template.pk),
        "quote": str(other.pk),
    }
    user.company_settings.save()
    client = APIClient()
    client.force_authenticate(user)

    assert client.delete(f"/api/v1/document-templates/{invoice_template.id}/").status_code == 204

    user.company_settings.refresh_from_db()
    assert user.company_settings.template_assignments == {"quote": str(other.pk)}


@pytest.mark.django_db
def test_the_last_template_cannot_be_deleted(user, invoice_template):
    # Otherwise the next list call recreates the default and the delete seems to fail.
    DocumentTemplate.objects.create(owner=User.objects.create_user("bob"), name="Bobs")
    client = APIClient()
    client.force_authenticate(user)

    r = client.delete(f"/api/v1/document-templates/{invoice_template.id}/")

    assert r.status_code == 400
    assert DocumentTemplate.objects.filter(pk=invoice_template.pk).exists()


@pytest.mark.django_db
def test_default_template_uses_the_company_date_format(user, invoice_template):
    user.company_settings.date_format = "YYYY-MM-DD"
    user.company_settings.save()
    client = APIClient()
    client.force_authenticate(user)

    r = client.post(
        f"/api/v1/document-templates/{invoice_template.id}/preview/",
        {"body_html": DEFAULT_BODY},
        format="json",
    )

    assert timezone.localdate().isoformat() in r.content.decode()


def _footer_boxes(html, user):
    """Each page's height and its footer's top and bottom edge, in mm."""
    from weasyprint import HTML

    def boxes(box):
        yield box
        for child in getattr(box, "children", None) or ():
            yield from boxes(child)

    mm = 96 / 25.4
    document = HTML(string=html, url_fetcher=OwnerResourceFetcher(user)).render()
    found = []
    for page in document.pages:
        for box in boxes(page._page_box):
            element = getattr(box, "element", None)
            if element is not None and element.get("id") == "page-footer":
                top = box.position_y + box.margin_top
                found.append((page.height / mm, top / mm, (top + box.border_height()) / mm))
    return found


@pytest.mark.django_db
def test_footer_height_from_css_is_reserved_inside_the_margins(user):
    template = DocumentTemplate(
        owner=user,
        margin_top=10,
        margin_bottom=10,
        footer_height=30,
        css="#page-footer { height: 30mm; }",
        footer_html="<div>Firma<br>Straße 1<br>12345 Ort<br>IBAN DE00<br>USt-IdNr. DE1</div>",
        body_html="".join(f"<p>Zeile {n}</p>" for n in range(120)),
    )

    footers = _footer_boxes(render_document_html(template, {}, user), user)

    assert len(footers) > 1  # repeated on every page of the long body
    for page_height, top, bottom in footers:
        assert top == pytest.approx(page_height - 40, abs=0.5)
        assert bottom == pytest.approx(page_height - 10, abs=0.5)


@pytest.mark.django_db
def test_footer_background_can_reach_the_page_edges(user):
    template = DocumentTemplate(
        owner=user,
        margin_bottom=10,
        footer_height=20,
        css="#page-footer { box-sizing: border-box; height: 30mm; margin-bottom: -10mm; }",
        footer_html="<div>Firma</div>",
        body_html="<p>x</p>",
    )

    [(page_height, top, bottom)] = _footer_boxes(render_document_html(template, {}, user), user)

    assert top == pytest.approx(page_height - 30, abs=0.5)
    assert bottom == pytest.approx(page_height, abs=0.5)
