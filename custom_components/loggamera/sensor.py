"""Sensor platform for Loggamera integration."""

import logging
from typing import Any, Dict, Iterable, List, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor_map import SENSOR_MAP

_LOGGER = logging.getLogger(__name__)

# Suggested area per device class for the HA device card
SUGGESTED_AREAS = {
    "PowerMeter": "Energy",
    "WaterMeter": "Utility",
    "RoomSensor": "Climate",
    "HeatPump": "HVAC",
    "CoolingUnit": "HVAC",
}

# Organization-level sensors (synthesized in setup; values fetched on property access)
ORG_SENSOR_NAMES = (
    "device_count",
    "organization_count",
    "child_organizations",
    "parent_organization",
    "user_count",
    "member_count",
    "is_parent_organization",
)

# Unit types coming back from the API as BOOLEAN
BOOLEAN_UNIT_TYPES = {"BooleanOnOff", "BooleanYesNo"}

# Used for dynamic detection when a sensor isn't in SENSOR_MAP. Each rule is a
# predicate over (unit_type, presentation, clear_text, name) returning sensor
# attrs, or None to skip. First match wins.
DetectionResult = Dict[str, Any]


def _matches_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(n in haystack for n in needles)


def _detect_sensor_attributes(
    unit_type: str, presentation: str, clear_text: str, name: str
) -> Optional[DetectionResult]:
    """Best-effort detection for sensors that aren't in SENSOR_MAP.

    Returns sensor attrs (device_class, unit, state_class, name) or None if
    nothing useful could be inferred.
    """
    display_name = (clear_text or name).title() if (clear_text or name) else None

    if (
        unit_type in {"degreescelsius", "celsius"}
        or "°c" in presentation
        or "celsius" in presentation
        or _matches_any(clear_text, ("temp", "temperatur"))
        or _matches_any(name, ("temp", "temperatur"))
    ):
        return {
            "device_class": SensorDeviceClass.TEMPERATURE,
            "unit": UnitOfTemperature.CELSIUS,
            "state_class": SensorStateClass.MEASUREMENT,
            "name": display_name,
        }

    if (
        unit_type in {"kwh", "kilowatthour"}
        or "kwh" in presentation
        or _matches_any(clear_text, ("energy", "energi", "förbrukning"))
        or _matches_any(name, ("energy", "consumed", "total"))
    ):
        return {
            "device_class": SensorDeviceClass.ENERGY,
            "unit": UnitOfEnergy.KILO_WATT_HOUR,
            "state_class": SensorStateClass.TOTAL_INCREASING,
            "name": display_name,
        }

    if (
        unit_type in {"kw", "kilowatt", "w", "watt"}
        or _matches_any(presentation, ("kw", "w"))
        or _matches_any(clear_text, ("power", "effekt", "watt"))
        or _matches_any(name, ("power", "watt"))
    ):
        unit = (
            UnitOfPower.KILO_WATT
            if "kw" in presentation or "kilowatt" in unit_type
            else UnitOfPower.WATT
        )
        return {
            "device_class": SensorDeviceClass.POWER,
            "unit": unit,
            "state_class": SensorStateClass.MEASUREMENT,
            "name": display_name,
        }

    if unit_type in {"ampere", "amp", "a"} or _matches_any(presentation, ("a", "amp")):
        return {
            "device_class": SensorDeviceClass.CURRENT,
            "unit": UnitOfElectricCurrent.AMPERE,
            "state_class": SensorStateClass.MEASUREMENT,
            "name": display_name,
        }

    if unit_type in {"volt", "v"} or _matches_any(presentation, ("v", "volt")):
        return {
            "device_class": SensorDeviceClass.VOLTAGE,
            "unit": UnitOfElectricPotential.VOLT,
            "state_class": SensorStateClass.MEASUREMENT,
            "name": display_name,
        }

    if (
        unit_type in {"m3", "cubicmeter", "liter", "litre"}
        or _matches_any(presentation, ("m³", "m3", "l"))
        or _matches_any(clear_text, ("water", "vatten", "volume"))
        or _matches_any(name, ("water", "consumed"))
    ):
        unit = (
            UnitOfVolume.CUBIC_METERS
            if "m3" in presentation or "m³" in presentation or "cubicmeter" in unit_type
            else UnitOfVolume.LITERS
        )
        return {
            "device_class": SensorDeviceClass.WATER,
            "unit": unit,
            "state_class": SensorStateClass.TOTAL_INCREASING,
            "name": display_name,
        }

    if (
        unit_type in {"percent", "percentage", "rh"}
        or _matches_any(presentation, ("%", "rh"))
        or _matches_any(clear_text, ("humidity", "fuktighet"))
        or _matches_any(name, ("humidity", "rh"))
    ):
        return {
            "device_class": SensorDeviceClass.HUMIDITY,
            "unit": PERCENTAGE,
            "state_class": SensorStateClass.MEASUREMENT,
            "name": display_name,
        }

    if (
        unit_type in {"boolean", "booleanonoff", "booleanyesno"}
        or _matches_any(clear_text, ("active", "on", "off", "alarm"))
        or _matches_any(name, ("active", "alarm", "status"))
    ):
        return {
            "device_class": None,
            "unit": None,
            "state_class": None,
            "name": display_name,
        }

    return None


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Loggamera sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    if not coordinator.data or "devices" not in coordinator.data:
        _LOGGER.error("No devices data in coordinator")
        return

    devices = coordinator.data.get("devices", [])
    seen_unique_ids: set = set()
    entities: List[LoggameraSensor] = []

    for device in devices:
        entities.extend(_build_device_entities(coordinator, api, device, seen_unique_ids))
        entities.extend(_build_raw_data_entities(coordinator, api, device, seen_unique_ids))

    if devices:
        entities.extend(_build_organization_entities(coordinator, api))

    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} Loggamera sensor entities")
    else:
        _LOGGER.warning("No Loggamera sensors added")


def _build_device_entities(
    coordinator, api, device: Dict[str, Any], seen_unique_ids: set
) -> List["LoggameraSensor"]:
    """Build entities from the standard device data block for one device."""
    device_id = device["Id"]
    device_type = device["Class"]
    device_name = device.get("Title", f"{device_type} {device_id}")

    device_data = coordinator.data.get("device_data", {}).get(
        str(device_id)
    ) or coordinator.data.get("device_data", {}).get(device_id)
    if not device_data or not (device_data.get("Data") or {}).get("Values"):
        if not device_data:
            _LOGGER.warning(f"No device data found for {device_name}")
        return []

    entities: List[LoggameraSensor] = []
    for value in device_data["Data"]["Values"]:
        if not value.get("ClearTextName") and not value.get("Name"):
            continue
        if not _should_create_entity(value, device_type):
            continue

        unique_id = f"loggamera_{device_id}_{value.get('Name', '')}"
        if unique_id in seen_unique_ids:
            continue
        seen_unique_ids.add(unique_id)

        entities.append(
            LoggameraSensor(coordinator, api, device_id, device_type, device_name, value)
        )
    return entities


def _should_create_entity(value: Dict[str, Any], device_type: str) -> bool:
    """Decide whether to expose this API value as an entity."""
    value_type = value.get("ValueType", "DECIMAL")
    if value_type in {"BOOLEAN", "STRING"}:
        return True
    raw = value.get("Value", "")
    if raw == "":
        return False
    if device_type == "PowerMeter":
        return True
    try:
        float(raw)
    except (ValueError, TypeError):
        return False
    return True


def _build_raw_data_entities(
    coordinator, api, device: Dict[str, Any], seen_unique_ids: set
) -> List["LoggameraSensor"]:
    """Build entities from the separate RawData block for one device."""
    device_id = device["Id"]
    device_type = device["Class"]
    device_name = device.get("Title", f"{device_type} {device_id}")

    raw_data = coordinator.data.get("device_data", {}).get(f"rawdata_{device_id}")
    if not raw_data or not (raw_data.get("Data") or {}).get("Values"):
        return []

    entities: List[LoggameraSensor] = []
    for value in raw_data["Data"]["Values"]:
        unique_id = f"rawdata_{device_id}_{device_type.lower()}_{value.get('Name', 'unknown')}"
        if unique_id in seen_unique_ids:
            continue
        seen_unique_ids.add(unique_id)
        entities.append(
            LoggameraSensor(
                coordinator, api, device_id, device_type, device_name, value, is_raw_data=True
            )
        )
    return entities


def _build_organization_entities(coordinator, api) -> List["LoggameraSensor"]:
    """Build organization-level sensors (one device, several values)."""
    org_name = (
        f"Organization {api.organization_id}" if api.organization_id else "Loggamera Organization"
    )
    entities: List[LoggameraSensor] = []
    for sensor_name in ORG_SENSOR_NAMES:
        value_data = {
            "Name": sensor_name,
            "Value": None,  # native_value pulls live from the coordinator
            "ClearTextName": SENSOR_MAP[sensor_name]["name"],
            "UnitType": "Count",
            "UnitPresentation": "",
            "ValueType": "INTEGER",
        }
        entities.append(
            LoggameraSensor(
                coordinator,
                api,
                device_id="organization",
                device_type="Organization",
                device_name=org_name,
                value_data=value_data,
                is_organization=True,
            )
        )
    return entities


# ---------------------------------------------------------------------------
# Sensor entity
# ---------------------------------------------------------------------------


class LoggameraSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Loggamera sensor."""

    def __init__(
        self,
        coordinator,
        api,
        device_id,
        device_type: str,
        device_name: str,
        value_data: Dict[str, Any],
        is_raw_data: bool = False,
        is_organization: bool = False,
    ):
        super().__init__(coordinator)
        self.api = api
        self.device_id = device_id
        self.device_type = device_type
        self.device_name = device_name
        self.value_data = value_data
        self.is_raw_data = is_raw_data
        self.is_organization = is_organization
        self.sensor_name = value_data.get("Name", "unknown")

        self._sensor_unit = value_data.get("UnitPresentation", "")
        self._is_boolean, self._is_string = _infer_value_kind(value_data)

        sensor_info = self._lookup_sensor_info()
        display_name = (
            sensor_info.get("name") or value_data.get("ClearTextName") or self.sensor_name
        )

        self._attr_unique_id = self._build_unique_id()
        self._attr_name = self._build_display_name(display_name)
        if is_raw_data:
            self._attr_entity_registry_enabled_default = False

        self._set_sensor_attributes(sensor_info)

    def _lookup_sensor_info(self) -> Dict[str, Any]:
        """Look up SENSOR_MAP, falling back to dynamic detection."""
        info = SENSOR_MAP.get(self.sensor_name)
        if info:
            return info
        detected = _detect_sensor_attributes(
            self.value_data.get("UnitType", "").lower(),
            self.value_data.get("UnitPresentation", "").lower(),
            self.value_data.get("ClearTextName", "").lower(),
            self.sensor_name.lower(),
        )
        if detected:
            _LOGGER.info(f"Used dynamic detection for unknown sensor: {self.sensor_name}")
            return detected
        _LOGGER.warning(
            f"No mapping or detection for sensor {self.sensor_name} "
            f"(UnitType: {self.value_data.get('UnitType', '')})"
        )
        return {}

    def _build_unique_id(self) -> str:
        """Build the entity unique_id; numeric device IDs go through int() for stability."""
        if self.is_organization:
            slug = self.sensor_name.lower().replace(" ", "_")
            return f"loggamera_org_{slug}"
        try:
            normalized_id = int(self.device_id)
        except (ValueError, TypeError):
            normalized_id = self.device_id
        if self.is_raw_data:
            return f"rawdata_{normalized_id}_{self.device_type.lower()}_{self.sensor_name}"
        return f"loggamera_{normalized_id}_{self.sensor_name}"

    def _build_display_name(self, display_name: str) -> str:
        """Display: 'Total Energy Consumption - (D5 mätare: 99954807)' style."""
        if self.is_organization:
            return display_name
        identifier = ""
        if "(" in self.device_name and ")" in self.device_name:
            start = self.device_name.find("(")
            end = self.device_name.rfind(")")
            identifier = self.device_name[start : end + 1]
        return f"{display_name} - {identifier}" if identifier else display_name

    def _set_sensor_attributes(self, sensor_info: Dict[str, Any]) -> None:
        """Apply device class / state class / unit / icon from the resolved sensor info."""
        if self.is_organization:
            if self.sensor_name == "device_count":
                self._attr_state_class = SensorStateClass.MEASUREMENT
                self._attr_native_unit_of_measurement = "devices"
                self._attr_icon = "mdi:counter"
            return

        if self._is_boolean and self.sensor_name == "alarmActive":
            self._attr_icon = self._alarm_icon(self.value_data.get("Value", ""))
        elif self._is_string and self.sensor_name == "alarmInClearText":
            self._attr_icon = "mdi:alert-box"

        if self._is_boolean or self._is_string:
            return

        self._attr_device_class = sensor_info.get("device_class")
        self._attr_state_class = sensor_info.get("state_class")
        self._attr_native_unit_of_measurement = sensor_info.get("unit", self._sensor_unit)
        if "icon" in sensor_info:
            self._attr_icon = sensor_info["icon"]

    @staticmethod
    def _alarm_icon(value: Any) -> str:
        is_active = value.lower() == "true" if isinstance(value, str) else bool(value)
        return "mdi:alert-circle" if is_active else "mdi:alert-circle-outline"

    # -- value parsing -------------------------------------------------------

    def _parse_value(self, value: Any) -> Any:
        """Coerce an API value into the right Python type."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if self._is_boolean:
                return value.lower() in {"true", "1", "on", "yes"}
            if not value:
                return None
            if self._is_string:
                return value[:255]
            try:
                return float(value.replace(",", "."))
            except ValueError:
                return value[:255]

        if self._is_boolean:
            return bool(value)
        if isinstance(value, (int, float)) and not self._is_string:
            return float(value)
        return str(value)[:255]

    # -- coordinator data lookup --------------------------------------------

    def _device_data_key(self):
        return f"rawdata_{self.device_id}" if self.is_raw_data else self.device_id

    def _device_data(self):
        """Find this entity's device data block in the coordinator."""
        data_map = (self.coordinator.data or {}).get("device_data", {})
        key = self._device_data_key()
        return data_map.get(key) or data_map.get(str(key))

    def _find_value(self) -> Optional[Dict[str, Any]]:
        """Locate the matching value entry in the latest device data."""
        device_data = self._device_data()
        if not device_data:
            return None
        values = (device_data.get("Data") or {}).get("Values") or []
        for value in values:
            if value.get("Name") == self.sensor_name:
                return value
        return None

    # -- HA properties ------------------------------------------------------

    @property
    def native_value(self):
        """Return the current value of the sensor."""
        if not self.coordinator.data or "device_data" not in self.coordinator.data:
            return None

        if self.is_organization:
            return self._organization_value()

        value_entry = self._find_value()
        if value_entry is None:
            return None

        raw_value = value_entry.get("Value", "")
        if self._is_boolean and self.sensor_name == "alarmActive":
            self._attr_icon = self._alarm_icon(raw_value)
        return self._parse_value(raw_value)

    @property
    def device_info(self) -> DeviceInfo:
        if self.is_organization:
            return DeviceInfo(
                identifiers={(DOMAIN, "organization")},
                name=self.device_name,
                manufacturer="Loggamera",
                model="Loggamera Organization",
                suggested_area="Energy",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.device_id))},
            name=f"{self.device_type} - {self.device_name}",
            manufacturer="Loggamera",
            model=f"Loggamera {self.device_type}",
            suggested_area=SUGGESTED_AREAS.get(self.device_type),
        )

    @property
    def available(self) -> bool:
        if not self.coordinator.data:
            return False
        if self.is_organization:
            if self.sensor_name == "device_count":
                return "devices" in self.coordinator.data
            return True
        return self._find_value() is not None

    # -- organization sensor values -----------------------------------------

    def _organization_value(self):
        data = self.coordinator.data
        organizations = data.get("organizations", []) or []
        current = self._current_org(organizations)

        if self.sensor_name == "device_count":
            return len(data.get("devices", []) or [])
        if self.sensor_name == "organization_count":
            return len(organizations)
        if self.sensor_name == "child_organizations":
            return self._child_org_count(organizations)
        if self.sensor_name == "is_parent_organization":
            return self._child_org_count(organizations) > 0
        if self.sensor_name == "parent_organization":
            return self._parent_org_name(organizations, current)
        if self.sensor_name == "user_count":
            return _org_count_field(current, ("UserCount", "Users"), "UserList")
        if self.sensor_name == "member_count":
            return _org_count_field(current, ("MemberCount", "Members"), "MemberList")
        return None

    def _current_org(self, organizations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self.api.organization_id:
            return None
        return next((o for o in organizations if o["Id"] == self.api.organization_id), None)

    def _child_org_count(self, organizations: List[Dict[str, Any]]) -> int:
        if not self.api.organization_id:
            return 0
        return sum(1 for o in organizations if o.get("ParentId") == self.api.organization_id)

    def _parent_org_name(
        self, organizations: List[Dict[str, Any]], current: Optional[Dict[str, Any]]
    ) -> str:
        if not current or not current.get("ParentId"):
            return "None"
        parent = next((o for o in organizations if o["Id"] == current["ParentId"]), None)
        return parent["Name"] if parent else "None"


def _infer_value_kind(value_data: Dict[str, Any]) -> tuple:
    """Infer (is_boolean, is_string) from the API value descriptor."""
    value_type = value_data.get("ValueType")
    if value_type is not None:
        return value_type == "BOOLEAN", value_type == "STRING"
    # ValueType is null in some RawData responses; infer from UnitType
    unit_type = value_data.get("UnitType", "")
    if unit_type in BOOLEAN_UNIT_TYPES:
        return True, False
    return False, False


def _org_count_field(org: Optional[Dict[str, Any]], scalar_keys: tuple, list_key: str) -> int:
    """Return a user/member count from whichever field the API decided to provide."""
    if not org:
        return 0
    if isinstance(org.get(list_key), list):
        return len(org[list_key])
    for key in scalar_keys:
        if key in org:
            return org[key]
    return 0
