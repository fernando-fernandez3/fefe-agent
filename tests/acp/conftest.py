"""Collection guards for ACP tests that require optional dependencies."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_ACP_REQUIRED_MODULES = frozenset(
    {
        "test_entry.py",
        "test_events.py",
        "test_mcp_e2e.py",
        "test_permissions.py",
        "test_ping_suppression.py",
        "test_server.py",
        "test_tools.py",
    }
)


def pytest_ignore_collect(collection_path, config):
    """Ignore ACP protocol tests when the optional ACP SDK is unavailable."""
    path = Path(str(collection_path))
    if path.name in _ACP_REQUIRED_MODULES and importlib.util.find_spec("acp") is None:
        return True
    return None
