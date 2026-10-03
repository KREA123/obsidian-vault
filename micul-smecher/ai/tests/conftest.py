"""Test-wide defaults.

The suites written before the founder's 3 Oct 2026 decision exercise brain A ("SOUL Cloud": AI on SOUL's own
keys), which is now OFF by default (SOUL_BUILTIN_AI=0, suflet_ai.config.builtin_ai_enabled). They run with it
ON, so the code path stays tested; tests of the default product set SOUL_BUILTIN_AI=0 themselves.
"""
import pytest


@pytest.fixture(autouse=True)
def _builtin_ai_on_for_legacy_suites(monkeypatch, request):
    if request.node.get_closest_marker("builtin_off"):
        monkeypatch.setenv("SOUL_BUILTIN_AI", "0")
    else:
        monkeypatch.setenv("SOUL_BUILTIN_AI", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "builtin_off: run with SOUL_BUILTIN_AI=0 (the default product)")
