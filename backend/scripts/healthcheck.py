"""Docker HEALTHCHECK: GET /api/v1/health on gunicorn inside the container.

Sent with the first ALLOWED_HOSTS entry as Host header, because Django rejects
unknown hosts. Plain http on purpose: the path is exempt from the SSL redirect.
"""

import os
import sys
import urllib.error
import urllib.request

host = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")[0].strip() or "localhost"
host = host.lstrip(".")  # ".example.com" wildcard entries
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/health", headers={"Host": host}
)
try:
    with urllib.request.urlopen(request, timeout=5) as response:
        sys.exit(0 if response.status == 200 else 1)
except (urllib.error.URLError, OSError) as error:
    print(error)
    sys.exit(1)
