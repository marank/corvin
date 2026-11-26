#!/bin/sh
# Start of the app container. It is the image's CMD (not its ENTRYPOINT), so the worker
# service's own `command` replaces it and the worker never migrates.
#
# Brings the database and the first admin up to date once, then hands over to supervisord
# (PID 1), which only supervises nginx and gunicorn. A failing check or migration stops the
# container before anything is served, and the restart policy tries again; a gunicorn
# restart inside the running container no longer migrates a second time.
set -eu
cd /app
python manage.py check --deploy --fail-level ERROR
python manage.py migrate --noinput
python manage.py ensure_admin
exec supervisord -c /etc/supervisord.conf
