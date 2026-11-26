"""Background jobs: deferring, the periodic tasks and the backups they write."""

import os
import tarfile
import time
from datetime import UTC, datetime
from datetime import time as clock
from pathlib import Path
from unittest import mock

import pytest
from django.core.management import CommandError, call_command
from django.db import transaction
from procrastinate.exceptions import AlreadyEnqueued

from core import jobs, tasks
from core.services import backups


def _ts(year: int, month: int, day: int, hour: int) -> int:
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp())


# --- defer ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_defer_without_queue_runs_after_commit(settings, django_capture_on_commit_callbacks):
    settings.JOB_QUEUE = False
    with (
        mock.patch("core.tasks.backups.backup") as run_backup,
        django_capture_on_commit_callbacks(execute=True) as callbacks,
    ):
        settings.BACKUP_DIR = "/backups"
        settings.BACKUP_TIME = clock(1, 30)
        jobs.defer("core.tasks.backup", timestamp=_ts(2026, 1, 15, 0))  # 01:00 in Berlin
        run_backup.assert_not_called()  # not before the commit
    assert len(callbacks) == 1
    run_backup.assert_called_once_with()


def _defer_mail_then_fail() -> None:
    with transaction.atomic():
        jobs.defer("core.tasks.send_invoice_email", invoice_id="x", to="a@b.c", subject="", body="")
        raise RuntimeError


@pytest.mark.django_db(transaction=True)
def test_defer_without_queue_skips_job_when_transaction_rolls_back(settings):
    settings.JOB_QUEUE = False
    with mock.patch("core.tasks.mailer.send_invoice_email") as send:
        with pytest.raises(RuntimeError):
            _defer_mail_then_fail()
        send.assert_not_called()


def test_defer_with_queue_enqueues_by_name(settings):
    settings.JOB_QUEUE = True
    with mock.patch("core.jobs.app") as app, mock.patch("core.jobs.transaction"):
        jobs.defer("core.tasks.process_recurring", queueing_lock="lock", timestamp=1)
    app.configure_task.assert_called_once_with(
        name="core.tasks.process_recurring", queueing_lock="lock"
    )
    app.configure_task.return_value.defer.assert_called_once_with(timestamp=1)


def test_defer_with_queue_ignores_job_already_waiting(settings):
    settings.JOB_QUEUE = True
    with mock.patch("core.jobs.app") as app, mock.patch("core.jobs.transaction"):
        app.configure_task.return_value.defer.side_effect = AlreadyEnqueued("waiting")
        jobs.defer("core.tasks.backup", queueing_lock="backup", timestamp=1)  # no exception


# --- periodic tasks --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("timestamp", "due"),
    [
        (_ts(2026, 1, 15, 5), True),  # 06:00 in Berlin (CET)
        (_ts(2026, 7, 15, 4), True),  # 06:00 in Berlin (CEST)
        (_ts(2026, 7, 15, 5), False),  # 07:00 in summer
        (_ts(2026, 1, 15, 6), False),
    ],
)
def test_process_recurring_runs_only_in_its_local_hour(settings, timestamp, due):
    settings.TIME_ZONE = "Europe/Berlin"
    settings.RECURRING_TIME = clock(6, 0)
    with mock.patch("core.tasks.contracts.process_due", return_value=[]) as process_due:
        tasks.process_recurring(timestamp=timestamp)
    assert process_due.called is due


def test_backup_task_does_nothing_without_backup_dir(settings):
    settings.BACKUP_DIR = ""
    settings.BACKUP_TIME = clock(1, 30)
    with mock.patch("core.tasks.backups.backup") as run_backup:
        tasks.backup(timestamp=_ts(2026, 1, 15, 0))
    run_backup.assert_not_called()


def test_send_invoice_email_task_delegates_to_mailer():
    with mock.patch("core.tasks.mailer.send_invoice_email") as send:
        tasks.send_invoice_email(
            invoice_id="id", to="a@b.c", subject="S", html="<p>H</p>", text="H"
        )
    send.assert_called_once_with("id", "a@b.c", "S", "<p>H</p>", "H", None, "invoice", "")


# --- backups ---------------------------------------------------------------------------


def _fake_pg_dump(args, **kwargs):
    target = next(arg.removeprefix("--file=") for arg in args if arg.startswith("--file="))
    Path(target).write_bytes(b"PGDMP")


@pytest.fixture
def backup_dirs(settings, tmp_path):
    media = tmp_path / "media"
    (media / "attachments").mkdir(parents=True)
    (media / "attachments" / "contract.pdf").write_bytes(b"%PDF")
    settings.MEDIA_ROOT = str(media)
    settings.BACKUP_DIR = str(tmp_path / "backups")
    settings.BACKUP_KEEP_DAYS = 14
    return tmp_path / "backups"


@pytest.mark.django_db
def test_backup_writes_dump_and_uploads(backup_dirs):
    with mock.patch("core.services.backups.subprocess.run", side_effect=_fake_pg_dump) as run:
        dump, media = backups.backup()
    assert run.call_args.args[0][:2] == ["pg_dump", "--format=custom"]
    assert run.call_args.kwargs["umask"] == 0o077
    assert dump.read_bytes() == b"PGDMP"
    with tarfile.open(media) as tar:
        assert "./attachments/contract.pdf" in tar.getnames()
    assert media.stat().st_mode & 0o777 == 0o600
    assert not list(backup_dirs.glob("*.partial"))


@pytest.mark.django_db
def test_failed_dump_leaves_no_partial_file(backup_dirs):
    import subprocess

    error = subprocess.CalledProcessError(1, "pg_dump", stderr="connection refused")
    with (
        mock.patch("core.services.backups.subprocess.run", side_effect=error),
        pytest.raises(backups.BackupError, match="connection refused"),
    ):
        backups.backup()
    assert not list(backup_dirs.glob("*"))


def test_remove_old_backups_keeps_recent_ones(settings, tmp_path):
    settings.BACKUP_KEEP_DAYS = 14
    old = time.time() - 15 * 86400
    files = {
        name: tmp_path / name
        for name in ("old.dump", "old.tar.gz", "new.dump", "stale.partial", "fresh.partial")
    }
    for path in files.values():
        path.write_bytes(b"x")
    for name in ("old.dump", "old.tar.gz", "stale.partial"):
        os.utime(files[name], (old, old))

    removed = backups.remove_old_backups(tmp_path)

    assert {path.name for path in removed} == {"old.dump", "old.tar.gz", "stale.partial"}
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fresh.partial", "new.dump"]


@pytest.mark.django_db
def test_backup_command_refuses_without_postgres(settings):
    settings.BACKUP_DIR = "/backups"
    with (
        mock.patch("core.services.backups.available", return_value=False),
        pytest.raises(CommandError, match="PostgreSQL"),
    ):
        call_command("backup_database")


@pytest.mark.django_db
def test_backup_command_refuses_without_backup_dir(settings):
    settings.BACKUP_DIR = ""
    with (
        mock.patch("core.services.backups.available", return_value=True),
        pytest.raises(CommandError, match="BACKUP_DIR"),
    ):
        call_command("backup_database")


@pytest.mark.django_db
def test_backup_command_reports_files(backup_dirs, capsys):
    with (
        mock.patch("core.services.backups.available", return_value=True),
        mock.patch("core.services.backups.subprocess.run", side_effect=_fake_pg_dump),
    ):
        call_command("backup_database")
    assert capsys.readouterr().out.count("Written") == 2


def test_send_invoice_mail_task_delegates_to_mailer():
    with mock.patch("core.tasks.mailer.send_invoice_mail") as send:
        tasks.send_invoice_mail(mail_id="m")
    send.assert_called_once_with("m")
