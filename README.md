# ProjectManager

Project management for IT consultants: customers, projects with budgets, tasks, time tracking (live timer + rounding), on-site visit reports, support contracts with included-hours retainers, invoices (A4/Letter PDF, ZUGFeRD/XRechnung e-invoicing, email delivery, GoBD archiving, partial payments), TOTP security, analytics dashboard — German/English, dark mode, mobile responsive.

## Stack

- **Backend**: Django 6.1 + DRF, single `core` app with split `models/` `serializers/` `views/` `services/` packages, `uv`-managed, SQLite dev / Postgres prod, WeasyPrint PDFs, drafthorse EN-16931 XML.
- **Frontend**: Vue 3.5 + TS + Vite, `pnpm`, PrimeVue + Tailwind, flat square UI, `vue-i18n` (de/en), Pinia, Chart.js.

## Local development (Windows, no Docker)

1. `scripts/setup-windows-dev.ps1` — one-time: installs MSYS2 + Pango (WeasyPrint native deps). Custom path? Set `MSYS2_BIN_DIR` in `backend/.env`.
2. Backend:
   ```powershell
   cd backend
   uv sync
   uv run python manage.py migrate
   uv run python manage.py createsuperuser   # or use /api/v1/auth/register
   uv run python manage.py runserver
   ```
3. Frontend:
   ```powershell
   cd frontend
   pnpm install
   pnpm dev          # http://localhost:5173, proxies /api + /media to :8000
   ```

Dev uses SQLite + console email backend. PDFs work once Pango is installed (`uv run python -c "import weasyprint"` verifies).

## Production (Linux, Docker Compose)

```bash
cp .env.example .env   # set SECRET_KEY, ALLOWED_HOSTS, POSTGRES_PASSWORD, SMTP…
docker compose up -d --build
```

Serves the built Vue app via nginx on :80; `/api` + `/media` proxied to gunicorn/Django on Postgres.

### Recurring invoices (support contracts)

Schedule daily:

```bash
docker compose exec backend uv run --no-sync python manage.py process_recurring
# or locally: uv run python manage.py process_recurring
```

Creates draft invoices for due active contracts (fixed price + optional overage hours).

## Tests / checks

```powershell
cd backend;  uv run pytest; uv run ruff check
cd frontend; pnpm exec vue-tsc -b; pnpm build
```

## Key concepts

- **Ledger hourly rates**: `HourlyRate` rows with `valid_from`, scoped project > customer > company default; resolved per entry date at consolidation and snapshotted onto line items.
- **Contract coverage**: `TimeEntry.contract` set = counts against included hours (+ overage if `bill_overage`); unset = normal billable pool invoiced separately via consolidation.
- **GoBD**: `finalize` renders PDF/XML once into `InvoiceDocument` with SHA-256 — immutable afterward.
- **E-invoice**: `e_invoice_format` = `zugferd` (PDF/A-3 with embedded factur-x XML) or `xrechnung` (XML-only, needs customer `buyer_reference` / Leitweg-ID).
