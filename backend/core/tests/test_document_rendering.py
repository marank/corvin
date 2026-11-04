from io import BytesIO

import pytest
from pypdf import PdfReader
from rest_framework.test import APIClient

from core.models import CompanyImage, DocumentTemplate
from core.services.pdf import build_pdf_html, write_pdf
from core.services.pdf_fetcher import OwnerResourceFetcher

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
        "http://backend:8000/api/v1/health",
        "file:///etc/hostname",
    ):
        with pytest.raises(ValueError):
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
