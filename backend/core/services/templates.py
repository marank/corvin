from core.models import DocumentTemplate

# Covers the §14 Abs. 4 UStG basics: both addresses, VAT ID, number, dates,
# items, net/VAT/gross. Users adapt it in the designer.
DEFAULT_BODY = """<div class="sender">{{ company.company_name }} · {{ company.street }} · {{ company.postal_code }} {{ company.city }}</div>
<div class="recipient">
<b>{{ customer.name }}</b><br>
{{ customer.street }}<br>
{{ customer.postal_code }} {{ customer.city }}<br>
{{ customer.country }}
</div>
<table class="meta">
<tr><td>Rechnungsnummer</td><td>{{ invoice.number }}</td></tr>
<tr><td>Rechnungsdatum</td><td>{{ invoice.issue_date|date:"d.m.Y" }}</td></tr>
{% if invoice.due_date %}<tr><td>Fällig am</td><td>{{ invoice.due_date|date:"d.m.Y" }}</td></tr>{% endif %}
{% if customer.vat_id %}<tr><td>USt-IdNr. Kunde</td><td>{{ customer.vat_id }}</td></tr>{% endif %}
</table>
<h1>Rechnung {{ invoice.number }}</h1>
<p>Leistungsdatum: siehe Positionen</p>
<table class="items">
<thead><tr><th>Pos.</th><th>Beschreibung</th><th>Menge</th><th>Einzelpreis</th><th>Gesamt</th></tr></thead>
<tbody>
{% for item in items %}
<tr><td>{{ item.position }}</td><td>{{ item.description }}</td>
<td>{{ item.quantity }} {% if item.unit == "hours" %}Std.{% elif item.unit == "flat" %}pauschal{% else %}Stk.{% endif %}</td>
<td>{{ item.unit_price }} {{ invoice.currency }}</td>
<td>{{ item.total }} {{ invoice.currency }}</td></tr>
{% endfor %}
</tbody></table>
<table class="totals">
<tr><td>Nettobetrag</td><td>{{ invoice.subtotal }} {{ invoice.currency }}</td></tr>
<tr><td>USt. {{ invoice.vat_rate }} %</td><td>{{ invoice.vat_amount }} {{ invoice.currency }}</td></tr>
<tr><td><b>Gesamtbetrag</b></td><td><b>{{ invoice.total }} {{ invoice.currency }}</b></td></tr>
</table>
{% if company and not company.vat_enabled %}<p>Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</p>{% endif %}
{% if invoice.notes %}<p>{{ invoice.notes|linebreaksbr }}</p>{% endif %}"""

DEFAULT_CSS = """body { font-family: sans-serif; font-size: 10pt; }
.sender { font-size: 7pt; color: #666; margin-bottom: 4mm; }
.recipient { margin-bottom: 10mm; }
.meta { margin-left: auto; margin-bottom: 6mm; }
.meta td:first-child { padding-right: 6mm; color: #666; }
.items { width: 100%; border-collapse: collapse; }
.items td, .items th { border-bottom: 1px solid #ccc; padding: 4px; text-align: left; }
.items td:nth-child(n+3), .items th:nth-child(n+3) { text-align: right; }
.totals { margin-left: auto; margin-top: 4mm; }
.totals td { padding: 2px 0 2px 8mm; text-align: right; }
#page-footer { font-size: 8pt; color: #666; }"""

DEFAULT_FOOTER = (
    "{{ company.company_name }} · {{ company.street }} · "
    "{{ company.postal_code }} {{ company.city }}"
    "{% if invoice.bank_account.iban %} · IBAN {{ invoice.bank_account.iban }}{% endif %}"
    "{% if company.vat_id %} · USt-IdNr. {{ company.vat_id }}{% endif %}"
    "{% if company.tax_id %} · St.-Nr. {{ company.tax_id }}{% endif %}"
)


def ensure_default_template(owner) -> DocumentTemplate:
    """Return the owner's first template, creating the default one if none exists."""
    template = DocumentTemplate.objects.filter(owner=owner).order_by("created_at").first()
    if template is None:
        template = DocumentTemplate.objects.create(
            owner=owner,
            name="Standard (DIN A4)",
            body_html=DEFAULT_BODY,
            css=DEFAULT_CSS,
            footer_html=DEFAULT_FOOTER,
        )
    return template
