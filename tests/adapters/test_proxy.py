"""Tests for FileProxyProvider."""
import textwrap
from pathlib import Path

import pytest

from visa_checker.adapters.anti_detection.proxy import FileProxyProvider, NullProxyProvider, _parse_proxy_line
from visa_checker.ports.proxy import ProxyConfig


# ── parsing ──────────────────────────────────────────────────────────────────

def test_parse_host_port():
    p = _parse_proxy_line("1.2.3.4:8080")
    assert p is not None
    assert p.server == "http://1.2.3.4:8080"
    assert p.username == ""


def test_parse_host_port_user_pass():
    p = _parse_proxy_line("1.2.3.4:8080:alice:secret")
    assert p is not None
    assert p.username == "alice"
    assert p.password == "secret"


def test_parse_url_style():
    p = _parse_proxy_line("http://alice:secret@1.2.3.4:8080")
    assert p is not None
    assert p.server == "http://1.2.3.4:8080"
    assert p.username == "alice"


def test_parse_comment_ignored():
    assert _parse_proxy_line("# this is a comment") is None


def test_parse_empty_line():
    assert _parse_proxy_line("") is None


# ── FileProxyProvider ─────────────────────────────────────────────────────────

def _write_proxies(tmp_path: Path, lines: list[str]) -> str:
    p = tmp_path / "proxies.txt"
    p.write_text("\n".join(lines))
    return str(p)


def test_loads_from_file(tmp_path):
    path = _write_proxies(tmp_path, [
        "1.2.3.4:8080",
        "5.6.7.8:3128:user:pass",
        "# comment line",
        "",
    ])
    provider = FileProxyProvider(path)
    assert len(provider._active) == 2


def test_next_returns_proxy(tmp_path):
    path = _write_proxies(tmp_path, ["1.2.3.4:8080", "5.6.7.8:3128"])
    provider = FileProxyProvider(path)
    proxy = provider.next()
    assert proxy is not None
    assert proxy.server.startswith("http://")


def test_next_random_selection(tmp_path):
    """next() should not always return the same proxy."""
    path = _write_proxies(tmp_path, [f"10.0.0.{i}:8080" for i in range(1, 11)])
    provider = FileProxyProvider(path)
    seen = {provider.next().server for _ in range(30)}
    # With 10 proxies and 30 draws, we expect more than 1 unique proxy
    assert len(seen) > 1


def test_mark_failed_removes_proxy(tmp_path):
    path = _write_proxies(tmp_path, ["1.2.3.4:8080", "5.6.7.8:3128"])
    provider = FileProxyProvider(path)
    provider.mark_failed("http://1.2.3.4:8080")
    assert len(provider._active) == 1
    assert all(p.server != "http://1.2.3.4:8080" for p in provider._active)


def test_mark_failed_all_resets_pool(tmp_path):
    path = _write_proxies(tmp_path, ["1.2.3.4:8080"])
    provider = FileProxyProvider(path)
    provider.mark_failed("http://1.2.3.4:8080")
    # Pool should reset after all proxies are exhausted
    assert len(provider._active) == 1


def test_missing_file_returns_none():
    provider = FileProxyProvider("/nonexistent/proxies.txt")
    assert provider.next() is None


def test_null_provider_returns_none():
    provider = NullProxyProvider()
    assert provider.next() is None
