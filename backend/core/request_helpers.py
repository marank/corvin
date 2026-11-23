"""Typed access to the parts of a DRF request the views use."""

from collections.abc import Mapping
from typing import Any, cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework.request import Request


def request_user(request: Request | HttpRequest) -> User:
    """The signed-in user of a request that passed IsAuthenticated (typing helper only)."""
    return cast(User, request.user)


def request_data(request: Request) -> Mapping[str, Any]:
    """The request body as a mapping; a JSON array or scalar body counts as empty."""
    data = request.data
    return data if isinstance(data, Mapping) else {}
