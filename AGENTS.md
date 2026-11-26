# Corvin — conventions for contributors and coding agents

Licensed under AGPL-3.0-or-later (`LICENSE`).

Django + DRF backend (`backend/`), Vue 3 + TypeScript SPA with PrimeVue (`frontend/`), one Docker image (`Dockerfile`, `docker/`) run with Docker Compose (`compose.yml`) in production. Development setup, checks and CI: `docs/development.md`; operations: `docs/operations.md`. Read this before changing structure.

## Commands

The `justfile` holds every command (`just` lists them); CI (`.github/workflows/build.yaml`) and the VS Code tasks only call its recipes.
- `just dev-backend` + `just dev-frontend` (VS Code task `dev`): Django :8000 + Vite :5173 → http://localhost:5173. Native development needs `DEBUG=true` in `.env`.
- `just check` runs what CI runs. It must pass before pushing. A new check goes into the justfile, nowhere else.
- `just migrations` after model changes; commit the migrations.
- `just api-types` after API changes: exports `frontend/openapi.json` and regenerates `frontend/src/api/schema.d.ts`; commit both (`check-backend` and `check-frontend` fail when they drift).
- Frontend package manager is **pnpm** only. Backend dependencies via `uv add` / `uv add --dev`.
- Dependabot doesn't update these — bump by hand: `TRIVY_IMAGE` (tag + digest) and the PostgreSQL major of the CI service in `.github/workflows/build.yaml` (together with `compose.yml` and `PG_MAJOR` in the `Dockerfile`), `SUPERVISOR_VERSION` in the `Dockerfile`, the actionlint and zizmor versions in the justfile, `rust-just==…` in the workflow.
- Lint limits are on tangle, never on length: complexity and cognitive complexity ≤ 15, nesting ≤ 4, import layers (`lint-imports` in the backend, `no-restricted-imports` in the frontend). Split by responsibility when one fires; don't silence it.

## Working rules

- The repo is public: no personal or local terms (names, hostnames, paths, internal labels) in code, comments, commits or PRs.
- Keep UI hints, placeholders and code comments short. No lengthy explanations.
- Commit only when the user says so.

## Backend rules

- One Django app, `core`, split into packages: `models/`, `serializers/`, `views/`, `services/`, `tests/` — one file per model/resource, `__init__.py` re-exports explicitly. Don't grow monolithic modules.
- Every model inherits `core.models.base.UuidModel` or `OwnedModel` (UUIDv7 primary key; `OwnedModel` adds `owner` + timestamps). Order queries explicitly.
- Every user-owned resource is scoped to `request.user` (`OwnedViewSet`). Never return another user's data — also not files: uploads are served only through owner-scoped API actions (`serve_file`), never via a public `/media/` URL.
- Business logic goes in `services/`, not in views or `save()`.
- User-facing API messages go through `gettext` (`_()`); German lives in `core/locale/de/LC_MESSAGES/django.po`. After changing messages run `uv run python ../manage.py makemessages -l de --no-location` in `backend/core`, translate, compile with `msgfmt` (or `compilemessages`) and commit `.po` and `.mo`. API responses follow `Accept-Language`; documents (PDF, previews, mail) always render in `LANGUAGE_CODE`.
- API under `/api/v1/`, session auth + CSRF (the anonymous auth views opt in with `csrf_protect`). `/api/v1/health` stays unauthenticated at exactly that path (Docker healthcheck).
- Configuration only via environment variables, read through `config/env.py` (strict parsers) in the single `config/settings.py`; every new variable gets a commented entry in `.env.example` (the docker compose template for self-hosters), or in the `.env` table of `docs/development.md` if only development or compose's fixed values need it.
- Coverage must not drop below `fail_under` in `pyproject.toml`; raise it when you add tests. The app is AGPL-3.0-or-later: production dependencies must be compatible with it — GPL/AGPL/LGPL are fine, GPL-2.0-only, SSPL and proprietary licenses are not (CI license check, backend and frontend).
- GoBD: a finalized invoice's archived PDF/XML (`DocumentArchive`) is immutable. Don't add code paths that rewrite it.

## Frontend rules

- Views in `src/views/<feature>/`, shared components in `src/components/`, client state in Pinia stores, API calls through `src/api/` (`client.ts` sends the CSRF token).
- PrimeVue 4 + Tailwind for UI. PrimeVue 5, `@primeuix/themes` 3 and `primeicons` 8 are no longer MIT (commercial PrimeUI license with license key) — don't upgrade without a licensing decision. All user-facing text through `vue-i18n` (`src/i18n/locales/de.json` and `en.json`, keep both complete).

## Docker / runtime

- One image (`ghcr.io/marank/corvin`), two services in `compose.yml` besides `db`: `app` runs nginx and gunicorn under supervisord (`docker/supervisord.conf`); `worker` runs the procrastinate job worker (`docker/worker`).
- Background jobs live in `core/tasks.py` (procrastinate, queue in PostgreSQL): invoice mails, recurring invoices daily at `RECURRING_TIME`, backups (pg_dump from `postgresql-client` in the server's major + uploads tarball) daily at `BACKUP_TIME`. Services defer them only through `core.jobs.defer("core.tasks.<name>", …)`, inside the transaction that causes them — never send mails or do slow work in the request, never call `task.defer()` directly. Tasks call services, services never import `core.tasks` (import-linter). Periodic jobs: `@app.periodic` hourly + `_is_due` for local times (procrastinate's cron is UTC). On SQLite (native, tests) there is no queue: jobs run in-process after the commit; tests use `django_capture_on_commit_callbacks(execute=True)`. Nothing periodic goes into a host cron.
- nginx (`docker/app.conf`) serves the SPA and proxies `/api/` to gunicorn on 127.0.0.1:8000. It sets `X-Forwarded-For`/`-Proto` itself and trusts them only from `TRUSTED_PROXIES`; Django relies on that (`NUM_PROXIES = 1`, `SECURE_PROXY_SSL_HEADER`).
- Every container runs as `app` (uid 10001), without capabilities, on a read-only root filesystem. Only the volumes (`/app/media`, `/backups`) and `/tmp` are writable — new features write there instead of loosening `compose.yml`. nginx listens on 8080.
- `docker/smoke-test` is the one smoke test (CI runs it in all three containers); new probes go there.

## Glossary

- **Ledger hourly rates**: `HourlyRate` rows with `valid_from`, scoped project > customer > company default; resolved per entry date at consolidation and snapshotted onto line items.
- **Contract coverage**: `TimeEntry.contract` set = counts against included hours (+ overage if `bill_overage`); unset = normal billable pool invoiced separately via consolidation.
- **GoBD archive**: `finalize` renders PDF/XML once into `DocumentArchive` with SHA-256 — immutable afterward.
- **E-invoice**: `e_invoice_format` = `zugferd` (PDF/A-3 with embedded factur-x XML) or `xrechnung` (XML-only, needs customer `buyer_reference` / Leitweg-ID).

## House defaults

Checked against django-spa-defaults 1.8.1 (2026-11-23). Accepted deviations and settled judgements,
one line each as `- ID: decision and reason`, or `- ID [path, …]: …` for exceptions in some places only
(IDs from the project-defaults checklist); the review does not report these again:

- BE-11: met — `DEBUG = env_bool("DEBUG", False)`; `config.env.secret_key()` refuses a missing, placeholder or short `SECRET_KEY` unless DEBUG is on, and settings refuse an empty `APP_URLS`.
- SEC-01: met — `SECURE_SSL_REDIRECT = False` and `SECURE_HSTS_SECONDS = 0` in `config/settings.py`, no cookie domain, nginx sends no HSTS (the check's pattern flags the explicit off values too).
- BE-04: met with `core.auth_backends.CaseInsensitiveModelBackend` and `username__iexact` lookups (registration, `ensure_admin`, `set_password`); the app lives in `backend/core/`, which the check does not scan.
- DOCKER-03: met — `docker/smoke-test app` probes health and the unauthenticated status at `/api/v1/health` and `/api/v1/auth/me` (the API is versioned), which the check's patterns don't match.

Project decisions (asked once; the review checks against them and asks again only if a line is missing):
- Releases: by hand
- Contributions: team only
