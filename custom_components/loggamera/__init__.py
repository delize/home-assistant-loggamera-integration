"""The Loggamera integration."""

import json
import logging
import time
from datetime import timedelta
from typing import Any, Dict, Optional

import aiofiles
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LoggameraAPI, LoggameraAPIError
from .const import (
    CONF_API_KEY,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_ORGANIZATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

# Since this integration only supports config entries and has no YAML configuration,
# we use the config_entry_only_config_schema helper
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Loggamera integration."""
    # Create domain data if not exists
    hass.data.setdefault(DOMAIN, {})
    return True


def _fixed_device_from_entry(entry: ConfigEntry) -> Optional[Dict[str, Any]]:
    """Return the fixed device for device-scoped API keys, or None."""
    device_id = entry.data.get(CONF_DEVICE_ID)
    if not device_id:
        return None
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
    return {"Id": device_id, "Class": device_type, "Title": f"{device_type} {device_id}"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loggamera from a config entry."""
    try:
        # Log integration version for troubleshooting

        manifest_path = hass.config.path("custom_components", "loggamera", "manifest.json")
        try:
            async with aiofiles.open(manifest_path, "r") as f:
                content = await f.read()
                manifest = json.loads(content)
                version = manifest.get("version", "unknown")
                _LOGGER.info(f"🔧 Loggamera Integration v{version} starting up")
        except Exception:
            _LOGGER.info("🔧 Loggamera Integration starting up (version unknown)")
        # Get config entry data
        api_key = entry.data[CONF_API_KEY]
        organization_id = entry.data.get(CONF_ORGANIZATION_ID)

        # Get scan interval from options or data, or use default
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        _LOGGER.debug(f"Setting up integration with scan interval: {scan_interval} seconds")

        # Create API client
        api = LoggameraAPI(api_key=api_key, organization_id=organization_id)

        # Device-scoped API keys cannot list organizations/devices, so poll one fixed device
        fixed_device = _fixed_device_from_entry(entry)

        # Test API connection (skipped for device-scoped keys, which cannot list organizations)
        if not fixed_device:
            try:
                # Test connection by getting organizations
                await hass.async_add_executor_job(api.get_organizations)
            except LoggameraAPIError as err:
                _LOGGER.error(f"Failed to connect to Loggamera API: {err}")
                raise ConfigEntryNotReady(f"Failed to connect to Loggamera API: {err}")

        # Create update coordinator
        coordinator = LoggameraDataUpdateCoordinator(
            hass,
            api=api,
            name=f"Loggamera {organization_id}" if organization_id else "Loggamera",
            update_interval=timedelta(seconds=scan_interval),
            device=fixed_device,
        )

        # Initial data fetch
        await coordinator.async_config_entry_first_refresh()

        if not coordinator.last_update_success:
            raise ConfigEntryNotReady(f"Failed to fetch initial data: {coordinator.last_exception}")

        # Store the coordinator and API client
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {
            "coordinator": coordinator,
            "api": api,
        }

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Add update listener
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        return True
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.exception(f"Unexpected error during setup: {err}")
        raise ConfigEntryNotReady(f"Unexpected error during setup: {err}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading Loggamera integration for {entry.title}")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug(f"Reloading Loggamera integration for {entry.title}")
    await hass.config_entries.async_reload(entry.entry_id)


class LoggameraDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Loggamera data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: LoggameraAPI,
        name: str,
        update_interval: timedelta,
        device: Optional[Dict[str, Any]] = None,
    ):
        """Initialize data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )
        self.api = api
        # Fixed device for device-scoped API keys (no Organizations/Devices access)
        self.fixed_device = device
        self.data = {
            "devices": [device] if device else [],
            "device_data": {},
            "scenarios": [],
            "organizations": [],
        }

        _LOGGER.debug(
            "Created Loggamera data coordinator with update interval: %s",
            update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:  # noqa: C901
        """Fetch data from API."""
        try:
            _LOGGER.debug("Starting data update cycle")
            start_time = time.time()

            # Start with existing data - we'll update it
            updated_data = self.data.copy()

            if self.fixed_device:
                # Device-scoped key: Organizations/Devices/Scenarios return "Invalid ApiKey"
                org_response = {}
            else:
                # Always fetch organizations for organization sensors
                _LOGGER.debug("Fetching organizations for organization sensors")
                org_response = await self.hass.async_add_executor_job(self.api.get_organizations)

            if (
                "Data" in org_response
                and "Organizations" in org_response["Data"]
                and org_response["Data"]["Organizations"]
            ):
                updated_data["organizations"] = org_response["Data"]["Organizations"]
                _LOGGER.debug(f"Found {len(updated_data['organizations'])} organizations")

                # Set organization ID if not already set
                if not self.api.organization_id:
                    self.api.organization_id = org_response["Data"]["Organizations"][0]["Id"]
                    _LOGGER.info(f"Set organization ID to {self.api.organization_id}")
            else:
                updated_data["organizations"] = []

            # Fetch devices if we don't have them yet
            if not updated_data["devices"]:
                devices_response = await self.hass.async_add_executor_job(self.api.get_devices)
                if "Data" in devices_response and "Devices" in devices_response["Data"]:
                    updated_data["devices"] = devices_response["Data"]["Devices"]
                    _LOGGER.info(f"Found {len(updated_data['devices'])} devices")

            # Fetch scenarios if available (for button platform if needed in future)
            if not self.fixed_device:
                try:
                    scenarios_response = await self.hass.async_add_executor_job(
                        self.api.get_scenarios
                    )
                    if "Data" in scenarios_response and "Scenarios" in scenarios_response["Data"]:
                        updated_data["scenarios"] = scenarios_response["Data"]["Scenarios"]
                        _LOGGER.debug(f"Found {len(updated_data['scenarios'])} scenarios")
                except LoggameraAPIError:
                    # Don't fail the whole update if scenarios aren't available
                    pass

            # Fetch device data for each device
            for device in updated_data["devices"]:
                device_id = device["Id"]
                device_type = device["Class"]
                try:
                    # Fetch standard device data (PowerMeter, HeatPump, etc.)
                    device_data = await self.hass.async_add_executor_job(
                        self.api.get_device_data, device_id, device_type
                    )

                    # Store the device data
                    updated_data["device_data"][str(device_id)] = device_data

                    # Also collect RawData separately for all devices
                    # This provides additional detailed sensors that users can enable
                    try:
                        raw_data = await self.hass.async_add_executor_job(
                            self.api.get_raw_data, device_id
                        )
                        if raw_data and "Data" in raw_data and raw_data["Data"]:
                            # Mark this as RawData source and store separately
                            raw_data["_endpoint_used"] = "RawData"
                            raw_data["_is_raw_data"] = True
                            updated_data["device_data"][f"rawdata_{device_id}"] = raw_data
                            _LOGGER.debug(f"Collected RawData for device {device_id}")
                    except LoggameraAPIError as e:
                        _LOGGER.debug(f"RawData not available for device {device_id}: {e}")
                        # This is normal - not all devices support RawData

                    # Log which data sources were used
                    sources = []
                    if device_data.get("_raw_data_used"):
                        sources.append("RawData")
                    if device_data.get("_power_meter_used"):
                        sources.append("PowerMeter")
                    if device_data.get("_endpoint_used"):
                        sources.append(device_data["_endpoint_used"])

                    if sources:
                        _LOGGER.debug(
                            f"Device {device_id} data fetched from: {', '.join(sources)}"  # noqa: E501
                        )
                except Exception as err:
                    if self.fixed_device and str(device_id) not in updated_data["device_data"]:
                        # No data yet for the only device: fail so setup retries and
                        # entities are created once the API recovers
                        raise
                    _LOGGER.warning(f"Failed to get data for device {device_id}: {err}")

            # Calculate time taken for the update
            elapsed = time.time() - start_time

            # Report API health status and data gaps
            try:
                gap_status = self.api.get_data_gap_status()
                devices_with_gaps = gap_status.get("devices_with_gaps", 0)
                total_devices = gap_status.get("total_devices_tracked", 0)

                if devices_with_gaps > 0:
                    _LOGGER.warning(
                        f"Data gaps detected: {devices_with_gaps}/{total_devices} devices affected."
                        f"Check 'Loggamera API Health' binary sensor for details."
                    )
                else:
                    _LOGGER.debug(f"All {total_devices} devices reporting data successfully.")
            except Exception as health_err:
                _LOGGER.debug(f"Could not check API health status: {health_err}")

            _LOGGER.debug(
                f"Finished fetching loggamera data in {elapsed:.3f} seconds (success: {True})"  # noqa: E501
            )

            return updated_data
        except LoggameraAPIError as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error fetching data: {err}")
        except Exception as err:
            _LOGGER.exception(f"Unexpected error during update: {err}")
            raise UpdateFailed(f"Unexpected error: {err}")
