from typing import TYPE_CHECKING

from django.contrib import admin

from core.models import (
    Attachment,
    CompanySettings,
    Contact,
    Customer,
    DocumentArchive,
    DocumentTemplate,
    HourlyRate,
    Invoice,
    InvoiceLineItem,
    OnSiteVisit,
    Payment,
    Project,
    SupportContract,
    Task,
    TimeEntry,
)

# Django's admin classes are generic only in django-stubs, not at runtime.
if TYPE_CHECKING:
    LineItemInlineBase = admin.TabularInline[InvoiceLineItem, Invoice]
    PaymentInlineBase = admin.TabularInline[Payment, Invoice]
    InvoiceAdminBase = admin.ModelAdmin[Invoice]
else:
    LineItemInlineBase = PaymentInlineBase = admin.TabularInline
    InvoiceAdminBase = admin.ModelAdmin


class LineItemInline(LineItemInlineBase):
    model = InvoiceLineItem
    extra = 0


class PaymentInline(PaymentInlineBase):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(InvoiceAdminBase):
    list_display = ["number", "customer", "issue_date", "status", "total"]
    list_filter = ["status"]
    inlines = [LineItemInline, PaymentInline]


for model in (
    Attachment,
    CompanySettings,
    Contact,
    Customer,
    HourlyRate,
    DocumentArchive,
    DocumentTemplate,
    OnSiteVisit,
    Project,
    SupportContract,
    Task,
    TimeEntry,
):
    admin.site.register(model)
