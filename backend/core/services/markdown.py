"""Markdown from the app's free-text fields (time entry reports) as HTML for documents.

Matches the frontend's renderer (markdown-it): raw HTML in the source is escaped and unsafe
link targets (javascript:, data:) stay plain text, so the result can go into a template as is.
"""

from functools import cache

from django.utils.safestring import SafeString, mark_safe
from markdown_it import MarkdownIt


@cache
def _parser() -> MarkdownIt:
    return MarkdownIt("js-default", {"html": False, "breaks": True})


def render_markdown(source: str) -> SafeString:
    html: str = _parser().render(source)
    return mark_safe(html)  # noqa: S308 - raw HTML is escaped (html=False)
