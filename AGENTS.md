# Corvin — conventions for contributors and coding agents

Licensed under AGPL-3.0-or-later (`LICENSE`).

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
- User-facing API messages go through `gettext` (`_()`); German lives in `core/locale/de/LC_MESSAGES/django.po`. After changing messages run `uv run python ../manage.py makemessages -l de --no-location` in `backend/core`, translate, compile with `msgfmt` (or `compilemessages`) and commit `.po` and `.mo`. API responses follow `Accept-Language`; documents (PDF, previews, mail) always render in `LANGUAGE_CODE`.
- API under `/api/v1/`, session auth + CSRF (the anonymous auth views opt in with `csrf_protect`). `/api/v1/health` stays unauthenticated at exactly that path (Docker healthcheck, SSL-redirect exemption).
- Configuration only via environment variables (`django-environ` in `config/settings/`); every new variable gets a commented entry in `.env.example`.
- Coverage must not drop below `fail_under` in `pyproject.toml`; raise it when you add tests. The app is AGPL-3.0-or-later: production dependencies must be compatible with it — GPL/AGPL/LGPL are fine, GPL-2.0-only, SSPL and proprietary licenses are not (CI license check, backend and frontend).
- GoBD: a finalized invoice's archived PDF/XML (`DocumentArchive`) is immutable. Don't add code paths that rewrite it.

## Frontend rules

- Views in `src/views/<feature>/`, shared components in `src/components/`, client state in Pinia stores, API calls through `src/api/` (`client.ts` sends the CSRF token).
- PrimeVue 4 + Tailwind for UI. PrimeVue 5, `@primeuix/themes` 3 and `primeicons` 8 are no longer MIT (commercial PrimeUI license with license key) — don't upgrade without a licensing decision. All user-facing text through `vue-i18n` (`src/i18n/locales/de.json` and `en.json`, keep both complete).

## Docker / runtime

- `frontend` (nginx) serves the SPA and proxies `/api/` to `backend` (gunicorn). nginx sets `X-Forwarded-For`/`-Proto` itself and trusts them only from `TRUSTED_PROXIES`; Django relies on that (`NUM_PROXIES = 1`, `SECURE_PROXY_SSL_HEADER`).
- Backend, scheduler and frontend run unprivileged (uid 10001 / 101), without capabilities, on a read-only root filesystem. Only volumes (`/app/media`) and `/tmp` are writable — new features write there instead of loosening `docker-compose.yml`. nginx listens on 8080.
- `scheduler` runs `process_recurring` daily; `backup` dumps the database and uploads nightly. Anything new that has to run periodically goes into `scheduler`, not a host cron.
