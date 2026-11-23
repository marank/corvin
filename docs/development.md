# Development

Conventions for contributors and coding agents are in [AGENTS.md](../AGENTS.md); how a change
gets in is in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Stack

- **Backend**: Django 6.1 + DRF, single `core` app with split `models/` `serializers/`
  `views/` `services/` packages, `uv`-managed, SQLite natively / PostgreSQL in Docker,
  WeasyPrint PDFs, drafthorse EN-16931 XML.
- **Frontend**: Vue 3.5 + TypeScript + Vite, `pnpm`, PrimeVue + Tailwind, `vue-i18n`
  (de/en), Pinia, Chart.js.

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), [just](https://just.systems) ≥ 1.38,
Node 26 LTS with pnpm in the version of `frontend/package.json`'s `packageManager`
(`corepack enable` or `npm install -g pnpm@<version>`). Docker only for the production-like
stack.

On Windows run `scripts/setup-windows-dev.ps1` once: it installs MSYS2 + Pango (WeasyPrint's
native dependencies). Custom path? Set `MSYS2_BIN_DIR` in `.env`. On Linux and macOS install
Pango from the package manager.

```bash
cp .env.example .env     # set DEBUG=true for native development
just setup               # uv sync + pnpm install
just migrate             # SQLite database + the admin from ADMIN_* in .env
just dev-backend         # Django on :8000
just dev-frontend        # second terminal: Vite on :5173 → http://localhost:5173
```

Native development uses SQLite and prints mails on the console. There is no job queue then:
jobs (`core/tasks.py`) run in-process right after the request's transaction, and the daily
jobs (recurring invoices, backups) don't run — `uv run python manage.py process_recurring`
runs the recurring invoices by hand. PDFs work once Pango is
installed (`uv run python -c "import weasyprint"` verifies).

## Checks

All commands live in the `justfile` (`just` lists them); the VS Code tasks (Terminal → Run
Task) and CI call its recipes.

```bash
just check            # everything CI checks: backend, deploy settings, frontend, workflows
just api-types        # after API changes: openapi.json + src/api/schema.d.ts
just migrations       # after model changes
just docker-up        # build the image from the checkout, start the stack on :80
```

Pre-commit hooks (whitespace, YAML/JSON, ruff lint + format): `uv tool run pre-commit install`
once. Claude Code runs `scripts/lint_file.py` after every edit (`.claude/settings.json`), so
an agent sees lint problems right away.

## CI and releases (GitHub)

`.github/workflows/build.yaml` runs `just check-backend` against PostgreSQL,
`just check-frontend`, `just check-workflows` (actionlint, zizmor), Trivy scans of the
repository and the images, a dependency review on pull requests, and a smoke test of the
compose stack (`docker/smoke-test` in the app and worker containers). On `main`
and `v*` tags it pushes `ghcr.io/marank/corvin` with a provenance attestation. Every Monday it rebuilds `main` and runs
`just check-eol` (warns 180 days before Python, Node.js, PostgreSQL or Django lose security
support). Dependabot (`.github/dependabot.yml`) proposes updates weekly; a person merges them
after green CI.

Releases are made by hand: `git tag v1.2.3 && git push --tags` builds and pushes `1.2.3`,
`1.2` and `1`.

Not updated by Dependabot, bump by hand: `TRIVY_IMAGE` (tag and digest) in `build.yaml`, the
actionlint and zizmor versions in the justfile, `rust-just==…` in the workflow, the
PostgreSQL major of the CI service together with `compose.yml` and `PG_MAJOR` in the
`Dockerfile`, `SUPERVISOR_VERSION` in the `Dockerfile`.

One-time GitHub setup:

1. **Ruleset for `main`**: pull requests required, squash merge only, required status checks
   `backend`, `frontend`, `workflows`, `repository`, `image` and (public repository)
   `dependency-review`. Without it Dependabot PRs can be merged with red CI.
2. **Security** (Settings → Advanced Security): private vulnerability reporting (SECURITY.md
   points there), Dependabot alerts, secret scanning with push protection, CodeQL default
   setup.
3. **Releases**: turn on immutable releases.
4. **Package**: the first push creates `ghcr.io/marank/corvin` as a private package. Make it
   public (or give the servers a read token) so `docker compose pull` works, and link it to
   the repository.

## Branding

Name **Corvin**, from Latin *corvus*, the raven: Odin's ravens Hugin and Munin stand for
thought and memory, and the *Bibliotheca Corviniana* was one of the great archives of the
Renaissance. Mark: a raven head from basic shapes, a half circle in violet and blue with a
cyan beak (`branding/corvin-mark.svg`). Wordmark in Space Grotesk 600 (OFL-1.1, self-hosted
via `@fontsource/space-grotesk`). In the app: `src/components/ui/AppLogo.vue`;
`frontend/public/favicon.svg` adapts to dark mode.

`branding/` holds the mark (SVG, PNG 256/512, multi-size ICO), the lockup with the wordmark
as outlines (`corvin-logo.svg`, `corvin-logo-white.svg` for dark backgrounds, PNG) and the
link-preview image. `frontend/public/` gets `favicon.ico`, the manifest icons
(`icon-192/512.png`, `icon-maskable-512.png`), `apple-touch-icon.png`, `og-image.png` and
`manifest.webmanifest`. All raster files come from `scripts/brand-assets.py` (usage in its
docstring) — change the mark there and rerun instead of editing PNGs by hand.
