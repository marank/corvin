from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from django.contrib.auth.models import User
from weasyprint import URLFetcher

from core.models import CompanyImage


class OwnerResourceFetcher(URLFetcher):  # type: ignore[misc]  # weasyprint ships no type information
    """Lets WeasyPrint load only `data:` URIs and the owner's company images.

    Templates are user-written HTML: without this, `<img>`, `<link rel="attachment">`
    or CSS `url()` would read any file on the server or reach internal hosts.
    """

    def __init__(self, owner: User) -> None:
        super().__init__(allowed_protocols={"data", "file"}, allow_redirects=False)
        self._allowed_paths = {
            Path(image.image.path).resolve() for image in CompanyImage.objects.filter(owner=owner)
        }

    def fetch(self, url: str, headers: dict[str, str] | None = None) -> Any:
        parts = urlsplit(url)
        if parts.scheme == "file":
            path = Path(unquote(parts.path)).resolve()
            if path not in self._allowed_paths:
                raise ValueError(f"Resource not allowed in documents: {url}")
        elif parts.scheme != "data":
            raise ValueError(f"Resource not allowed in documents: {url}")
        return super().fetch(url, headers)
