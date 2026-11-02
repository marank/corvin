# ProjectManager — conventions for contributors and coding agents

Django + DRF backend (`backend/`), Vue 3 + TypeScript SPA with PrimeVue (`frontend/`), Docker Compose for production. `README.md` has setup and commands; read this before changing structure.

## Commands

VS Code tasks (`.vscode/tasks.json`) hold the everyday commands; the README lists the plain equivalents.
- `dev` task: Django :8000 + Vite :5173 → http://localhost:5173.
- `check` task runs what CI runs (`.gitea/workflows/build.yaml`). It must pass before pushing. If you change a check, change it in both files.
- `django: makemigrations` after model changes; commit the migrations.
- Frontend package manager is **pnpm** only. Backend dependencies via `uv add` / `uv add --dev`.

## Backend rules

- One Django app, `core`, split into packages: `models/`, `serializers/`, `views/`, `services/`, `tests/` — one file per model/resource, `__init__.py` re-exports explicitly. Don't grow monolithic modules.
- Every model inherits `core.models.base.UuidModel` or `OwnedModel` (UUIDv7 primary key; `OwnedModel` adds `owner` + timestamps). Order queries explicitly.
- Every user-owned resource is scoped to `request.user` (`OwnedViewSet`). Never return another user's data — also not files: uploads are served only through owner-scoped API actions (`serve_file`), never via a public `/media/` URL.
- Business logic goes in `services/`, not in views or `save()`.
- API under `/api/v1/`, session auth + CSRF (the anonymous auth views opt in with `csrf_protect`). `/api/v1/health` stays unauthenticated at exactly that path (Docker healthcheck, SSL-redirect exemption).
- Configuration only via environment variables (`django-environ` in `config/settings/`); every new variable gets a commented entry in `.env.example`.
- Coverage must not drop below `fail_under` in `pyproject.toml`; raise it when you add tests. No GPL/AGPL/SSPL production dependencies (CI license check).
- GoBD: a finalized invoice's archived PDF/XML (`DocumentArchive`) is immutable. Don't add code paths that rewrite it.

## Frontend rules

- Views in `src/views/<feature>/`, shared components in `src/components/`, client state in Pinia stores, API calls through `src/api/` (`client.ts` sends the CSRF token).
- PrimeVue + Tailwind for UI. All user-facing text through `vue-i18n` (`src/i18n/locales/de.json` and `en.json`, keep both complete).

## Docker / runtime

- `frontend` (nginx) serves the SPA and proxies `/api/` to `backend` (gunicorn). nginx sets `X-Forwarded-For`/`-Proto` itself and trusts them only from `TRUSTED_PROXIES`; Django relies on that (`NUM_PROXIES = 1`, `SECURE_PROXY_SSL_HEADER`).
- `scheduler` runs `process_recurring` daily; `backup` dumps the database and uploads nightly. Anything new that has to run periodically goes into `scheduler`, not a host cron.
