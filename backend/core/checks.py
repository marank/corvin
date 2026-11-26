"""System checks: a sane TRUSTED_PROXIES (run at container start by `check --deploy`)."""

import ipaddress
from typing import Any

from django.core import checks

from config.env import env_list


def trusted_proxy_problems(entries: list[str]) -> list[str]:
    """What is wrong with a TRUSTED_PROXIES value (empty list: nothing).

    Each entry is an IP address or a CIDR range. `none` (alone) says on purpose that no proxy
    is in front. A range that covers every address is refused: nginx would then believe any
    client's X-Forwarded-For, and rate limits and logs could be dodged by lying about the address.
    """
    if entries == ["none"]:
        return []
    problems = []
    for entry in entries:
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            problems.append(f"{entry!r} is not an IP address or CIDR range")
            continue
        if network.prefixlen == 0:
            problems.append(f"{entry!r} trusts every address")
    return problems


@checks.register()
def trusted_proxies(app_configs: Any = None, **kwargs: Any) -> list[checks.CheckMessage]:
    return [
        checks.Error(
            f"TRUSTED_PROXIES: {problem}.",
            hint="List the address(es) of your TLS proxy, or leave it empty (or set `none`).",
            id="core.E002",
        )
        for problem in trusted_proxy_problems(env_list("TRUSTED_PROXIES"))
    ]
