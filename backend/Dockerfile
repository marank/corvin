FROM python:3.14-slim

# WeasyPrint runtime deps (Pango + friends)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libjpeg62-turbo \
    libopenjp2-7 libffi-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv run --no-sync python manage.py collectstatic --noinput \
    --settings=config.settings.production

EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync python manage.py migrate --settings=config.settings.production && uv run --no-sync gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
