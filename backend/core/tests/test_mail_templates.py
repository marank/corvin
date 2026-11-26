"""E-mail templates: defaults, blocks and bases, validation, assignments, previews."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import CompanySettings, DocumentTemplate, MailTemplate
from core.services.mail_templates import html_to_text, mail_template_for, slot_names
from core.services.user_setup import set_up_user


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def layout(user):
    set_up_user(user)
    return MailTemplate.objects.get(owner=user, base__isnull=True)


def _create(client, **data):
    return client.post("/api/v1/mail-templates/", data, format="json")


@pytest.mark.django_db
def test_new_users_start_with_the_defaults_assigned():
    user = User.objects.create_user("bob", password="testpass123")
    set_up_user(user)
    company = CompanySettings.objects.get(user=user)
    invoice_template = DocumentTemplate.objects.get(owner=user)
    assert company.template_assignments == {"invoice": str(invoice_template.pk)}
    assigned = {
        kind: MailTemplate.objects.get(pk=pk)
        for kind, pk in company.mail_template_assignments.items()
    }
    assert set(assigned) == {"invoice", "payment_reminder"}
    assert {t.base.name for t in assigned.values() if t.base} == {"Standard-Layout"}
    # Idempotent: nothing twice.
    set_up_user(user)
    assert MailTemplate.objects.filter(owner=user).count() == 3


@pytest.mark.django_db
def test_the_layouts_blocks_are_offered(layout):
    assert slot_names(layout) == ["anrede", "inhalt", "gruss", "fusszeile"]


@pytest.mark.django_db
def test_a_new_template_starts_with_the_blocks_of_its_base(client, layout):
    r = _create(client, name="Leer", base=str(layout.pk))
    assert r.status_code == 201, r.json()
    assert r.json()["html"] == (
        "{% block anrede %}{{ block.super }}{% endblock %}\n\n"
        "{% block inhalt %}{{ block.super }}{% endblock %}\n\n"
        "{% block gruss %}{{ block.super }}{% endblock %}\n\n"
        "{% block fusszeile %}{{ block.super }}{% endblock %}"
    )


@pytest.mark.django_db
def test_a_template_fills_the_blocks_of_its_base(client, layout):
    r = _create(
        client,
        name="Kurz",
        subject="Nr. {{ invoice.number }} & mehr",
        base=str(layout.pk),
        html=(
            "{% block inhalt %}<p>Kurz und knapp.</p>{% endblock %}\n"
            "{% block gruss %}{{ block.super }}{% endblock %}"
        ),
    )
    assert r.status_code == 201, r.json()
    preview = client.get(f"/api/v1/mail-templates/{r.json()['id']}/preview/").json()
    assert "<p>Kurz und knapp.</p>" in preview["html"]
    # Blocks left out or kept with block.super show the base's content.
    assert "Viele Grüße" in preview["html"]
    # Subjects are no HTML.
    assert preview["subject"].endswith("& mehr")

    # Built on again: the chain still works, and offers the same blocks.
    r = _create(
        client,
        name="Noch kürzer",
        base=r.json()["id"],
        html="{% block anrede %}<p>Hi,</p>{% endblock %}",
    )
    assert r.status_code == 201, r.json()
    assert r.json()["slot_names"] == ["anrede", "inhalt", "gruss", "fusszeile"]
    html = client.get(f"/api/v1/mail-templates/{r.json()['id']}/preview/").json()["html"]
    assert "<p>Hi,</p>" in html
    assert "Kurz und knapp." in html


@pytest.mark.django_db
def test_unsaved_changes_can_be_previewed(client, layout):
    template = mail_template_for(layout.owner, "invoice")
    r = client.post(
        f"/api/v1/mail-templates/{template.pk}/preview/",
        {"html": "{% block inhalt %}<p>Entwurf</p>{% endblock %}"},
        format="json",
    )
    assert "<p>Entwurf</p>" in r.json()["html"]
    template.refresh_from_db()
    assert "Entwurf" not in template.html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    [
        {"html": "{% block nirgends %}<p>x</p>{% endblock %}"},
        {"html": "{% block inhalt %}{% if %}{% endblock %}"},
        {"html": "<p>outside every block</p>"},
        {"subject": "{% if %}"},
    ],
)
def test_broken_templates_are_refused(client, layout, data):
    r = _create(client, name="Kaputt", base=str(layout.pk), **data)
    assert r.status_code == 400


@pytest.mark.django_db
def test_a_template_cannot_build_on_itself(client, layout):
    derived = mail_template_for(layout.owner, "invoice")
    r = client.patch(
        f"/api/v1/mail-templates/{layout.pk}/", {"base": str(derived.pk)}, format="json"
    )
    assert r.status_code == 400
    assert "base" in r.json()


@pytest.mark.django_db
def test_bases_of_another_user_are_refused(client, layout):
    stranger = User.objects.create_user("mallory", password="testpass123")
    set_up_user(stranger)
    theirs = MailTemplate.objects.get(owner=stranger, base__isnull=True)
    assert _create(client, name="X", base=str(theirs.pk)).status_code == 400


@pytest.mark.django_db
def test_used_templates_are_not_deleted(client, layout):
    assigned = mail_template_for(layout.owner, "invoice")
    assert client.delete(f"/api/v1/mail-templates/{assigned.pk}/").status_code == 400
    assert client.delete(f"/api/v1/mail-templates/{layout.pk}/").status_code == 400

    spare = _create(client, name="Übrig", base=str(layout.pk)).json()
    assert client.delete(f"/api/v1/mail-templates/{spare['id']}/").status_code == 204


@pytest.mark.django_db
def test_templates_are_duplicated(client, layout):
    template = mail_template_for(layout.owner, "invoice")
    r = client.post(f"/api/v1/mail-templates/{template.pk}/duplicate/")
    assert r.status_code == 201
    assert r.json()["name"].startswith(template.name)
    assert r.json()["html"] == template.html
    assert r.json()["base"] == str(layout.pk)

    document = DocumentTemplate.objects.get(owner=layout.owner)
    r = client.post(f"/api/v1/document-templates/{document.pk}/duplicate/")
    assert r.status_code == 201
    assert r.json()["body_html"] == document.body_html
    assert DocumentTemplate.objects.filter(owner=layout.owner).count() == 2


@pytest.mark.django_db
def test_mail_assignments_need_a_template_with_a_subject(client, layout):
    r = client.put(
        "/api/v1/settings/",
        {"mail_template_assignments": {"payment_reminder": str(layout.pk)}},
        format="json",
    )
    assert r.status_code == 400
    template = _create(client, name="Anders", subject="Erinnerung", base=str(layout.pk)).json()
    r = client.put(
        "/api/v1/settings/",
        {"mail_template_assignments": {"payment_reminder": template["id"]}},
        format="json",
    )
    assert r.status_code == 200, r.json()
    # Kinds left out keep their template.
    assignments = r.json()["mail_template_assignments"]
    assert assignments["payment_reminder"] == template["id"]
    assert assignments["invoice"] == str(mail_template_for(layout.owner, "invoice").pk)


@pytest.mark.django_db
def test_invoices_always_keep_a_document_template(client, layout):
    r = client.put("/api/v1/settings/", {"template_assignments": {"invoice": None}}, format="json")
    assert r.status_code == 400


def test_plain_text_comes_from_the_html():
    html = (
        "<html><head><style>p{}</style></head><body><p>Guten Tag,</p>"
        '<p>siehe <a href="https://x.example">Portal</a><br>Zeile 2</p>'
        "<ul><li>eins</li><li>zwei</li></ul><p>A &amp; B</p></body></html>"
    )
    assert html_to_text(html) == (
        "Guten Tag,\n\nsiehe Portal (https://x.example)\nZeile 2\n\n- eins\n- zwei\n\nA & B"
    )
