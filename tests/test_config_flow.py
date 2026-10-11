"""Tests for the Loggamera config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.loggamera.api import LoggameraAPIError
from custom_components.loggamera.const import (
    CONF_API_KEY,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

API = "custom_components.loggamera.config_flow.LoggameraAPI"
DEVICE_INPUT = {CONF_API_KEY: "test-key", CONF_DEVICE_ID: 1234, CONF_DEVICE_TYPE: "HeatPump"}


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_device_id_creates_entry(hass):
    """A Device ID validates via the device endpoint and never lists organizations."""
    result = await _start(hass)
    with patch(f"{API}.get_device_data", return_value={"Data": {"Values": []}}) as dev, patch(
        f"{API}.get_organizations"
    ) as orgs, patch("custom_components.loggamera.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DEVICE_INPUT)
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Loggamera HeatPump 1234"
    assert result["data"][CONF_DEVICE_ID] == 1234
    assert result["data"][CONF_DEVICE_TYPE] == "HeatPump"
    assert CONF_SCAN_INTERVAL in result["data"]
    assert result["result"].unique_id == "device_1234"
    dev.assert_called_once_with(1234, "HeatPump")
    orgs.assert_not_called()


async def test_device_id_api_error_shows_cannot_connect(hass):
    """An API error while reading the device is reported as cannot_connect."""
    result = await _start(hass)
    with patch(f"{API}.get_device_data", side_effect=LoggameraAPIError("Invalid ApiKey")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DEVICE_INPUT)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_device_id_unexpected_error_shows_unknown(hass):
    """Any other exception is reported as unknown."""
    result = await _start(hass)
    with patch(f"{API}.get_device_data", side_effect=RuntimeError("boom")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DEVICE_INPUT)

    assert result["errors"] == {"base": "unknown"}


async def test_device_id_already_configured(hass):
    """The same Device ID cannot be added twice."""
    MockConfigEntry(domain=DOMAIN, unique_id="device_1234", data={}).add_to_hass(hass)
    result = await _start(hass)
    with patch(f"{API}.get_device_data", return_value={"Data": {"Values": []}}):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DEVICE_INPUT)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_without_device_id_uses_organizations(hass):
    """Without a Device ID the original organization flow is used."""
    result = await _start(hass)
    orgs = {"Data": {"Organizations": [{"Id": 7, "Name": "Home"}]}}
    with patch(f"{API}.get_organizations", return_value=orgs), patch(
        f"{API}.get_device_data"
    ) as dev, patch("custom_components.loggamera.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "test-key"}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert CONF_DEVICE_ID not in result["data"]
    dev.assert_not_called()


async def test_device_id_wrong_type_is_rejected(hass):
    """A type whose endpoint fails but RawData answers is reported, not silently accepted."""
    result = await _start(hass)
    raw = {"Data": {"Values": [{"Name": "x"}]}, "_endpoint_used": "RawData"}
    with patch(f"{API}.get_device_data", return_value=raw):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**DEVICE_INPUT, CONF_DEVICE_TYPE: "PowerMeter"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_DEVICE_TYPE: "wrong_device_type"}
