#!/usr/bin/env python3
"""
Fail unless a pull request title is a Conventional Commit.

    TITLE="feat: show the owner on the detail page" just check-pr-title "$TITLE"

With squash merging the PR title becomes the commit message on `main`, and release-please
builds the changelog and the next version from those messages: one malformed title leaves
a gap. CI runs this on every pull request (`pr-title.yaml`); the title comes in
through the environment, never through the shell command line. Standard library only.
"""

from __future__ import annotations

import os
import re
import sys

TYPES = ("feat", "fix", "perf", "deps", "docs", "refactor", "style", "test", "build", "ci", "chore", "revert")
TITLE = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([\w./,-]+\))?!?: \S.*$")


def main() -> int:
    title = os.environ.get("TITLE", "").strip()
    if TITLE.fullmatch(title) and "\n" not in title:
        print(f"title ok: {title}")
        return 0
    print(f"not a Conventional Commit: {title!r}", file=sys.stderr)
    print(f"expected `<type>[(scope)][!]: <description>` with type one of {', '.join(TYPES)}, "
          'e.g. "feat: show the owner on the detail page"', file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
