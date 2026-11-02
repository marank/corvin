"""Fail if a production dependency's license can't be combined with this app's
AGPL-3.0-or-later, or is proprietary / unknown.

Reads `pip-licenses --format=json` from stdin (see the Licenses step in CI).

Fine: permissive licenses, MPL-2.0, LGPL, GPL-3.0, AGPL-3.0, "GPLv2 or later".
Not fine: GPL-2.0-only (can't be combined with (A)GPLv3), SSPL, EPL-1.0, CDDL,
BSD-4-Clause, and anything proprietary or without a machine-readable license.
A package that offers several licenses ("A; B" or "A OR B") passes when one of
them is fine.
"""

import json
import re
import sys

INCOMPATIBLE = re.compile(
    r"""
    SSPL | Server\ Side\ Public
    | EPL-1\.0 | Eclipse\ Public\ License\ 1
    | CDDL | Common\ Development\ and\ Distribution
    | BSD-4-Clause | Original\ BSD
    # GPL version 2 without "or later"; LGPL ("Lesser"/"Library") allows the upgrade.
    | (?<![LA])GPL-?2(\.0)?-only
    | (?<!Lesser\ )(?<!Library\ )General\ Public\ License\ v2\ \(GPLv2\)
    | (?<![LA])GPLv2(?!\+|\ or\ later)
    """,
    re.I | re.X,
)
# Not open source, or nothing machine-readable: needs a look (and an ALLOW entry).
# ("Unlicense" is public domain and doesn't match.)
PROPRIETARY = re.compile(
    r"SEE LICENSE IN|\bUNLICENSED\b|proprietary|commercial|^\s*UNKNOWN\s*$|^\s*$", re.I
)
CHOICE = re.compile(r";|\s+OR\s+")

# Packages whose metadata is wrong or ambiguous, after checking them by hand:
# {"package-name": "reason"}
ALLOW: dict[str, str] = {}


def acceptable(license_: str) -> bool:
    options = [part.strip(" ()") for part in CHOICE.split(license_)] or [license_]
    return any(
        not INCOMPATIBLE.search(option) and not PROPRIETARY.search(option) for option in options
    )


def main() -> int:
    bad = []
    for pkg in json.load(sys.stdin):
        name, license_ = pkg["Name"], pkg.get("License", "")
        if name.lower() in ALLOW:
            continue
        if not acceptable(license_):
            bad.append(f"{name} {pkg.get('Version', '')}: {license_}")
    for line in bad:
        print(f"license not compatible with AGPL-3.0-or-later: {line}")
    if not bad:
        print("licenses ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
