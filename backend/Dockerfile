FROM python:3.15-slim

# WeasyPrint runtime deps (Pango + friends)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libjpeg62-turbo \
    libopenjp2-7 libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

# Unprivileged runtime user. The container runs with a read-only root filesystem:
# only /app/media (volume) and /tmp (tmpfs; HOME, so font caches land there) are
# writable.
RUN useradd --system --uid 10001 --no-create-home --home-dir /tmp \
    --shell /usr/sbin/nologin app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/app/.venv/bin:$PATH \
    HOME=/tmp

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
# Static files and bytecode at build time: nothing can be written at runtime.
RUN python manage.py collectstatic --noinput --settings=config.settings.production && \
    python -m compileall -q config core && \
    mkdir -p media && chown app:app media

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "scripts/healthcheck.py"]
# Migrations, first administrator, gunicorn; or the command given (scheduler).
ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
