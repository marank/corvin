"""Every existing user gets the default templates, assigned: a document template for
invoices (unless they have one) and the default e-mail layout with one template per mail
kind. New users get them when they are created (services.user_setup)."""

from django.db import migrations

from core.services import mail_defaults
from core.services.templates import DEFAULT_BODY, DEFAULT_CSS, DEFAULT_FOOTER


def _document_template(apps, user, company):
    DocumentTemplate = apps.get_model("core", "DocumentTemplate")
    templates = DocumentTemplate.objects.filter(owner=user).order_by("created_at")
    assignments = dict(company.template_assignments or {})
    if templates.filter(pk=assignments.get("invoice") or None).exists():
        return
    template = templates.first() or DocumentTemplate.objects.create(
        owner=user,
        name="Standard (DIN A4)",
        body_html=DEFAULT_BODY,
        css=DEFAULT_CSS,
        footer_html=DEFAULT_FOOTER,
        footer_height=10,
    )
    assignments["invoice"] = str(template.pk)
    company.template_assignments = assignments


def _mail_templates(apps, user, company):
    MailTemplate = apps.get_model("core", "MailTemplate")
    layout = MailTemplate.objects.create(
        owner=user, name=mail_defaults.LAYOUT_NAME, html=mail_defaults.LAYOUT_HTML
    )
    assignments = {}
    for kind, default in mail_defaults.TEMPLATES.items():
        template = MailTemplate.objects.create(
            owner=user,
            name=default["name"],
            subject=default["subject"],
            base=layout,
            html=default["html"],
        )
        assignments[kind] = str(template.pk)
    company.mail_template_assignments = assignments


def create_defaults(apps, schema_editor):
    User = apps.get_model("auth", "User")
    CompanySettings = apps.get_model("core", "CompanySettings")
    for user in User.objects.all():
        company, _created = CompanySettings.objects.get_or_create(user=user)
        _document_template(apps, user, company)
        _mail_templates(apps, user, company)
        company.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0039_mail_templates"),
    ]

    operations = [
        migrations.RunPython(create_defaults, migrations.RunPython.noop),
    ]
