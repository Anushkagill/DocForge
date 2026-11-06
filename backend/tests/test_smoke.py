"""Smoke test verifying test runner and project structure."""

import docforge


def test_smoke() -> None:
    """Verify package import and metadata."""
    assert docforge.__version__ == "0.1.0"

