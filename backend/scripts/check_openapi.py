"""Fail if frontend/openapi.json no longer matches the API.

    uv run python scripts/check_openapi.py         (in backend/; part of `just check-backend`)

Exports the schema into a temporary file with the same command as `just api-schema` and
compares it with the committed file. It changes nothing in the working tree, so it also
passes with an uncommitted, but current, openapi.json.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

COMMITTED = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def export(target: Path) -> None:
    """The schema as `just api-schema` writes it (test settings: no .env or secrets needed)."""
    subprocess.run(
        [
            sys.executable,
            "manage.py",
            "spectacular",
            "--validate",
            "--fail-on-warn",
            "--format",
            "openapi-json",
            "--file",
            str(target),
        ],
        check=True,
        env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings_test"},
    )


def main() -> int:
    if len(sys.argv) > 1:  # `just api-schema`: write the committed file
        export(COMMITTED)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "openapi.json"
        export(target)
        current = target.read_bytes()
    if not COMMITTED.exists() or COMMITTED.read_bytes() != current:
        print("API changed: run `just api-types` and commit both files", file=sys.stderr)
        return 1
    print("openapi.json up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
