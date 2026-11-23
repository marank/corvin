from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase


class PermissionsPolicyMiddleware:
    """Sends settings.PERMISSIONS_POLICY with every response Django makes."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        response.headers.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        return response
