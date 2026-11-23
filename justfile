# Corvin's commands — the one place they live. CI (.github/workflows/build.yaml) and the
# VS Code tasks (.vscode/tasks.json) call these recipes, so a check is changed here and
# nowhere else. `just` lists them. Needs just >= 1.38 (working-directory attribute).

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# List the recipes
default:
    @just --list

# --- Setup --------------------------------------------------------------------------

# Install all dependencies
setup: setup-backend setup-frontend

[working-directory: 'backend']
setup-backend:
    uv sync

[working-directory: 'frontend']
setup-frontend:
    pnpm install

# --- Development ----------------------------------------------------------------------

# Django on :8000 (needs DEBUG=true in .env)
[working-directory: 'backend']
dev-backend:
    uv run python manage.py runserver

# Vite on :5173, proxying /api to Django
[working-directory: 'frontend']
dev-frontend:
    pnpm dev

# Apply migrations and create the first admin
[working-directory: 'backend']
migrate:
    uv run python manage.py migrate
    uv run python manage.py ensure_admin

# After model changes; commit the migrations
[working-directory: 'backend']
migrations:
    uv run python manage.py makemigrations

# After API changes: schema -> frontend/openapi.json -> src/api/schema.d.ts; commit both
[working-directory: 'frontend']
api-types: api-schema
    pnpm api:types

[working-directory: 'backend']
api-schema:
    uv run python scripts/check_openapi.py --write

# After new backend texts; then translate core/locale/de/LC_MESSAGES/django.po
[working-directory: 'backend/core']
messages:
    uv run python ../manage.py makemessages -l de --no-location

[working-directory: 'backend/core']
compile-messages:
    msgfmt -o locale/de/LC_MESSAGES/django.mo locale/de/LC_MESSAGES/django.po

# --- Checks (= CI) --------------------------------------------------------------------

# Everything CI checks; must pass before a push
check: check-backend check-deploy check-frontend check-workflows

# ruff, mypy, cognitive complexity, import layers, deptry, licenses, migrations, Django checks, OpenAPI, tests
[working-directory: 'backend']
check-backend: check-backend-licenses
    uv sync --locked
    uv run ruff check --output-format=concise .
    uv run ruff format --check .
    uv run mypy .
    uv run complexipy
    uv run lint-imports
    uv run deptry .
    uv run python manage.py makemigrations --check --dry-run
    uv run python manage.py check --fail-level WARNING
    uv run python scripts/check_openapi.py
    uv run pytest -q --cov

# Production dependencies must be compatible with AGPL-3.0-or-later (scripts/check_licenses.py)
[working-directory: 'backend']
check-backend-licenses:
    #!/usr/bin/env sh
    set -eu
    dir=$(mktemp -d)
    trap 'rm -rf "$dir"' EXIT
    uv export --locked --no-dev --no-hashes --format requirements.txt -o "$dir/requirements.txt"
    uv venv --quiet "$dir/venv"
    uv pip install --quiet --python "$dir/venv" -r "$dir/requirements.txt" pip-licenses
    "$dir/venv/bin/pip-licenses" --format=json --ignore-packages pip-licenses prettytable wcwidth \
      | uv run python scripts/check_licenses.py

# Django's deploy checks with production settings (deploy-check.env)
[working-directory: 'backend']
check-deploy:
    uv run --env-file deploy-check.env python manage.py check --deploy --fail-level WARNING

# formatting, lint, types, tests + coverage, duplication, API types, build, bundle size, licenses, audit
[working-directory: 'frontend']
check-frontend:
    pnpm install --frozen-lockfile
    pnpm check
    pnpm api:types
    git diff --exit-code -- src/api/schema.d.ts
    pnpm build-only
    pnpm size
    pnpm check:licenses
    pnpm audit --prod --audit-level high

# GitHub workflows: syntax (actionlint) and security (zizmor)
check-workflows:
    uvx --from actionlint-py==1.7.12.25 actionlint
    uvx zizmor@1.33.1 .github/

# Platforms near the end of their security support (Python, Node.js, PostgreSQL, Django).
# Not in `check`: it needs the network and its result changes with the date (weekly in CI).
[working-directory: 'backend']
check-eol:
    uv run --no-project python scripts/check_eol.py

# --- Docker ----------------------------------------------------------------------------

# Build the image from the checkout and start the production-like stack with it
docker-up $APP_IMAGE="corvin":
    docker build -t corvin .
    docker compose up -d

docker-down:
    docker compose down

# Dump the database and uploads now (the backup service does it nightly)
docker-backup:
    docker compose exec backup sh /usr/local/bin/backup now
