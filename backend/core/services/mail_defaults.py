"""The e-mail templates every user starts with: a layout and one template per mail kind.

Plain strings, so the data migration that gives existing users these templates can use
them as well (it must not import models).
"""

from typing import TypedDict


class DefaultMail(TypedDict):
    name: str
    subject: str
    html: str


LAYOUT_NAME = "Standard-Layout"

# Tables and inline styles: what mail programs (Outlook among them) render reliably.
LAYOUT_HTML = """<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#f4f4f5;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:6px;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;color:#1f2937;">
{% if images.logo_light %}<tr><td style="padding:24px 32px 0;"><img src="{{ images.logo_light }}" alt="{{ company.company_name }}" style="max-height:48px;max-width:240px;"></td></tr>{% endif %}
<tr><td style="padding:24px 32px;">
{% block anrede %}<p>Guten Tag{% if contact.name %} {{ contact.name }}{% endif %},</p>{% endblock %}
{% block inhalt %}{% endblock %}
{% block gruss %}<p>Viele Grüße<br>{{ company.company_name }}</p>{% endblock %}
</td></tr>
<tr><td style="padding:16px 32px;border-top:1px solid #e5e7eb;font-size:12px;color:#6b7280;">
{% block fusszeile %}{{ company.company_name }} · {{ company.street }} · {{ company.postal_code }} {{ company.city }}{% if company.email %} · {{ company.email }}{% endif %}{% endblock %}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

# Per kind: name, subject and the blocks of the layout it fills (the others keep the layout's).
TEMPLATES: dict[str, DefaultMail] = {
    "invoice": {
        "name": "Rechnung",
        "subject": "Rechnung {{ invoice.number }}",
        "html": (
            "{% block inhalt %}\n"
            "<p>anbei erhalten Sie unsere Rechnung {{ invoice.number }} vom "
            "{% display_date invoice.issue_date %} über "
            "{% display_money invoice.total invoice.currency %}.</p>\n"
            "{% if invoice.due_date %}<p>Bitte überweisen Sie den Betrag bis zum "
            "{% display_date invoice.due_date %}"
            "{% if invoice.bank_account.iban %} auf das Konto "
            "{{ invoice.bank_account.iban }}{% endif %}.</p>{% endif %}\n"
            "{% endblock %}"
        ),
    },
    "payment_reminder": {
        "name": "Zahlungserinnerung",
        "subject": "Zahlungserinnerung: Rechnung {{ invoice.number }}",
        "html": (
            "{% block inhalt %}\n"
            "<p>sicher ist es Ihrer Aufmerksamkeit entgangen: Unsere Rechnung "
            "{{ invoice.number }} vom {% display_date invoice.issue_date %} war am "
            "{% display_date invoice.due_date %} fällig. Offen sind noch "
            "{% display_money remaining invoice.currency %}.</p>\n"
            "<p>Bitte überweisen Sie den Betrag in den nächsten Tagen. Hat sich Ihre "
            "Zahlung mit dieser Erinnerung überschnitten, betrachten Sie sie bitte als "
            "gegenstandslos.</p>\n"
            "{% endblock %}"
        ),
    },
}
