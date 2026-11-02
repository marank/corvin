from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django_otp import devices_for_user
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.models import CompanySettings


class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "10/min"


def _verify_otp(user, code: str) -> bool:
    return any(device.verify_token(code) for device in devices_for_user(user, confirmed=True))


def _has_totp(user) -> bool:
    return any(
        devices_for_user(user, confirmed=True),
    )


# DRF's SessionAuthentication only enforces CSRF for authenticated users, so
# the anonymous auth endpoints opt in explicitly (prevents login CSRF).
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        otp_code = request.data.get("otp_code", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if _has_totp(user):
            if not otp_code:
                return Response({"requires_otp": True}, status=status.HTTP_401_UNAUTHORIZED)
            if not _verify_otp(user, otp_code):
                return Response(
                    {"detail": "Invalid code.", "requires_otp": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        login(request, user)
        return Response(_me_payload(user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        get_token(request)
        if not request.user.is_authenticated:
            return Response({"authenticated": False}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(_me_payload(request.user))


def _me_payload(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "totp_enabled": _has_totp(user),
        "authenticated": True,
    }


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        if not django_settings.REGISTRATION_OPEN:
            return Response(
                {"detail": "Registration is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.create_user(**ser.validated_data)
        CompanySettings.objects.get_or_create(user=user)
        login(request, user)
        return Response(_me_payload(user), status=status.HTTP_201_CREATED)
