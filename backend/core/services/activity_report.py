"""Activity report (Tätigkeitsbericht): what was done, entry by entry, for the hours an invoice
bills.

Like the time report (time_report.py) it follows the invoice's lines and their entries, but
instead of a table it prints each entry's report (Markdown) under its date, time, project and
duration; an entry without a report shows its description. Rendered on demand, in
LANGUAGE_CODE.
"""

from typing import Any

from django.conf import settings
from django.template import Context, Template
from django.utils.translation import gettext as _
from django.utils.translation import override, pgettext

from core.models import Invoice

from .markdown import render_markdown
from .pdf import write_pdf
from .time_report import report_header

ACTIVITY_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{{ base_style|safe }}
.line { font-weight: 600; background: #f2f2f2; padding: 1.5mm 2mm; margin: 5mm 0 1mm;
  display: flex; justify-content: space-between; break-after: avoid; }
.entry { padding: 2.5mm 2mm 3mm; border-bottom: 0.2mm solid #e5e5e5; }
.entry-head { color: #555; display: flex; gap: 3mm; break-after: avoid; }
.entry-head .duration { margin-left: auto; white-space: nowrap; }
.entry-title { font-size: 10pt; font-weight: 600; margin: 1mm 0 1.5mm; break-after: avoid; }
.report { line-height: 1.45; }
.report > :first-child { margin-top: 0; }
.report > :last-child { margin-bottom: 0; }
.report p, .report ul, .report ol, .report blockquote, .report pre, .report table {
  margin: 0 0 2mm; }
.report h1, .report h2, .report h3, .report h4, .report h5, .report h6 {
  font-size: 9.5pt; margin: 3mm 0 1mm; break-after: avoid; }
.report ul, .report ol { padding-left: 5mm; }
.report blockquote { margin-left: 0; padding-left: 3mm; border-left: 0.6mm solid #ccc;
  color: #555; }
.report code { font-family: "Courier New", monospace; font-size: 8.5pt; background: #f2f2f2;
  padding: 0 0.5mm; }
.report pre { background: #f2f2f2; padding: 2mm; white-space: pre-wrap; }
.report pre code { background: none; padding: 0; }
.report table { border-collapse: collapse; }
.report th, .report td { border: 0.2mm solid #ccc; padding: 1mm 1.5mm; text-align: left; }
.report a { color: inherit; }
.total { display: flex; justify-content: space-between; font-weight: 700; margin-top: 4mm;
  padding: 1.5mm 2mm; border-top: 0.4mm solid #161616; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<div class="meta">{{ invoice_label }} {{ invoice.number }} · {% display_date invoice.issue_date %}
 · {{ customer.name }}</div>
{% for line in lines %}
<div class="line"><span>{{ labels.position }} {{ line.position }}: {{ line.description }}</span>
<span>{{ line.duration }}</span></div>
{% for entry in line.entries %}
<div class="entry">
<div class="entry-head">
<span>{% display_date entry.date %}</span>
<span>{% display_time entry.start %}–{% display_time entry.end %}</span>
{% if entry.project %}<span>{{ entry.project }}</span>{% endif %}
<span class="duration">{{ entry.duration }}</span>
</div>
{% if entry.description %}<div class="entry-title">{{ entry.description }}</div>{% endif %}
{% if entry.report_html %}<div class="report">{{ entry.report_html }}</div>{% endif %}
</div>
{% endfor %}
{% endfor %}
<div class="total"><span>{{ labels.total }}</span><span>{{ total }}</span></div>
</body>
</html>"""


def activity_report_context(invoice: Invoice) -> dict[str, Any]:
    """The time report's lines and entries, each entry's report rendered from Markdown."""
    context = report_header(invoice, _("Activity report"))
    for line in context["lines"]:
        for entry in line["entries"]:
            report = entry["report"].strip()
            entry["report_html"] = render_markdown(report) if report else ""
    return context


def render_activity_report_pdf(invoice: Invoice) -> bytes:
    with override(settings.LANGUAGE_CODE):
        context = Context(
            {
                **activity_report_context(invoice),
                "labels": {
                    "position": pgettext("time report", "Item"),
                    "total": pgettext("time report", "Total"),
                },
            }
        )
        html = Template(ACTIVITY_TEMPLATE).render(context)
    return write_pdf(html, invoice.owner)
