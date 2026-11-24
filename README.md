# Corvin

Corvin is project management and invoicing for independent IT consultants. You keep your
customers, projects and support contracts in one place, track your time while you work, and
turn it into correct invoices — including German e-invoices — without a spreadsheet in
between. It runs on your own server with Docker, in German and English.

## Features

### Customers and projects

- **Customers** with contacts, addresses and their own hourly rates.
- **Projects with budgets** and tasks, so you see early when hours run out.
- **Hourly rates that change over time**: a new rate applies from its date; older work keeps
  the rate it was done at.

### Time and visits

- **Live timer** with breaks, or type times and durations directly; configurable rounding.
- **On-site visit reports** for work at the customer's premises.
- **Support contracts** with included hours per period; overage billed only if you want.

### Invoices

- **Invoices from tracked time** in a few clicks, as A4 or Letter PDF.
- **E-invoicing**: ZUGFeRD (PDF with embedded XML) or XRechnung (XML with Leitweg-ID).
- **Email delivery** straight from Corvin, **partial payments** and open amounts.
- **Your own invoice layout** with the invoice designer and reusable text blocks.
- **Recurring invoices** for support contracts are drafted automatically every day.
- **GoBD archiving**: a finalized invoice's PDF and XML are stored once and never changed.

### Overview

- **Analytics dashboard** for revenue and hours across customers and projects.
- **Dark mode** and a layout that works on the phone.

### Security and operations

- **Two-factor sign-in** (TOTP) and a rate-limited login.
- **Hardened containers**: unprivileged, no capabilities, read-only file system.
- **Nightly backups** of the database and uploaded files.

## Quick start with Docker

You need Docker with the Compose plugin. Corvin runs from the published image
`ghcr.io/marank/corvin`; the server needs only two files.

1. Download `compose.yml` and the example configuration:

   ```bash
   mkdir corvin && cd corvin
   curl -fsSLO https://raw.githubusercontent.com/marank/corvin/main/compose.yml
   curl -fsSL https://raw.githubusercontent.com/marank/corvin/main/.env.example -o .env
   ```

2. Edit `.env` and set at least these values:

   | Variable | Value |
   | --- | --- |
   | `SECRET_KEY` | A random string of at least 40 characters. Corvin does not start with the placeholder. |
   | `ADMIN_PASSWORD` | Password of the first administrator (user `admin`). |
   | `DB_PASSWORD` | Password of the database, used only between the containers. |
   | `APP_URLS` | The address users open, e.g. `https://corvin.example.com`. Keep `http://localhost` to try it on your own machine. |
   | `EMAIL_*` | Your SMTP server, for sending invoices. |

   Generate the random values for `SECRET_KEY` and `DB_PASSWORD` with
   `openssl rand -hex 32`.

3. Start Corvin and its database:

   ```bash
   docker compose up -d
   ```

Open <http://localhost> and sign in as `admin`. Updates:
`docker compose pull && docker compose up -d`; migrations run on every start.

## Operations

- **TLS:** put a TLS proxy in front and set `TRUSTED_PROXIES` to its address.
- **Settings:** every variable is explained in [`.env.example`](.env.example).
- **Backups, restore, versions:** see [docs/operations.md](docs/operations.md).

## Contributing

Corvin is still in active development, so pull requests are not accepted yet; bug reports
and ideas are welcome as issues. See [CONTRIBUTING.md](CONTRIBUTING.md).

To run Corvin from source (details in [docs/development.md](docs/development.md)):

```bash
cp .env.example .env    # then add DEBUG=true to .env
just setup && just migrate
just dev-backend     # second terminal: just dev-frontend → http://localhost:5173
```

## License

[GNU Affero General Public License v3.0 or later](LICENSE). Running a modified Corvin for
others over a network obliges you to offer them its source.
