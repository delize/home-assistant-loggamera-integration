"""Shared fixtures for Loggamera tests."""

from unittest.mock import patch

import pytest

# Live-API command-line scripts, not unit tests
collect_ignore = ["test_power_meter.py", "test_powermeter_endpoint.py"]


@pytest.fixture(autouse=True)
def no_retry_sleep():
    """Skip real retry back-off sleeps so failing API calls don't hang tests."""
    with patch("custom_components.loggamera.api.LoggameraAPI._sleep_sync"):
        yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components/loggamera in every test."""
    yield
