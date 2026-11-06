"""Tests verifying structured JSON logging output."""

import json
import logging
from docforge.config.logging import JSONFormatter


def test_json_formatter() -> None:
    """Verify JSONFormatter outputs valid, structured JSON without crashes."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="docforge.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test structured log message",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "docforge.test"
    assert parsed["message"] == "Test structured log message"
    assert "timestamp" in parsed

