from typing import Any

from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django_otp import devices_for_user
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.request_helpers import request_data, request_user
from core.services.user_setup import set_up_user


class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "10/min"


def _verify_otp(user: User, code: str) -> bool:
    return any(device.verify_token(code) for device in devices_for_user(user, confirmed=True))


def _has_totp(user: User) -> bool:
    return any(
        devices_for_user(user, confirmed=True),
    )


ME = inline_serializer(
    "Me",
    {
        "id": serializers.IntegerField(),
        "username": serializers.CharField(),
        "email": serializers.CharField(),
        "totp_enabled": serializers.BooleanField(),
        "authenticated": serializers.BooleanField(),
    },
)
DETAIL = inline_serializer("Detail", {"detail": serializers.CharField()})


# DRF's SessionAuthentication only enforces CSRF for authenticated users, so
# the anonymous auth endpoints opt in explicitly (prevents login CSRF).
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(
        request=inline_serializer(
            "LoginRequest",
            {
                "username": serializers.CharField(),
                "password": serializers.CharField(),
                "otp_code": serializers.CharField(required=False),
            },
        ),
        responses={
            200: ME,
            401: inline_serializer(
                "LoginFailed",
                {
                    "detail": serializers.CharField(required=False),
                    "requires_otp": serializers.BooleanField(required=False),
                },
            ),
        },
    )
    def post(self, request: Request) -> Response:
        username = request_data(request).get("username", "")
        password = request_data(request).get("password", "")
        otp_code = request_data(request).get("otp_code", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": _("Invalid credentials.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if _has_totp(user):
            if not otp_code:
                return Response({"requires_otp": True}, status=status.HTTP_401_UNAUTHORIZED)
            if not _verify_otp(user, otp_code):
                return Response(
                    {"detail": _("Invalid code."), "requires_otp": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        login(request, user)
        return Response(_me_payload(user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: ME,
            401: inline_serializer("Anonymous", {"authenticated": serializers.BooleanField()}),
        }
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        get_token(request)
        if not request.user.is_authenticated:
            return Response({"authenticated": False}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(_me_payload(request_user(request)))


def _me_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "totp_enabled": _has_totp(user),
        "authenticated": True,
    }


class RegisterSerializer(serializers.Serializer[Any]):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_("Username already taken."))
        return value


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: ME, 403: DETAIL})
    def post(self, request: Request) -> Response:
        if not django_settings.REGISTRATION_ENABLED:
            return Response(
                {"detail": _("Registration is disabled.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.create_user(**ser.validated_data)
        set_up_user(user)
        login(request, user)
        return Response(_me_payload(user), status=status.HTTP_201_CREATED)
