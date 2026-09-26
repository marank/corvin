from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views.attachment import AttachmentViewSet
from core.views.auth import LoginView, LogoutView, MeView, RegisterView
from core.views.customer import ContactViewSet, CustomerViewSet
from core.views.hourly_rate import HourlyRateViewSet
from core.views.invoice import InvoiceViewSet
from core.views.invoice_template import InvoiceTemplateViewSet
from core.views.payment import PaymentViewSet
from core.views.project import ProjectViewSet
from core.views.security import (
    ChangePasswordView,
    SessionListView,
    TotpConfirmView,
    TotpDisableView,
    TotpSetupView,
)
from core.views.settings import CompanySettingsView
from core.views.stats import DashboardStatsView
from core.views.support_contract import SupportContractViewSet
from core.views.task import TaskViewSet
from core.views.time_entry import TimeEntryViewSet
from core.views.visit import OnSiteVisitViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("contacts", ContactViewSet, basename="contact")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("visits", OnSiteVisitViewSet, basename="visit")
router.register("time-entries", TimeEntryViewSet, basename="time-entry")
router.register("hourly-rates", HourlyRateViewSet, basename="hourly-rate")
router.register(
    "support-contracts", SupportContractViewSet, basename="support-contract"
)
router.register(
    "invoice-templates", InvoiceTemplateViewSet, basename="invoice-template"
)
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")
router.register("attachments", AttachmentViewSet, basename="attachment")

urlpatterns = [
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
    path("stats/dashboard", DashboardStatsView.as_view()),
    path("", include(router.urls)),
]
