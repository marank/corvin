"""Time report (Leistungsnachweis): the time entries an invoice bills, line by line.

Invoice lines may group entries (per day, per project); the report lists every entry behind
them with date, time, project, text and duration, so the customer can follow the hours. It is
rendered on demand from the entries linked to the invoice and always in LANGUAGE_CODE, like
the invoice itself.
"""

from typing import Any

from django.conf import settings
from django.template import Context, Template
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override, pgettext

from core.models import Invoice

from .pdf import write_pdf

# Page, type and title shared with the activity report (activity_report.py).
BASE_STYLE = """
@page { size: A4; margin: 18mm 15mm 18mm 20mm;
  @bottom-right { content: counter(page) " / " counter(pages); font-size: 8pt; color: #777; } }
body { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #161616; }
h1 { font-size: 16pt; margin: 0 0 1mm; }
.meta { color: #555; margin-bottom: 6mm; }
"""

REPORT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{{ base_style|safe }}
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-weight: 600; border-bottom: 0.4mm solid #161616; padding: 1.5mm 1mm; }
td { padding: 1.2mm 1mm; border-bottom: 0.2mm solid #e5e5e5; vertical-align: top; }
.num { text-align: right; white-space: nowrap; }
.nowrap { white-space: nowrap; }
tr.line td { background: #f2f2f2; font-weight: 600; border-bottom: none; padding-top: 2mm; }
tr.total td { font-weight: 700; border-top: 0.4mm solid #161616; border-bottom: none; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<div class="meta">{{ invoice_label }} {{ invoice.number }} · {% display_date invoice.issue_date %}
 · {{ customer.name }}</div>
<table>
<thead><tr>
<th>{{ labels.date }}</th><th>{{ labels.time }}</th><th>{{ labels.project }}</th>
<th>{{ labels.description }}</th><th class="num">{{ labels.duration }}</th>
</tr></thead>
<tbody>
{% for line in lines %}
<tr class="line"><td colspan="4">{{ labels.position }} {{ line.position }}: {{ line.description }}</td>
<td class="num">{{ line.duration }}</td></tr>
{% for entry in line.entries %}
<tr>
<td class="nowrap">{% display_date entry.date %}</td>
<td class="nowrap">{% display_time entry.start %}–{% display_time entry.end %}</td>
<td>{{ entry.project }}</td>
<td>{{ entry.description }}</td>
<td class="num">{{ entry.duration }}</td>
</tr>
{% endfor %}
{% endfor %}
<tr class="total"><td colspan="4">{{ labels.total }}</td><td class="num">{{ total }}</td></tr>
</tbody>
</table>
</body>
</html>"""


def hours(minutes: int) -> str:
    return f"{minutes // 60}:{minutes % 60:02d} h"


def time_report_context(invoice: Invoice) -> dict[str, Any]:
    """The lines with time entries, each with its entries and summed duration."""
    lines = []
    total = 0
    for item in invoice.items.order_by("position").prefetch_related("time_entries__project"):
        entries = sorted(item.time_entries.all(), key=lambda e: e.start_datetime)
        if not entries:
            continue
        minutes = sum(e.duration_minutes for e in entries)
        total += minutes
        lines.append(
            {
                "position": item.position,
                "description": item.description,
                "duration": hours(minutes),
                "entries": [
                    {
                        "date": timezone.localdate(e.start_datetime),
                        "start": timezone.localtime(e.start_datetime),
                        "end": timezone.localtime(e.end_datetime) if e.end_datetime else None,
                        "project": e.project.name if e.project else "",
                        "description": e.description,
                        "report": e.report,
                        "duration": hours(e.duration_minutes),
                    }
                    for e in entries
                ],
            }
        )
    return {"lines": lines, "total": hours(total)}


def report_header(invoice: Invoice, title: str) -> dict[str, Any]:
    """What both reports show above their entries: title, invoice and customer."""
    return {
        **time_report_context(invoice),
        "base_style": BASE_STYLE,
        "invoice": invoice,
        "customer": invoice.customer,
        "company": getattr(invoice.owner, "company_settings", None),
        "title": title,
        "invoice_label": _("Invoice"),
    }


def render_time_report_pdf(invoice: Invoice) -> bytes:
    with override(settings.LANGUAGE_CODE):
        context = Context(
            {
                **report_header(invoice, _("Time report")),
                "labels": {
                    "date": pgettext("time report", "Date"),
                    "time": pgettext("time report", "Time"),
                    "project": pgettext("time report", "Project"),
                    "description": pgettext("time report", "Description"),
                    "duration": pgettext("time report", "Duration"),
                    "position": pgettext("time report", "Item"),
                    "total": pgettext("time report", "Total"),
                },
            }
        )
        html = Template(REPORT_TEMPLATE).render(context)
    return write_pdf(html, invoice.owner)
