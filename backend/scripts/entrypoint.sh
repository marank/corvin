#!/bin/sh
# Container entrypoint of the backend image.
#   no arguments: migrate, create the first administrator (ADMIN_* in .env, only if
#                 missing), then run gunicorn
#   arguments:    run them instead, e.g. the scheduler's daily job or a one-off
#                 `docker compose run --rm backend python manage.py …`
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

python manage.py migrate --noinput
python manage.py ensure_admin
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}"
