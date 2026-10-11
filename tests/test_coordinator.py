"""Tests for the Loggamera coordinator with a fixed (device-scoped) device."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.loggamera import LoggameraDataUpdateCoordinator
from custom_components.loggamera.api import LoggameraAPIError
from custom_components.loggamera.const import (
    CONF_API_KEY,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    DOMAIN,
)

DEVICE = {"Id": 1234, "Class": "HeatPump", "Title": "HeatPump 1234"}
VALUES = {"Data": {"Values": [{"Name": "x", "Value": "1", "ValueType": "DECIMAL"}]}}


def _mock_api():
    api = MagicMock()
    api.organization_id = None
    api.get_device_data.return_value = VALUES
    api.get_raw_data.return_value = {"Data": {"Values": []}}
    api.get_data_gap_status.return_value = {}
    return api


async def test_fixed_device_skips_org_device_and_scenario_calls(hass):
    """Only device endpoints are called for a fixed device."""
    api = _mock_api()
    coordinator = LoggameraDataUpdateCoordinator(
        hass, api=api, name="Loggamera", update_interval=timedelta(minutes=20), device=DEVICE
    )

    data = await coordinator._async_update_data()

    api.get_organizations.assert_not_called()
    api.get_devices.assert_not_called()
    api.get_scenarios.assert_not_called()
    api.get_device_data.assert_called_once_with(1234, "HeatPump")
    api.get_raw_data.assert_called_once_with(1234)
    assert data["devices"] == [DEVICE]
    assert data["organizations"] == []
    assert data["scenarios"] == []
    assert data["device_data"]["1234"] == VALUES


async def test_setup_entry_with_device_id(hass):
    """A device-scoped entry loads without calling Organizations."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device_1234",
        data={CONF_API_KEY: "test-key", CONF_DEVICE_ID: 1234, CONF_DEVICE_TYPE: "HeatPump"},
    )
    entry.add_to_hass(hass)
    api_path = "custom_components.loggamera.LoggameraAPI"
    with (
        patch(f"{api_path}.get_organizations") as orgs,
        patch(f"{api_path}.get_scenarios") as scen,
        patch(f"{api_path}.get_device_data", return_value=VALUES),
        patch(f"{api_path}.get_raw_data", return_value={"Data": {"Values": []}}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    orgs.assert_not_called()
    scen.assert_not_called()
    # Device-scoped entries have no organization data, so no organization sensors
    assert not [e for e in hass.states.async_entity_ids("sensor") if "organization" in e]


async def test_setup_entry_with_device_id_retries_on_api_error(hass):
    """A failing fixed device must not leave a LOADED entry without entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device_1234",
        data={CONF_API_KEY: "bad-key", CONF_DEVICE_ID: 1234, CONF_DEVICE_TYPE: "HeatPump"},
    )
    entry.add_to_hass(hass)
    api_path = "custom_components.loggamera.LoggameraAPI"
    error = LoggameraAPIError("Invalid ApiKey")
    with (
        patch(f"{api_path}.get_device_data", side_effect=error),
        patch(f"{api_path}.get_raw_data", side_effect=error),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_two_device_entries_do_not_duplicate_unique_ids(hass):
    """Each device entry gets its own API health sensor and no shared organization sensors."""
    api_path = "custom_components.loggamera.LoggameraAPI"
    with (
        patch(f"{api_path}.get_device_data", return_value=VALUES),
        patch(f"{api_path}.get_raw_data", return_value={"Data": {"Values": []}}),
    ):
        for device_id in (1234, 5678):
            entry = MockConfigEntry(
                domain=DOMAIN,
                unique_id=f"device_{device_id}",
                data={
                    CONF_API_KEY: "test-key",
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_TYPE: "HeatPump",
                },
            )
            entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    health = hass.states.async_entity_ids("binary_sensor")
    assert len([e for e in health if "api_health" in e]) == 2


async def test_fixed_device_first_failure_raises_update_failed(hass):
    """Without any data yet, a failing fixed device fails the update (setup retries)."""
    api = _mock_api()
    api.get_device_data.side_effect = LoggameraAPIError("Invalid ApiKey")
    coordinator = LoggameraDataUpdateCoordinator(
        hass, api=api, name="Loggamera", update_interval=timedelta(minutes=20), device=DEVICE
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_fixed_device_later_failure_keeps_last_data(hass):
    """After a good poll, one failed poll keeps the last data, like organization entries."""
    api = _mock_api()
    coordinator = LoggameraDataUpdateCoordinator(
        hass, api=api, name="Loggamera", update_interval=timedelta(minutes=20), device=DEVICE
    )
    coordinator.data = await coordinator._async_update_data()
    api.get_device_data.side_effect = LoggameraAPIError("All endpoints failed for device 1234")

    data = await coordinator._async_update_data()

    assert data["device_data"]["1234"] == VALUES
