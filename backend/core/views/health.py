from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

_HEALTH = inline_serializer("HealthStatus", {"status": serializers.CharField()})


class HealthView(APIView):
    """Unauthenticated liveness probe for Docker and CI; also checks the database."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(responses={200: _HEALTH, 503: _HEALTH})
    def get(self, request: Request) -> Response:
        try:
            connection.ensure_connection()
        except DatabaseError:
            return Response(
                {"status": "database unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok"})
