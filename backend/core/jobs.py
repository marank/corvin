"""Deferring background jobs (the jobs themselves live in ``core/tasks.py``).

With PostgreSQL (``settings.JOB_QUEUE``) a job goes into the procrastinate queue within the
current transaction: it exists only once the change that caused it is committed, and the
worker runs it, retrying failures. With SQLite (native development, local tests) there is
no queue and no worker: the job runs in-process right after the commit, and a failure is
only logged.

Services defer jobs only through ``defer``, never with ``task.defer()`` directly. Jobs are
named by their dotted path (``"core.tasks.send_invoice_email"``), so services don't import
``core.tasks`` — the tasks call services, not the other way round.
"""

from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string
from procrastinate.contrib.django import app
from procrastinate.exceptions import AlreadyEnqueued


def defer(task_name: str, *, queueing_lock: str | None = None, **kwargs: Any) -> None:
    """Run the task ``task_name`` (dotted path) with ``kwargs`` in the background.

    With ``queueing_lock`` the job is skipped while one with the same lock still waits in
    the queue (e.g. for a retry). Without a queue the lock has no effect.
    """
    if settings.JOB_QUEUE:
        try:
            # A savepoint: a rejected insert must not abort the caller's transaction.
            with transaction.atomic():
                app.configure_task(name=task_name, queueing_lock=queueing_lock).defer(**kwargs)
        except AlreadyEnqueued:
            pass
    else:
        task = import_string(task_name)
        transaction.on_commit(lambda: task(**kwargs), robust=True)
