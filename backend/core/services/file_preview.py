"""Which uploads the app may show in place, decided by file extension.

Markdown and text are rendered by the SPA (raw HTML escaped, as plain text); images and
PDFs are served inline (`INLINE_CONTENT_TYPES`). Everything else is only downloaded.
"""

from typing import Literal

PreviewKind = Literal["markdown", "text", "image", "pdf"]

# Text is loaded into the page as a whole; larger files are only downloaded.
TEXT_PREVIEW_LIMIT = 1024 * 1024

_KINDS: dict[str, PreviewKind] = {
    **dict.fromkeys(["md", "markdown"], "markdown"),
    **dict.fromkeys(
        ["txt", "log", "csv", "tsv", "json", "xml", "yaml", "yml", "ini", "cfg", "conf", "toml"],
        "text",
    ),
    **dict.fromkeys(["png", "jpg", "jpeg", "gif", "webp"], "image"),
    "pdf": "pdf",
}


def preview_kind(filename: str, size: int | None) -> PreviewKind | None:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    kind = _KINDS.get(extension)
    if kind in ("markdown", "text") and (size is None or size > TEXT_PREVIEW_LIMIT):
        return None
    return kind
