# Operations

Running Corvin with Docker Compose on a Linux host. Every setting is explained in
[`.env.example`](../.env.example).

## Services

Corvin is one image, `ghcr.io/marank/corvin`, run as two services next to PostgreSQL:

| Service | Purpose |
|---|---|
| `db` | PostgreSQL 18 |
| `app` | nginx on `APP_BIND` (default 80: SPA, `/api` proxy, login rate limit) and gunicorn/Django; health check on `/api/v1/health` |
| `worker` | background jobs: invoice mails (retried for about 18 hours if the mail server fails), draft invoices for due support contracts daily at `RECURRING_TIME`, backups daily at `BACKUP_TIME` |

To run the recurring invoices right away: `docker compose exec worker python manage.py
process_recurring` (safe to run twice; a contract is billed once per period).

Every container runs as an unprivileged user without capabilities on a read-only root
filesystem; writable are only its volumes and `/tmp`.

The first start creates the `ADMIN_USERNAME` account. Updates:
`docker compose pull && docker compose up -d`; migrations run on every start. `APP_IMAGE`
in `.env` pins a version (`ghcr.io/marank/corvin:1.2` gets patch releases, `:1.2.3` stays
put). Before updating from a release that used `APP_PORT`: rename it to `APP_BIND` in
`.env`. `ADMIN_ENABLED=true` opens the Django admin at `/django-admin/` for staff users. Verify an image's origin with
`gh attestation verify oci://ghcr.io/marank/corvin:<tag> --owner marank`.

## TLS

Put a TLS proxy (Caddy, Traefik, …) in front of `app` and list its address in
`TRUSTED_PROXIES` (IP addresses or CIDR ranges; the app refuses to start with a range that
covers every address). Only then does nginx take over the proxy's `X-Forwarded-For`/`-Proto`.
With https `APP_URLS` but without it, Django sees every request as plain http and all users
share one login rate limit. The http→https redirect and HSTS are the proxy's job; Corvin
sets neither.

Uploaded files are only served to their owner through the API
(`/api/v1/attachments/<id>/file/`, `/api/v1/company-images/<id>/file/`); there is no public
`/media/`.

## Backups

The worker writes `<db>-<timestamp>.dump` (pg_dump, custom format) and
`media-<timestamp>.tar.gz` (uploads, archived invoice PDFs) into the `backups` volume and
deletes files older than `BACKUP_KEEP_DAYS`.

```bash
docker compose exec worker python manage.py backup_database  # backup right now, e.g. before an update
docker compose cp worker:/backups ./backups             # copy off the host
```

Backups on the same host don't protect against losing the host — copy them somewhere else
regularly (or point your host backup at the `backups` volume). Check the time zone once with
`docker compose exec worker date`.

Restore into a fresh stack (stop the app first so nothing writes meanwhile):

```bash
docker compose stop app worker
docker compose exec -T db sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/<db>-<timestamp>.dump
docker compose run --rm -T --no-deps -v ./backups:/restore:ro app \
  sh -c 'mkdir -p /data/media && tar -xzf /restore/media-<timestamp>.tar.gz -C /data/media'
docker compose start app worker
```
