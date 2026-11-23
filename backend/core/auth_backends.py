from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest


class CaseInsensitiveModelBackend(ModelBackend):
    """Django's model backend, but "Admin" signs in as "admin".

    Registration refuses names that differ only in case, so the lookup finds at most one user.
    """

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)
        if username is None or password is None:
            return None
        user = user_model._default_manager.filter(username__iexact=username).first()
        if user is None:
            # Run the hasher anyway, so response times don't reveal which names exist.
            user_model().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
