from django.contrib import admin

from core.models import (
    Attachment,
    CompanySettings,
    Contact,
    Customer,
    HourlyRate,
    Invoice,
    InvoiceDocument,
    InvoiceLineItem,
    InvoiceTemplate,
    OnSiteVisit,
    Payment,
    Project,
    SupportContract,
    Task,
    TimeEntry,
)


class LineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "customer", "issue_date", "status", "total"]
    list_filter = ["status"]
    inlines = [LineItemInline, PaymentInline]


for model in (
    Attachment,
    CompanySettings,
    Contact,
    Customer,
    HourlyRate,
    InvoiceDocument,
    InvoiceTemplate,
    OnSiteVisit,
    Project,
    SupportContract,
    Task,
    TimeEntry,
):
    admin.site.register(model)
