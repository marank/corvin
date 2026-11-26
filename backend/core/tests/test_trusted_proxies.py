"""TRUSTED_PROXIES: addresses and ranges are fine, "trust everyone" and typos are not."""

import pytest

from core.checks import trusted_proxies, trusted_proxy_problems


@pytest.mark.parametrize(
    "entries",
    [[], ["none"], ["127.0.0.1"], ["10.0.0.0/8", "fd00::/8"], ["172.18.0.2", "192.168.1.0/24"]],
)
def test_sane_values_pass(entries):
    assert trusted_proxy_problems(entries) == []


@pytest.mark.parametrize(
    "entries",
    [["0.0.0.0/0"], ["::/0"], ["10.0.0.1", "0.0.0.0/0"], ["proxy.example.com"], ["10.0.0.0/33"]],
)
def test_bad_values_are_refused(entries):
    assert trusted_proxy_problems(entries)


def test_none_only_counts_alone():
    assert trusted_proxy_problems(["none", "10.0.0.1"])


def test_the_check_reports_core_e002(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "0.0.0.0/0")
    assert [error.id for error in trusted_proxies()] == ["core.E002"]
    monkeypatch.setenv("TRUSTED_PROXIES", "")
    assert trusted_proxies() == []
