"""The Loggamera integration."""

import logging
import time
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration

from .api import LoggameraAPI, LoggameraAPIError
from .const import (
    CONF_API_KEY,
    CONF_ORGANIZATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Loggamera integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Loggamera from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(f"Loggamera Integration v{integration.version} starting up")

    api_key = entry.data[CONF_API_KEY]
    organization_id = entry.data.get(CONF_ORGANIZATION_ID)
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    api = LoggameraAPI(api_key=api_key, organization_id=organization_id)

    try:
        await hass.async_add_executor_job(api.get_organizations)
    except LoggameraAPIError as err:
        raise ConfigEntryNotReady(f"Failed to connect to Loggamera API: {err}") from err

    coordinator = LoggameraDataUpdateCoordinator(
        hass,
        api=api,
        name=f"Loggamera {organization_id}" if organization_id else "Loggamera",
        update_interval=timedelta(seconds=scan_interval),
    )
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {coordinator.last_exception}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator, "api": api}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry on options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class LoggameraDataUpdateCoordinator(DataUpdateCoordinator):
    """Fetch organizations, devices, device data, and scenarios on a schedule.

    Devices are fetched once on the first successful cycle and cached for the
    lifetime of the coordinator (Loggamera devices change rarely; reloading the
    entry refreshes them). Per-device data and scenarios are fetched every cycle.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: LoggameraAPI,
        name: str,
        update_interval: timedelta,
    ) -> None:
        super().__init__(hass, _LOGGER, name=name, update_interval=update_interval)
        self.api = api
        self.data: Dict[str, Any] = {
            "devices": [],
            "device_data": {},
            "scenarios": [],
            "organizations": [],
        }

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            return await self._fetch_all()
        except LoggameraAPIError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during update")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_all(self) -> Dict[str, Any]:
        start = time.time()
        data = dict(self.data)

        data["organizations"] = await self._fetch_organizations()
        if not data["devices"]:
            data["devices"] = await self._fetch_devices()
        data["scenarios"] = await self._fetch_scenarios()

        # device_data persists across cycles: a failed per-device fetch leaves the
        # last known reading in place rather than wiping the entity to unavailable.
        device_data = dict(self.data.get("device_data", {}))
        for device in data["devices"]:
            await self._fetch_device(device, device_data)
        data["device_data"] = device_data

        self._log_health()
        _LOGGER.debug(f"Loggamera update cycle finished in {time.time() - start:.2f}s")
        return data

    async def _fetch_organizations(self) -> list:
        response = await self.hass.async_add_executor_job(self.api.get_organizations)
        orgs = ((response.get("Data") or {}).get("Organizations")) or []
        if orgs and not self.api.organization_id:
            self.api.organization_id = orgs[0]["Id"]
            _LOGGER.info(f"Set organization ID to {self.api.organization_id}")
        return orgs

    async def _fetch_devices(self) -> list:
        response = await self.hass.async_add_executor_job(self.api.get_devices)
        devices = ((response.get("Data") or {}).get("Devices")) or []
        if devices:
            _LOGGER.info(f"Found {len(devices)} devices")
        return devices

    async def _fetch_scenarios(self) -> list:
        try:
            response = await self.hass.async_add_executor_job(self.api.get_scenarios)
        except LoggameraAPIError:
            return []
        return ((response.get("Data") or {}).get("Scenarios")) or []

    async def _fetch_device(self, device: Dict[str, Any], target: Dict[Any, Any]) -> None:
        device_id = device["Id"]
        device_type = device["Class"]
        try:
            target[str(device_id)] = await self.hass.async_add_executor_job(
                self.api.get_device_data, device_id, device_type
            )
        except Exception as err:
            _LOGGER.warning(f"Failed to get data for device {device_id}: {err}")
            return

        try:
            raw = await self.hass.async_add_executor_job(self.api.get_raw_data, device_id)
        except LoggameraAPIError:
            return  # RawData is not supported on every device
        if raw and raw.get("Data"):
            raw["_endpoint_used"] = "RawData"
            raw["_is_raw_data"] = True
            target[f"rawdata_{device_id}"] = raw

    def _log_health(self) -> None:
        try:
            status = self.api.get_data_gap_status()
        except Exception as err:
            _LOGGER.debug(f"Could not check API health status: {err}")
            return
        with_gaps = status.get("devices_with_gaps", 0)
        total = status.get("total_devices_tracked", 0)
        if with_gaps:
            _LOGGER.warning(
                f"Data gaps: {with_gaps}/{total} devices affected. "
                f"Check the 'Loggamera API Health' binary sensor for details."
            )
        else:
            _LOGGER.debug(f"All {total} devices reporting data successfully")
