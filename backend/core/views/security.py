import secrets
import string

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.translation import gettext as _
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class ChangePasswordView(APIView):
    def post(self, request):
        user = request.user
        old = request.data.get("old_password", "")
        new = request.data.get("new_password", "")
        if not user.check_password(old):
            return Response(
                {"old_password": [_("Wrong password.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new) < 8:
            return Response(
                {"new_password": [_("At least 8 characters.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new)
        user.save()
        # kill other sessions, keep the current one
        _delete_other_sessions(user, request.session.session_key)
        update_session_auth_hash(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TotpSetupView(APIView):
    """Create an unconfirmed TOTP device and return the provisioning URI."""

    def post(self, request):
        device = TOTPDevice.objects.filter(
            user=request.user, confirmed=False
        ).first() or TOTPDevice.objects.create(user=request.user, name="default", confirmed=False)
        return Response({"config_url": device.config_url})


class TotpConfirmView(APIView):
    def post(self, request):
        code = request.data.get("code", "")
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device or not device.verify_token(code):
            return Response({"code": [_("Invalid code.")]}, status=status.HTTP_400_BAD_REQUEST)
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        # generate one-time backup codes
        static, _created = StaticDevice.objects.get_or_create(user=request.user, name="backup")
        static.token_set.all().delete()
        alphabet = string.ascii_lowercase + string.digits
        codes = ["".join(secrets.choice(alphabet) for _i in range(10)) for _j in range(10)]
        StaticToken.objects.bulk_create(StaticToken(device=static, token=c) for c in codes)
        return Response({"backup_codes": codes})


class TotpDisableView(APIView):
    def post(self, request):
        if not request.user.check_password(request.data.get("password", "")):
            return Response(
                {"password": [_("Wrong password.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        TOTPDevice.objects.filter(user=request.user).delete()
        StaticDevice.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _user_sessions(user: User):
    """Active sessions belonging to a user."""
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user.pk):
            yield session


def _delete_other_sessions(user: User, keep_key: str | None):
    for session in _user_sessions(user):
        if session.session_key != keep_key:
            session.delete()


class SessionListView(APIView):
    def get(self, request):
        sessions = [
            {
                "key": s.session_key,
                "expire_date": s.expire_date,
                "current": s.session_key == request.session.session_key,
            }
            for s in _user_sessions(request.user)
        ]
        return Response(sessions)

    def delete(self, request):
        key = request.data.get("key")
        if key and key != request.session.session_key:
            Session.objects.filter(session_key=key).delete()
        elif request.data.get("all"):
            _delete_other_sessions(request.user, request.session.session_key)
        return Response(status=status.HTTP_204_NO_CONTENT)
