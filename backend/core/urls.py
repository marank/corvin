from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views.attachment import AttachmentViewSet
from core.views.auth import LoginView, LogoutView, MeView, RegisterView
from core.views.bank_account import BankAccountViewSet
from core.views.company_contact import CompanyContactViewSet
from core.views.company_image import CompanyImageViewSet
from core.views.customer import (
    AddressViewSet,
    ContactViewSet,
    CustomerViewSet,
)
from core.views.document_template import DocumentTemplateViewSet
from core.views.health import HealthView
from core.views.hourly_rate import HourlyRateViewSet
from core.views.invoice import InvoiceViewSet
from core.views.invoice_line_item import InvoiceLineItemViewSet
from core.views.payment import PaymentViewSet
from core.views.project import ProjectViewSet
from core.views.security import (
    ChangePasswordView,
    SessionListView,
    TotpConfirmView,
    TotpDisableView,
    TotpSetupView,
)
from core.views.settings import CompanySettingsView, NumberPreviewView
from core.views.stats import DashboardStatsView
from core.views.support_contract import SupportContractViewSet
from core.views.task import TaskViewSet
from core.views.text_block import TextBlockViewSet
from core.views.time_entry import TimeEntryViewSet
from core.views.visit import OnSiteVisitViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("company-images", CompanyImageViewSet, basename="company-image")
router.register("company-contacts", CompanyContactViewSet, basename="company-contact")
router.register("contacts", ContactViewSet, basename="contact")
router.register("addresses", AddressViewSet, basename="address")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("text-blocks", TextBlockViewSet, basename="text-block")
router.register("visits", OnSiteVisitViewSet, basename="visit")
router.register("time-tracking", TimeEntryViewSet, basename="time-tracking")
router.register("hourly-rates", HourlyRateViewSet, basename="hourly-rate")
router.register("support-contracts", SupportContractViewSet, basename="support-contract")
router.register("document-templates", DocumentTemplateViewSet, basename="document-template")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-items", InvoiceLineItemViewSet, basename="invoice-item")
router.register("payments", PaymentViewSet, basename="payment")
router.register("attachments", AttachmentViewSet, basename="attachment")

urlpatterns = [
    path("health", HealthView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/me", MeView.as_view()),
    path("auth/register", RegisterView.as_view()),
    path("auth/password/change", ChangePasswordView.as_view()),
    path("security/totp/setup", TotpSetupView.as_view()),
    path("security/totp/confirm", TotpConfirmView.as_view()),
    path("security/totp/disable", TotpDisableView.as_view()),
    path("security/sessions", SessionListView.as_view()),
    path("settings/", CompanySettingsView.as_view()),
    path("settings/preview-number/", NumberPreviewView.as_view()),
    path("stats/dashboard", DashboardStatsView.as_view()),
    path("", include(router.urls)),
]
