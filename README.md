# Corvin

Project management for IT consultants: customers, projects with budgets, tasks, time tracking (live timer + rounding), on-site visit reports, support contracts with included-hours retainers, invoices (A4/Letter PDF, ZUGFeRD/XRechnung e-invoicing, email delivery, GoBD archiving, partial payments), TOTP security, analytics dashboard — German/English, dark mode, mobile responsive.

## Stack

- **Backend**: Django 6.1 + DRF, single `core` app with split `models/` `serializers/` `views/` `services/` packages, `uv`-managed, SQLite dev / Postgres prod, WeasyPrint PDFs, drafthorse EN-16931 XML.
- **Frontend**: Vue 3.5 + TS + Vite, `pnpm`, PrimeVue + Tailwind, flat square UI, `vue-i18n` (de/en), Pinia, Chart.js.

## Branding

Name **Corvin**, from Latin *corvus*, the raven: Odin's ravens Hugin and Munin stand for thought and memory, and the *Bibliotheca Corviniana* was one of the great archives of the Renaissance. Mark: a raven head from basic shapes, a half circle in violet and blue with a cyan beak (`branding/corvin-mark.svg`). Wordmark in Space Grotesk 600 (OFL-1.1, self-hosted via `@fontsource/space-grotesk`). In the app: `src/components/ui/AppLogo.vue`; `frontend/public/favicon.svg` adapts to dark mode.

`branding/` holds the mark (SVG, PNG 256/512, multi-size ICO), the lockup with the wordmark as outlines (`corvin-logo.svg`, `corvin-logo-white.svg` for dark backgrounds, PNG) and the link-preview image. `frontend/public/` gets `favicon.ico`, the manifest icons (`icon-192/512.png`, `icon-maskable-512.png`), `apple-touch-icon.png`, `og-image.png` and `manifest.webmanifest` (PWA install on Android/desktop). All raster files come from `scripts/brand-assets.py` (usage in its docstring) — change the mark there and rerun instead of editing PNGs by hand.

## Local development (Windows, no Docker)

Prerequisites: [uv](https://docs.astral.sh/uv/), Node 26 LTS with corepack (`npm install -g corepack`; the pnpm version comes from `package.json`), Docker for production.

1. `scripts/setup-windows-dev.ps1` — one-time: installs MSYS2 + Pango (WeasyPrint native deps). Custom path? Set `MSYS2_BIN_DIR` in `.env`.
2. Backend:
   ```powershell
   cd backend
   uv sync
   uv run python manage.py migrate
   uv run python manage.py createsuperuser   # or ensure_admin with ADMIN_* from .env
   uv run python manage.py runserver
   ```
3. Frontend:
   ```powershell
   cd frontend
   pnpm install
   pnpm dev          # http://localhost:5173, proxies /api to :8000
   ```

Dev uses SQLite + console email backend. PDFs work once Pango is installed (`uv run python -c "import weasyprint"` verifies).

## Production (Linux, Docker Compose)

```bash
cp .env.example .env   # every variable is explained there; set at least APP_URLS,
                       # SECRET_KEY, DB_PASSWORD, ADMIN_PASSWORD, TRUSTED_PROXIES, SMTP
docker compose up -d --build   # creates the ADMIN_USERNAME account on first start
```

| Service | Purpose |
|---|---|
| `db` | PostgreSQL 18 |
| `backend` | gunicorn/Django, healthcheck on `/api/v1/health` |
| `frontend` | nginx on `APP_PORT` (default 80): SPA + `/api` proxy, login rate limit |

Backend, scheduler and frontend run as unprivileged users without capabilities on a read-only root filesystem; writable are only their volumes and `/tmp`.
| `scheduler` | runs `process_recurring` daily at `RECURRING_TIME` (draft invoices for due support contracts; safe to run twice) |
| `backup` | nightly database dump + uploads tarball at `BACKUP_TIME` |

**TLS.** Put a TLS proxy (Caddy, Traefik, …) in front of `frontend` and list its address in `TRUSTED_PROXIES`. Only then does nginx take over the proxy's `X-Forwarded-For`/`-Proto`. With https `APP_URLS` but without it, Django sees every request as plain http and redirects it to https in a loop, and all users share one login rate limit. Uploaded files are only served to their owner through the API (`/api/v1/attachments/<id>/file/`, `/api/v1/company-images/<id>/file/`); there is no public `/media/`.

### Backups

The `backup` service writes `<db>-<timestamp>.dump` (pg_dump, custom format) and `media-<timestamp>.tar.gz` (uploads, archived invoice PDFs) into the `backups` volume and deletes files older than `BACKUP_KEEP_DAYS`.

```bash
docker compose exec backup sh /backup.sh now                          # backup right now
docker compose cp backup:/var/lib/postgresql/backups ./backups        # copy off the host
```

Backups on the same host don't protect against losing the host — copy them somewhere else regularly (or point your host backup at the `backups` volume). Check the time zone once with `docker compose exec backup date`.

Restore into a fresh stack (stop the app first so nothing writes meanwhile):

```bash
docker compose stop backend scheduler frontend
docker compose exec -T backup sh -c 'pg_restore --clean --if-exists -d "$PGDATABASE"' < backups/<db>-<timestamp>.dump
docker compose run --rm -T --no-deps -v ./backups:/restore:ro backend \
  sh -c 'tar -xzf /restore/media-<timestamp>.tar.gz -C /app/media'
docker compose start backend scheduler frontend
```

## Checks, tooling, CI

VS Code tasks (`.vscode/tasks.json`, Terminal → Run Task): `dev`, `check` (everything CI runs), `django: makemigrations`/`migrate`, `docker: up`/`down`/`backup now`. Without VS Code:

```bash
cd backend && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run deptry . \
  && uv run python manage.py makemigrations --check --dry-run \
  && uv run python manage.py check --fail-level WARNING && uv run pytest -q --cov
cd frontend && pnpm install --frozen-lockfile && pnpm build && pnpm check:licenses
```

Pre-commit hooks (whitespace, YAML/JSON, ruff lint + format): `uv tool run pre-commit install` once.

**Gitea CI** (`.gitea/workflows/build.yaml`) runs the backend checks against PostgreSQL, the frontend build, license checks, `pnpm audit`, Trivy scans of the repository and the images, a smoke test of the compose stack, and pushes `<registry>/<repo>/backend` and `/frontend` on `main` and `v*` tags. **Renovate** (`renovate.json`, `.gitea/workflows/renovate.yaml`) opens update PRs daily and merges green minor/patch updates itself. Setup in Gitea:

1. **Branch protection on `main` with required status checks** `backend`, `frontend`, `repository`, `image`. Do this first: Renovate's automerge relies on it — without required checks Gitea merges immediately, even with red CI.
2. Secrets: `REGISTRY_USER`, `REGISTRY_TOKEN` (scope `write:package`) for the build; `RENOVATE_TOKEN` (`write:repository`, `write:issue`, `read:organization`, `read:user`, `read:package`) and optionally `GH_COM_TOKEN` (read-only github.com token) for Renovate.
3. Actions enabled for the repository; the runner needs Docker.

Conventions for contributors and coding agents: [AGENTS.md](AGENTS.md).

## Key concepts

- **Ledger hourly rates**: `HourlyRate` rows with `valid_from`, scoped project > customer > company default; resolved per entry date at consolidation and snapshotted onto line items.
- **Contract coverage**: `TimeEntry.contract` set = counts against included hours (+ overage if `bill_overage`); unset = normal billable pool invoiced separately via consolidation.
- **GoBD**: `finalize` renders PDF/XML once into `DocumentArchive` with SHA-256 — immutable afterward.
- **E-invoice**: `e_invoice_format` = `zugferd` (PDF/A-3 with embedded factur-x XML) or `xrechnung` (XML-only, needs customer `buyer_reference` / Leitweg-ID).

## License

GNU Affero General Public License v3.0 or later — see [LICENSE](LICENSE). Anyone who runs a modified version as a network service must offer its users the corresponding source code (AGPL section 13). Production dependencies must be AGPL-compatible; the CI license checks enforce that.
