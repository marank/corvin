import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

from core.models import CompanySettings
from core.services.admin_user import ensure_admin

STRONG = "a-Long-and-unguessable-passphrase-42"


@pytest.mark.django_db
def test_creates_superuser_with_company_settings():
    message = ensure_admin("boss", "it@example.com", STRONG)

    user = User.objects.get(username="boss")
    assert "created" in message
    assert user.is_superuser
    assert user.is_staff
    assert user.email == "it@example.com"
    assert user.check_password(STRONG)
    assert CompanySettings.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_existing_user_is_left_alone():
    User.objects.create_user("boss", password="old-password-123")

    message = ensure_admin("boss", "it@example.com", STRONG)

    user = User.objects.get(username="boss")
    assert "exists" in message
    assert user.check_password("old-password-123")
    assert not user.is_superuser


@pytest.mark.django_db
def test_password_is_taken_as_is():
    ensure_admin("boss", "", "change-me")

    assert User.objects.get(username="boss").check_password("change-me")


@pytest.mark.django_db
@pytest.mark.parametrize(("username", "password"), [("", STRONG), ("boss", "")])
def test_empty_username_or_password_creates_nobody(username, password):
    assert "empty" in ensure_admin(username, "", password)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_command_reads_environment(monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_USERNAME", "root")
    monkeypatch.setenv("ADMIN_EMAIL", "root@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", STRONG)

    call_command("ensure_admin")

    assert User.objects.get(username="root").is_superuser
    assert "created" in capsys.readouterr().out


@pytest.fixture
def typed(monkeypatch):
    def answers(*values):
        replies = iter(values)
        monkeypatch.setattr(
            "core.management.commands.set_password.getpass", lambda prompt: next(replies)
        )

    return answers


@pytest.mark.django_db
def test_set_password_takes_any_password(typed, capsys):
    User.objects.create_user("boss", password="old-password-123")
    typed("123", "123")

    call_command("set_password", "boss")

    assert User.objects.get(username="boss").check_password("123")
    assert "changed" in capsys.readouterr().out


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("answers", "error"),
    [(("", ""), "empty"), (("one", "two"), "do not match")],
)
def test_set_password_refuses_empty_or_mismatch(typed, answers, error):
    User.objects.create_user("boss", password="old-password-123")
    typed(*answers)

    with pytest.raises(CommandError, match=error):
        call_command("set_password", "boss")

    assert User.objects.get(username="boss").check_password("old-password-123")


@pytest.mark.django_db
def test_set_password_unknown_user():
    with pytest.raises(CommandError, match="does not exist"):
        call_command("set_password", "nobody")
