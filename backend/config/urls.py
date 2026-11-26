from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

admin.site.site_header = admin.site.site_title = "Corvin"

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/", include("core.urls")),
]

if settings.ADMIN_ENABLED:
    # Under /django-admin, so /admin stays free for the SPA.
    urlpatterns.insert(0, path("django-admin/", admin.site.urls))
