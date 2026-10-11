"""Support for Loggamera binary sensors."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DEVICE_TYPE, DOMAIN

_LOGGER = logging.getLogger(__name__)

ALARM_DEVICE_CLASSES = {
    "PowerMeter": BinarySensorDeviceClass.PROBLEM,
    "RoomSensor": BinarySensorDeviceClass.PROBLEM,
    "WaterMeter": BinarySensorDeviceClass.PROBLEM,
    "CoolingUnit": BinarySensorDeviceClass.PROBLEM,
    "HeatPump": BinarySensorDeviceClass.PROBLEM,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Loggamera binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    binary_sensors = []

    # Get devices from coordinator
    for device in coordinator.data.get("devices", []):
        device_id = device["Id"]
        device_name = device.get("Title", f"Device {device_id}")
        device_type = device.get("Class", "Unknown")

        # Process device data to find binary sensors
        device_data = coordinator.data.get("device_data", {}).get(str(device_id))
        if not device_data or "Data" not in device_data or "Values" not in device_data["Data"]:
            continue

        for value in device_data["Data"]["Values"]:
            # Only process boolean values
            if value.get("ValueType") == "BOOLEAN":
                binary_sensors.append(
                    LoggameraBinarySensor(
                        coordinator=coordinator,
                        api=api,
                        device_id=device_id,
                        device_name=device_name,
                        device_type=device_type,
                        value_data=value,
                    )
                )

    # Always add API health diagnostic sensor
    binary_sensors.append(
        LoggameraAPIHealthSensor(
            coordinator=coordinator,
            api=api,
        )
    )

    if binary_sensors:
        async_add_entities(binary_sensors)
        _LOGGER.info(f"Adding {len(binary_sensors)} Loggamera binary sensors")


class LoggameraBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Loggamera binary sensor."""

    def __init__(self, coordinator, api, device_id, device_name, device_type, value_data):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_type = device_type
        self._value_data = value_data

        # Value properties
        self._value_name = value_data.get("Name", "Unknown")
        self._clear_name = value_data.get("ClearTextName", self._value_name)

        # Entity attributes
        self._attr_unique_id = f"loggamera_{device_id}_{self._value_name}"
        self._attr_name = f"{device_name} {self._clear_name}"

        # Set device class
        if "alarm" in self._value_name.lower() or "alarm" in self._clear_name.lower():
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        else:
            self._attr_device_class = ALARM_DEVICE_CLASSES.get(device_type)

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": device_name,
            "manufacturer": "Loggamera",
            "model": device_type,
        }

        self._state = False
        self._last_update = None

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        try:
            device_data = self.coordinator.data.get("device_data", {}).get(str(self._device_id))
            if not device_data or "Data" not in device_data or "Values" not in device_data["Data"]:
                return self._state

            for value in device_data["Data"]["Values"]:
                if value.get("Name") == self._value_name:
                    value_str = str(value.get("Value", "")).lower()
                    self._state = value_str in ["true", "yes", "1", "on"]

                    # Update timestamp if available
                    if "LogDateTimeUtc" in device_data["Data"]:
                        self._last_update = device_data["Data"]["LogDateTimeUtc"]

                    return self._state

            return self._state
        except Exception as err:
            _LOGGER.error(f"Error getting state for {self.name}: {err}")
            return self._state

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return extra state attributes."""
        attrs = {
            ATTR_DEVICE_TYPE: self._device_type,
        }

        if self._last_update:
            attrs["last_update"] = self._last_update

        return attrs


class LoggameraAPIHealthSensor(CoordinatorEntity, BinarySensorEntity):
    """Diagnostic sensor that tracks API health and data gaps."""

    def __init__(self, coordinator, api):
        """Initialize the API health sensor."""
        super().__init__(coordinator)
        self.api = api

        # Entity attributes
        # Legacy unique ID is kept for organization entries so existing entities aren't orphaned
        fixed = coordinator.fixed_device
        self._attr_unique_id = (
            f"loggamera_api_health_{fixed['Id']}" if fixed else "loggamera_api_health"
        )
        self._attr_name = "Loggamera API Health"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:api"

        # Device info for integration
        self._attr_device_info = {
            "identifiers": {
                (
                    DOMAIN,
                    f"loggamera_integration_{fixed['Id']}" if fixed else "loggamera_integration",
                )
            },
            "name": f"Loggamera Integration {fixed['Id']}" if fixed else "Loggamera Integration",
            "manufacturer": "Loggamera",
            "model": "API Client",
        }

    @property
    def is_on(self):
        """Return true if there are API health issues (data gaps)."""
        try:
            # Get data gap status from API client
            gap_status = self.api.get_data_gap_status()

            # Sensor is "on" (problem state) if there are active data gaps
            return gap_status.get("devices_with_gaps", 0) > 0
        except Exception as err:
            _LOGGER.error(f"Error getting API health status: {err}")
            return False

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return detailed API health information."""
        try:
            gap_status = self.api.get_data_gap_status()

            attrs = {
                "devices_with_gaps": gap_status.get("devices_with_gaps", 0),
                "total_devices_tracked": gap_status.get("total_devices_tracked", 0),
                "last_update": (
                    self.coordinator.last_update_success_time.isoformat()
                    if hasattr(self.coordinator, "last_update_success_time")
                    and self.coordinator.last_update_success_time
                    else None
                ),
            }

            # Add details for devices with active gaps
            devices_with_gaps = []
            for device_id, device_status in gap_status.get("devices", {}).items():
                if device_status.get("has_active_gap", False):
                    device_info = {
                        "device_id": device_id,
                        "gap_duration_minutes": device_status.get("gap_duration_minutes", 0),
                        "consecutive_failures": device_status.get("consecutive_failures", 0),
                        "endpoint": device_status.get("endpoint", "unknown"),
                        "total_gaps": device_status.get("total_gaps", 0),
                    }
                    devices_with_gaps.append(device_info)

            if devices_with_gaps:
                attrs["affected_devices"] = devices_with_gaps

            # Add summary statistics
            if gap_status.get("devices"):
                total_gaps = sum(
                    device.get("total_gaps", 0) for device in gap_status["devices"].values()
                )
                attrs["total_gaps_all_devices"] = total_gaps

                # Find device with longest gap
                max_gap_device = None
                max_gap_duration = 0
                for device_id, device_status in gap_status["devices"].items():
                    gap_duration = device_status.get("gap_duration_minutes", 0)
                    if gap_duration > max_gap_duration:
                        max_gap_duration = gap_duration
                        max_gap_device = device_id

                if max_gap_device:
                    attrs["longest_gap_device"] = max_gap_device
                    attrs["longest_gap_minutes"] = max_gap_duration

            return attrs
        except Exception as err:
            _LOGGER.error(f"Error getting API health attributes: {err}")
            return {
                "error": str(err),
                "last_update": None,
            }
