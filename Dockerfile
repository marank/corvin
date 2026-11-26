# syntax=docker/dockerfile:1

# Corvin in one image: nginx serves the SPA and proxies /api/ to gunicorn/Django, both under
# supervisord. The same image runs the job worker (mails, recurring invoices, nightly
# backups) with a different command (compose.yml).

# Versions in one place. Images are pinned by tag and digest (of the multi-platform
# index, so amd64 and arm64 builds use the same pin); Dependabot updates both. PG_MAJOR
# follows the postgres major in compose.yml.
ARG PG_MAJOR=18
ARG SUPERVISOR_VERSION=4.3.0

# --- 1. Build the SPA ------------------------------------------------------------
FROM node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# pnpm in the version of packageManager in package.json (the one place it is set).
RUN npm install -g "$(node -p "require('./package.json').packageManager.split('+')[0]")" \
 && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

# --- project: build stages ---
# uv, only to install the backend's packages; a stage of its own so Dependabot sees the pin.
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv
# --- end ---

# --- 2. Runtime: supervisord → nginx + gunicorn/Django; the same image runs the worker -
# Named "runtime": CI builds it without cache (no-cache-filters), so system package updates
# are never held back.
FROM python:3.15-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS runtime
ARG PG_MAJOR
ARG SUPERVISOR_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/tmp \
    DATA_DIR=/data \
    BACKUP_DIR=/backups

# nginx; gettext-base for envsubst (start-nginx), gettext for compilemessages;
# postgresql-client from PostgreSQL's own repository in the server's major, so pg_dump
# (nightly backups) accepts the server. curl only for the key and removed again.
# supervisord lives outside the app's venv: it's infrastructure, not an app dependency.
# pip is not needed at runtime. setuid/setgid bits are removed; nothing in the container
# may gain privileges. /data and /backups belong to "app", so fresh volumes mounted there
# are writable.
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends nginx gettext-base gettext curl ca-certificates \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/keyrings/pgdg.asc \
 && echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends "postgresql-client-${PG_MAJOR}" \
 && apt-get purge -y curl && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled /etc/nginx/conf.d \
 && pip install --no-cache-dir --root-user-action=ignore "supervisor==${SUPERVISOR_VERSION}" \
 && pip uninstall -y --root-user-action=ignore pip \
 && groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home --shell /usr/sbin/nologin app \
 && install -d -o app -g app -m 0700 /data /backups \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} +

# --- project: system packages ---
# WeasyPrint's native libraries (Pango and friends).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libjpeg62-turbo libopenjp2-7 \
 && rm -rf /var/lib/apt/lists/* \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} +
# --- end ---

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    --mount=type=cache,target=/tmp/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
# The app's own modules too: the root filesystem is read-only at runtime, so Python could not
# cache them there. Settings need APP_URLS and a strong key without DEBUG; throwaway values
# are enough at build time.
RUN python -m compileall -q config core \
 && SECRET_KEY="build-only-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')" DB_PASSWORD=unused \
    APP_URLS=http://localhost \
    sh -c 'python manage.py collectstatic --noinput && python manage.py compilemessages --ignore=.venv'

COPY --from=frontend /frontend/dist /srv/spa
COPY docker/nginx.conf docker/django_proxy.conf docker/security_headers.conf /etc/nginx/
COPY docker/app.conf.template /etc/nginx/app.conf.template
COPY docker/supervisord.conf docker/gunicorn.conf.py /etc/
COPY docker/entrypoint.sh docker/start-nginx docker/exit-on-fatal docker/healthcheck docker/smoke-test docker/worker /usr/local/bin/

# Everything above is owned by root and read-only for "app"; only /data, /backups and /tmp are written.
USER app
EXPOSE 8080
VOLUME ["/data", "/backups"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD ["python", "/usr/local/bin/healthcheck"]
# entrypoint.sh: deploy checks, migrate, first admin, then supervisord. CMD, not ENTRYPOINT: the
# worker service replaces it with its own command.
CMD ["sh", "/usr/local/bin/entrypoint.sh"]
