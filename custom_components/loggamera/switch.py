"""Support for Loggamera scenario switches."""

import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import LoggameraAPIError
from .const import ATTR_DURATION_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Loggamera switches based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    scenarios = (coordinator.data or {}).get("scenarios") or []
    if not scenarios:
        _LOGGER.info("No scenarios available")
        return

    switches = [LoggameraScenarioSwitch(coordinator, api, scenario) for scenario in scenarios]
    async_add_entities(switches)
    _LOGGER.info(f"Adding {len(switches)} Loggamera scenario switches")


class LoggameraScenarioSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Loggamera scenario switch.

    Scenarios are momentary: triggering one fires it on the platform; we flip
    the switch on, then auto-flip it off after a short delay.
    """

    def __init__(self, coordinator, api, scenario):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._scenario = scenario
        self._scenario_id = scenario["Id"]
        self._is_on = False

        self._attr_unique_id = f"scenario_{self._scenario_id}"
        self._attr_name = f"Scenario {scenario['Name']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"scenario_{self._scenario_id}")},
            name=f"Scenario {scenario['Name']}",
            manufacturer="Loggamera",
            model="Scenario",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs):
        """Trigger the scenario."""
        try:
            await self.hass.async_add_executor_job(
                self._api.execute_scenario_async, self._scenario_id
            )
        except LoggameraAPIError as err:
            _LOGGER.error(f"Failed to execute scenario {self._scenario_id}: {err}")
            return

        self._is_on = True
        self.async_write_ha_state()

        async def _auto_off():
            await asyncio.sleep(2)
            self._is_on = False
            self.async_write_ha_state()

        asyncio.create_task(_auto_off())

    async def async_turn_off(self, **kwargs):
        """Scenarios are momentary; just clear the on state."""
        self._is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return extra state attributes."""
        attrs: Dict[str, Any] = {"scenario_id": self._scenario_id}
        if "Description" in self._scenario:
            attrs["description"] = self._scenario["Description"]
        if "DurationMinutes" in self._scenario:
            attrs[ATTR_DURATION_MINUTES] = self._scenario["DurationMinutes"]
        return attrs
