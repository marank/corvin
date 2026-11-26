"""Background jobs, run by ``manage.py procrastinate worker`` (the ``worker`` container).

Services defer jobs inside the transaction that causes them, always through
``core.jobs.defer("core.tasks.<name>", ...)``: with PostgreSQL the job exists only once the
change is committed; with SQLite (native development) it runs in-process after the commit.
The periodic jobs only run where there is a worker, i.e. with PostgreSQL. Procrastinate's
cron runs in UTC, so the daily jobs come every hour and act only in the hour that is their
time of day in ``TIME_ZONE``.
"""

import logging
from datetime import UTC, datetime, time

from django.conf import settings
from django.utils import timezone
from procrastinate import JobContext, RetryStrategy
from procrastinate.contrib.django import app

from core.services import backups, contracts, mailer

logger = logging.getLogger(__name__)


def _is_due(timestamp: int, at: time) -> bool:
    """Whether the hourly run at ``timestamp`` (UTC) is the one for ``at`` in TIME_ZONE."""
    return timezone.localtime(datetime.fromtimestamp(timestamp, UTC)).hour == at.hour


# SMTP servers fail now and then: retried after 2, 4, 8, … seconds, for about 18 hours in
# all, before the job counts as failed.
@app.task(retry=RetryStrategy(max_attempts=15, exponential_wait=2))
def send_invoice_email(
    invoice_id: str,
    to: list[str] | str,
    subject: str,
    html: str = "",
    text: str = "",
    images: list[str] | None = None,
    kind: str = "invoice",
    body: str = "",
) -> None:
    mailer.send_invoice_email(invoice_id, to, subject, html, text, images, kind, body)


@app.periodic(cron=f"{settings.RECURRING_TIME.minute} * * * *")
@app.task(queueing_lock="process_recurring")
def process_recurring(timestamp: int) -> None:
    """Daily at ``RECURRING_TIME``: draft invoices for due support contracts. Idempotent,
    so a retried or repeated run never bills twice."""
    if _is_due(timestamp, settings.RECURRING_TIME):
        invoices = contracts.process_due()
        logger.info("Recurring invoices: %d created", len(invoices))


@app.periodic(cron=f"{settings.BACKUP_TIME.minute} * * * *")
@app.task(queueing_lock="backup")
def backup(timestamp: int) -> None:
    """Daily at ``BACKUP_TIME``: database dump and uploads into ``BACKUP_DIR``."""
    if settings.BACKUP_DIR and _is_due(timestamp, settings.BACKUP_TIME):
        backups.backup()


@app.periodic(cron="30 3 * * *")
@app.task(pass_context=True)
async def remove_old_jobs(context: JobContext, timestamp: int) -> None:
    """Finished jobs hold recipients and mail texts; keep them only briefly."""
    manager = context.app.job_manager
    await manager.delete_old_jobs(nb_hours=24)
    await manager.delete_old_jobs(
        nb_hours=14 * 24, include_failed=True, include_cancelled=True, include_aborted=True
    )
