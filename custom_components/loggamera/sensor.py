"""Sensor platform for Loggamera integration."""

import logging
from datetime import datetime  # noqa: F401
from typing import Any, Dict, List, Optional  # noqa: F401

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

from .const import (  # noqa: F401
    DOMAIN,
    SENSOR_ENERGY,
    SENSOR_HUMIDITY,
    SENSOR_POWER,
    SENSOR_TEMPERATURE,
    SENSOR_VALUE,
    SENSOR_WATER,
)

_LOGGER = logging.getLogger(__name__)

# Mapping of sensor name to device class and unit
SENSOR_MAP = {
    # PowerMeter standard values - THESE MUST BE PRESERVED
    "ConsumedTotalInkWh": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Energy Consumption",
    },
    "PowerInkW": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.KILO_WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Energy Consumption",
    },
    "alarmActive": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Alarm Status",
        "icon": "mdi:alert-circle",
    },
    "alarmInClearText": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Alarm Context",
        "icon": "mdi:alert-box",
    },
    # Organization sensors
    "device_count": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Total Device Count",
        "icon": "mdi:counter",
    },
    "organization_count": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Total Organization Count",
        "icon": "mdi:domain",
    },
    "parent_organization": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Parent Organization ID",
        "icon": "mdi:account-supervisor",
    },
    "child_organizations": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Child Organization Count",
        "icon": "mdi:account-group",
    },
    "user_count": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "User Count",
        "icon": "mdi:account",
    },
    "member_count": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Member Count",
        "icon": "mdi:account-multiple",
    },
    "is_parent_organization": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Is Parent Organization",
        "icon": "mdi:account-supervisor-circle",
    },
    # RawData specific values - these are the most common ones
    "544352": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Energy Consumed",
    },  # Energy imported
    "544353": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Energy Interval",
    },  # Energy imported interval
    "544399": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power",
    },  # Power
    # Common HeatPump RawData temperature sensors
    "541388": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Hot Water Temperature",
    },  # Varmvattentemp
    "541125": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Set Room Temperature",
    },  # Inställd rumstemperatur
    "541119": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Outdoor Temperature",
    },  # Utetemperatur
    "541655": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Hot Gas Temperature",
    },  # Hetgas (T6)
    "541104": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Heat Carrier 1",
    },  # Värmebärare 1
    "541646": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Heat Carrier Outgoing",
    },  # Värmebärare utgående (T8)
    "541647": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Heat Carrier Incoming",
    },  # Värmebärare ingående (T9)
    "541651": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Brine Incoming",
    },  # Köldbärare ingående (T10)
    "541648": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Brine Outgoing",
    },  # Köldbärare utgående (T11)
    # HeatPump endpoint standard sensor names
    "heatCarrierInTempInDeg": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Heat Carrier Inlet Temperature",
    },
    "heatCarrierOutTempInDeg": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Heat Carrier Outlet Temperature",
    },
    "brineInTempInDeg": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Brine Inlet Temperature",
    },
    "brineOutTempInDeg": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Brine Outlet Temperature",
    },
    "reducedModeActive": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Reduced Mode",
        "icon": "mdi:power-sleep",
    },
    "pumpActivity": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Pump Activity",
        "icon": "mdi:pump",
    },
    "filterAlarmIsActive": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Filter Alarm",
        "icon": "mdi:air-filter",
    },
    "544463": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Energy Phase 1",
    },  # Energy (Phase 1)
    "544464": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Energy Phase 2",
    },  # Energy (Phase 2)
    "544465": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Energy Phase 3",
    },  # Energy (Phase 3)
    "544391": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 1",
    },  # Current (Phase 1)
    "544393": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 2",
    },  # Current (Phase 2)
    "544394": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 3",
    },  # Current (Phase 3)
    "544395": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 1",
    },  # Voltage (Phase 1)
    "544396": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 2",
    },  # Voltage (Phase 2)
    "544397": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 3",
    },  # Voltage (Phase 3)
    "549990": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Energy Generated",
    },  # Exported energy
    "550224": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Energy Generated Interval",
    },  # Exported energy interval
    "550205": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power Phase 1",
    },  # Power phase 1
    "550206": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power Phase 2",
    },  # Power phase 2
    "550207": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power Phase 3",
    },  # Power phase 3
    # HeatMeter RawData sensors
    "544310": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Energy",
    },
    "544311": {
        "device_class": None,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Volume",
    },
    "544320": {
        "device_class": None,
        "unit": "m³/h",
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Flow Rate",
    },
    "544321": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Flow Temperature",
    },
    "544322": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Return Temperature",
    },
    "544323": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Temperature Difference",
    },
    "544324": {
        "device_class": None,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Error Code",
        "icon": "mdi:alert-circle-outline",
    },
    # ChargingStation voltage sensors - corrects API misspelling "Voltate"
    "544426": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 1",  # API says "Voltate (Phase 1)" - corrected
    },
    "544427": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 2",  # API says "Voltate (Phase 2)" - corrected
    },
    "544428": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage Phase 3",  # API says "Voltate (Phase 3)" - corrected
    },
    # RoomSensor signal quality - corrects API misspelling "Signal-Noice"
    "543837": {
        "device_class": None,
        "unit": "dB",
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Signal to Noise Ratio",  # API says "Signal-Noice relation (Snr)" - corrected
        "icon": "mdi:signal",
    },
    # PowerMeter RawData sensors (additional)
    "543817": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Energy",
    },
    "543801": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power Average",
    },
    "543802": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Voltage",
    },
    "543803": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 1",
    },
    "543804": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 2",
    },
    "543805": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 3",
    },
    "543842": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Power Peak",
    },
    "543821": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Consumption Interval",
    },
    # ChargingStation RawData sensors
    "544424": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Consumption",
    },
    "544434": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Session Consumption",
    },
    "544429": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 1",
    },
    "544430": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 2",
    },
    "544431": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Phase 3",
    },
    "544425": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Consumption Interval",
    },
    "544432": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Charging State",
        "icon": "mdi:ev-station",
    },
    "544443": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Load Balanced",
        "icon": "mdi:scale-balance",
    },
    "544441": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Firmware Version",
        "icon": "mdi:chip",
    },
    "544442": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Hardware Version",
        "icon": "mdi:chip",
    },
    "544436": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Status Code A",
        "icon": "mdi:information",
    },
    "544437": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Status Code B",
        "icon": "mdi:information",
    },
    # RoomSensor RawData sensors
    "543700": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Temperature",
    },
    "543701": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Humidity",
    },
    "543709": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Battery",
    },
    "543836": {
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "unit": "dBm",
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Signal Strength RSSI",
        "icon": "mdi:wifi",
    },
    "543838": {
        "device_class": None,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Spreading Factor",
        "icon": "mdi:radio-tower",
    },
    # WaterMeter RawData sensors
    "422568": {
        "device_class": None,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Meter Value",
    },
    "542175": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Consumption Since Midnight",
    },
    "542176": {
        "device_class": None,
        "unit": "L/min",
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Current Flow",
    },
    "544316": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Consumption Interval",
    },
    # Generic Device alarm sensors (available on all devices)
    "alarmCodeNumber": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Alarm Code Number",
        "icon": "mdi:numeric",
    },
    "alarmClassification": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": "Alarm Classification",
        "icon": "mdi:alert-decagram",
    },
}

# Temperature sensor mappings
TEMP_MAPPINGS = {
    "TemperatureInC": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "HumidityInRH": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
}

# Water sensor mappings
WATER_MAPPINGS = {
    "ConsumedTotalInm3": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Water Consumption",
    },
    "ConsumedTotalInM3": {  # Note: Capital M3 variant
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Total Water Consumption",
    },
    "ConsumedSinceMidnightInLiters": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": "Water Used Since Midnight",
    },
}

# Combine all mappings
SENSOR_MAP.update(TEMP_MAPPINGS)
SENSOR_MAP.update(WATER_MAPPINGS)


async def async_setup_entry(  # noqa: C901
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Loggamera sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    processed_unique_ids = set()  # Track which sensors we've already created

    if not coordinator.data or "devices" not in coordinator.data:
        _LOGGER.error("No devices data in coordinator")
        return

    for device in coordinator.data.get("devices", []):
        device_id = device["Id"]
        device_type = device["Class"]
        device_name = device.get("Title", f"{device_type} {device_id}")

        _LOGGER.debug(
            f"Setting up sensors for device: {device_name} (ID: {device_id}, Type: {device_type})"  # noqa: E501
        )

        # Get device data from coordinator
        device_data = coordinator.data.get("device_data", {}).get(str(device_id))
        if not device_data:
            # Try with integer key as fallback
            device_data = coordinator.data.get("device_data", {}).get(device_id)

        if not device_data:
            _LOGGER.warning(f"No device data found for {device_name}")
            continue

        if "Data" not in device_data or device_data["Data"] is None:
            _LOGGER.warning(f"No 'Data' in device data for {device_name}")
            continue

        # Log data sources used
        data_sources = []
        if device_data.get("_raw_data_used"):
            data_sources.append("RawData")
        if device_data.get("_power_meter_used"):
            data_sources.append("PowerMeter")
        if device_data.get("_endpoint_used"):
            data_sources.append(device_data["_endpoint_used"])
        if device_data.get("_generic_device_used"):
            data_sources.append("GenericDevice")

        if data_sources:
            _LOGGER.debug(f"Device {device_name} data sources: {', '.join(data_sources)}")

        if "Values" in device_data["Data"]:
            values = device_data["Data"]["Values"]
            if not values:
                _LOGGER.warning(f"Device {device_name} has no sensor values")
                continue

            # Create sensor entities for each value
            for value in values:
                # Skip empty or unlabeled values
                if not value.get("ClearTextName") and not value.get("Name"):
                    continue

                # Get value name and type
                value_name = value.get("Name", "")
                value_type = value.get("ValueType", "DECIMAL")
                is_boolean = value_type == "BOOLEAN"
                is_string = value_type == "STRING"

                # For non-numeric values, check if we should include them
                if not is_boolean and not is_string:
                    # Skip empty values (but allow boolean false values)
                    if value.get("Value", "") == "":
                        continue

                # Generate a unique ID for this sensor
                unique_id = f"loggamera_{device_id}_{value_name}"

                # Skip if we've already processed this unique ID
                if unique_id in processed_unique_ids:
                    continue
                processed_unique_ids.add(unique_id)

                # For PowerMeter devices, include all values including non-numeric
                if device_type == "PowerMeter":
                    # Include all PowerMeter values
                    entity = LoggameraSensor(
                        coordinator=coordinator,
                        api=api,
                        device_id=device_id,
                        device_type=device_type,
                        device_name=device_name,
                        value_data=value,
                        hass=hass,
                    )
                    entities.append(entity)
                    _LOGGER.debug(
                        f"Created sensor: {entity.name} with value: {value.get('Value')}"  # noqa: E501
                    )
                else:
                    # For other device types, only include numeric values
                    try:
                        # Try to convert to float for numeric check
                        float(value.get("Value", "0"))
                        is_numeric = True
                    except (ValueError, TypeError):
                        is_numeric = False

                    if is_numeric:
                        entity = LoggameraSensor(
                            coordinator=coordinator,
                            api=api,
                            device_id=device_id,
                            device_type=device_type,
                            device_name=device_name,
                            value_data=value,
                            hass=hass,
                        )
                        entities.append(entity)
                        _LOGGER.debug(
                            f"Created sensor: {entity.name} with value: {value.get('Value')}"  # noqa: E501
                        )
        else:
            _LOGGER.warning(f"No 'Values' data for device {device_name}")

    # Process RawData entities separately (disabled by default)
    _LOGGER.debug("Processing RawData entities...")
    for device in coordinator.data.get("devices", []):
        device_id = device["Id"]
        device_type = device["Class"]
        device_name = device.get("Title", f"{device_type} {device_id}")

        # Look for separately collected RawData
        raw_data_key = f"rawdata_{device_id}"
        raw_data = coordinator.data.get("device_data", {}).get(raw_data_key)

        if raw_data and "Data" in raw_data and raw_data["Data"] and "Values" in raw_data["Data"]:
            _LOGGER.debug(
                f"Processing {len(raw_data['Data']['Values'])} RawData values " f"for {device_name}"
            )

            for value in raw_data["Data"]["Values"]:
                # Create unique ID to avoid conflicts with processed sensors
                unique_id = (
                    f"rawdata_{device_id}_{device_type.lower()}_" f"{value.get('Name', 'unknown')}"
                )

                if unique_id not in processed_unique_ids:
                    # Create RawData sensor
                    entity = LoggameraSensor(
                        coordinator=coordinator,
                        api=api,
                        device_id=device_id,
                        device_type=device_type,
                        device_name=device_name,
                        value_data=value,
                        hass=hass,
                        is_raw_data=True,  # Flag to indicate this is RawData
                    )
                    entities.append(entity)
                    processed_unique_ids.add(unique_id)
                    _LOGGER.debug(f"Created RawData sensor: {entity.name} (disabled by default)")

    # Create organization-level sensors (not for device-scoped keys: no organization data)
    if coordinator.data.get("devices") and not coordinator.fixed_device:
        device_count = len(coordinator.data["devices"])
        organization_name = (
            f"Organization {api.organization_id}"
            if api.organization_id
            else "Loggamera Organization"
        )

        # Get organization data for enhanced sensors
        organizations_data = coordinator.data.get("organizations", [])
        current_org = None
        child_orgs_count = 0
        total_orgs_count = len(organizations_data)
        parent_org_name = "None"
        user_count = 0
        member_count = 0

        if api.organization_id and organizations_data:
            # Find current organization
            current_org = next(
                (org for org in organizations_data if org["Id"] == api.organization_id),
                None,
            )
            if current_org:
                # Count child organizations
                child_orgs_count = len(
                    [
                        org
                        for org in organizations_data
                        if org.get("ParentId") == api.organization_id
                    ]
                )
                # Find parent organization name
                if current_org.get("ParentId", 0) != 0:
                    parent_org = next(
                        (org for org in organizations_data if org["Id"] == current_org["ParentId"]),
                        None,
                    )
                    if parent_org:
                        parent_org_name = parent_org["Name"]

                # Future-ready: Check for user/member data in API response
                # These fields don't exist yet but will be used automatically when API provides them
                user_count = current_org.get("UserCount", current_org.get("Users", 0))
                member_count = current_org.get("MemberCount", current_org.get("Members", 0))

                # Also check for alternative field names the API might use
                if isinstance(current_org.get("UserList"), list):
                    user_count = len(current_org["UserList"])
                if isinstance(current_org.get("MemberList"), list):
                    member_count = len(current_org["MemberList"])

        # Create multiple organization sensors
        org_sensors = [
            {
                "Name": "device_count",
                "Value": device_count,
                "ClearTextName": "Total Device Count",
            },
            {
                "Name": "organization_count",
                "Value": total_orgs_count,
                "ClearTextName": "Total Organization Count",
            },
            {
                "Name": "child_organizations",
                "Value": child_orgs_count,
                "ClearTextName": "Child Organization Count",
            },
            {
                "Name": "parent_organization",
                "Value": parent_org_name,
                "ClearTextName": "Parent Organization ID",
            },
            {
                "Name": "user_count",
                "Value": user_count,  # Future-ready: will use API data when available
                "ClearTextName": "User Count",
            },
            {
                "Name": "member_count",
                "Value": member_count,  # Future-ready: will use API data when available
                "ClearTextName": "Member Count",
            },
            {
                "Name": "is_parent_organization",
                "Value": child_orgs_count > 0,  # True if this org has children (is a parent)
                "ClearTextName": "Is Parent Organization",
            },
        ]

        # Create organization sensors
        for sensor_data in org_sensors:
            org_value_data = {
                **sensor_data,
                "UnitType": ("Count" if isinstance(sensor_data["Value"], int) else "String"),
                "UnitPresentation": "",
                "ValueType": ("INTEGER" if isinstance(sensor_data["Value"], int) else "STRING"),
            }
            org_entity = LoggameraSensor(
                coordinator=coordinator,
                api=api,
                device_id="organization",
                device_type="Organization",
                device_name=organization_name,
                value_data=org_value_data,
                hass=hass,
                is_organization=True,
            )
            entities.append(org_entity)
            _LOGGER.debug(
                f"Created organization sensor: {org_entity.name} = {sensor_data['Value']}"
            )

    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} Loggamera sensor entities")
    else:
        _LOGGER.warning("No Loggamera sensors added")


class LoggameraSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Loggamera sensor."""

    def __init__(  # noqa: C901
        self,
        coordinator,
        api,
        device_id,
        device_type,
        device_name,
        value_data,
        hass,
        is_raw_data=False,
        is_organization=False,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.api = api
        self.device_id = device_id
        self.device_type = device_type
        self.device_name = device_name
        self.value_data = value_data
        self.hass = hass
        self.is_raw_data = is_raw_data
        self.is_organization = is_organization
        self.sensor_name = value_data.get("Name", "unknown")

        # Initialize sensor attributes
        self._sensor_value = None
        self._sensor_unit = value_data.get("UnitPresentation", "")
        self._unit_type = value_data.get("UnitType", "")

        # Determine value type - handle null ValueType by inferring from UnitType
        value_type = value_data.get("ValueType")
        unit_type = value_data.get("UnitType", "")
        value = value_data.get("Value", "")

        # If ValueType is null (common in RawData responses), infer from UnitType
        if value_type is None:
            if unit_type in ["BooleanOnOff", "BooleanYesNo"]:
                self._is_boolean = True
                self._is_string = False
            elif unit_type == "Unitless" and str(value).replace(".", "").isdigit():
                # Unitless numeric values (like counters, indexes)
                self._is_boolean = False
                self._is_string = False
            elif unit_type in ["DegreesCelsius", "DegreesKelvin", "DegreesFahrenheit"]:
                # Temperature values are always numeric
                self._is_boolean = False
                self._is_string = False
            else:
                # Default to numeric for other measurement types
                self._is_boolean = False
                self._is_string = False
        else:
            # Use explicit ValueType when available
            self._is_boolean = value_type == "BOOLEAN"
            self._is_string = value_type == "STRING"

        # Get friendly name from SENSOR_MAP if available
        sensor_info = SENSOR_MAP.get(self.sensor_name, {})
        friendly_name = sensor_info.get("name")

        # If not found in hardcoded map, try dynamic detection for name
        if not friendly_name:
            dynamic_info = self._detect_sensor_attributes_dynamically()
            friendly_name = dynamic_info.get("name") if dynamic_info else None

        # Use friendly name if available, otherwise use ClearTextName or sensor name
        display_name = (
            friendly_name if friendly_name else value_data.get("ClearTextName", self.sensor_name)
        )

        # Extract device identifier (part in parentheses) for display names
        device_identifier = ""
        if "(" in device_name and ")" in device_name:
            # Extract everything from first ( to last )
            start = device_name.find("(")
            end = device_name.rfind(")")
            device_identifier = device_name[start : end + 1]

        # Clean names for entity IDs (remove special characters, spaces to underscores)
        clean_sensor_name = (
            display_name.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(":", "")
        )
        clean_device_name = (
            device_name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(":", "")
        )

        # Set entity naming based on device type
        if self.is_organization:
            # Use organization naming pattern: loggamera_org_{sensor_name}
            self._attr_unique_id = f"loggamera_org_{clean_sensor_name}"
            self._attr_name = display_name
        elif self.is_raw_data:
            # Use rawdata naming pattern: rawdata_{sensor}_{id}_{device}
            self._attr_unique_id = f"rawdata_{clean_sensor_name}_{device_id}_{clean_device_name}"

            # Display name: "Energy Phase 3 - (D5 mätare: 99954807)"
            self._attr_name = (
                f"{display_name} - {device_identifier}" if device_identifier else display_name
            )
            # Disable RawData entities by default
            self._attr_entity_registry_enabled_default = False
        else:
            # Use standard naming pattern: loggamera_{sensor}_{id}_{device}
            self._attr_unique_id = f"loggamera_{clean_sensor_name}_{device_id}_{clean_device_name}"

            # Display name: "Total Energy Consumption - (D5 mätare: 99954807)"
            self._attr_name = (
                f"{display_name} - {device_identifier}" if device_identifier else display_name
            )

        # Ensure consistent device ID format
        try:
            if self.is_raw_data:
                device_type_lower = device_type.lower()
                self._attr_unique_id = (
                    f"rawdata_{int(device_id)}_{device_type_lower}_{self.sensor_name}"
                )
            else:
                self._attr_unique_id = f"loggamera_{int(device_id)}_{self.sensor_name}"
        except (ValueError, TypeError):
            pass

        # Determine device class, state class, and unit of measurement
        self._set_sensor_attributes()

        _LOGGER.debug(f"Initialized sensor: {self.name} with value: {value_data.get('Value')}")

    def _parse_value(self, value):  # noqa: C901
        """Parse value to the correct type with proper sanitization."""
        if value is None:
            return None

        # Handle string values
        if isinstance(value, str):
            # Remove any leading/trailing whitespace
            value = value.strip()

            # Check for empty strings
            if not value and not self._is_boolean:
                return None

            # For boolean values, convert to boolean
            if self._is_boolean:
                # Handle various boolean representations
                value_lower = value.lower()
                if value_lower in ["true", "1", "on", "yes"]:
                    return True
                elif value_lower in ["false", "0", "off", "no", ""]:
                    return False
                else:
                    # Default to false for unknown boolean values
                    return False

            # For string values, return as is (but sanitized)
            if self._is_string:
                # Limit string length for safety
                return value[:255]

            # Try to convert to float for numeric values
            try:
                # Convert to float, handling comma as decimal separator (European format)  # noqa: E501
                value = value.replace(",", ".")
                return float(value)
            except (ValueError, TypeError):
                # Not a number, return as is (but sanitized)
                return value[:255]

        # If it's already a boolean, return it
        if isinstance(value, bool) and self._is_boolean:
            return value

        # Handle numeric boolean values (0/1)
        if self._is_boolean and isinstance(value, (int, float)):
            return bool(value)

        # If it's already a number, return it
        if isinstance(value, (int, float)) and not self._is_boolean and not self._is_string:
            return float(value)

        # For any other type, convert to string and sanitize
        return str(value)[:255]

    def _detect_sensor_attributes_dynamically(self):  # noqa: C901
        """Dynamically detect sensor attributes for unknown sensors.

        Analyzes UnitType, UnitPresentation, ClearTextName, and sensor name
        to intelligently determine device_class, unit, and state_class.

        Returns:
            Dict with detected sensor attributes
        """
        detected = {}

        unit_type = self.value_data.get("UnitType", "").lower()
        unit_presentation = self.value_data.get("UnitPresentation", "").lower()
        clear_text_name = self.value_data.get("ClearTextName", "").lower()
        sensor_name = self.sensor_name.lower()

        # Temperature detection
        if (
            unit_type in ["degreescelsius", "celsius"]
            or "°c" in unit_presentation
            or "celsius" in unit_presentation
            or any(temp_word in clear_text_name for temp_word in ["temp", "temperatur"])
            or any(temp_word in sensor_name for temp_word in ["temp", "temperatur"])
        ):
            detected.update(
                {
                    "device_class": SensorDeviceClass.TEMPERATURE,
                    "unit": UnitOfTemperature.CELSIUS,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(
                f"Dynamic detection: {sensor_name} → TEMPERATURE " f"(UnitType: {unit_type})"
            )

        # Energy detection
        elif (
            unit_type in ["kwh", "kilowatthour"]
            or "kwh" in unit_presentation
            or any(
                energy_word in clear_text_name
                for energy_word in ["energy", "energi", "förbrukning"]
            )
            or any(energy_word in sensor_name for energy_word in ["energy", "consumed", "total"])
        ):
            detected.update(
                {
                    "device_class": SensorDeviceClass.ENERGY,
                    "unit": UnitOfEnergy.KILO_WATT_HOUR,
                    "state_class": SensorStateClass.TOTAL_INCREASING,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → ENERGY (UnitType: {unit_type})")

        # Power detection
        elif (
            unit_type in ["kw", "kilowatt", "w", "watt"]
            or "kw" in unit_presentation
            or "w" in unit_presentation
            or any(power_word in clear_text_name for power_word in ["power", "effekt", "watt"])
            or any(power_word in sensor_name for power_word in ["power", "watt"])
        ):
            # Determine if kilowatt or watt based on presentation
            if "kw" in unit_presentation.lower() or "kilowatt" in unit_type:
                unit = UnitOfPower.KILO_WATT
            else:
                unit = UnitOfPower.WATT
            detected.update(
                {
                    "device_class": SensorDeviceClass.POWER,
                    "unit": unit,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → POWER (UnitType: {unit_type})")

        # Current detection
        elif (
            unit_type in ["ampere", "amp", "a"]
            or "a" in unit_presentation
            or "amp" in unit_presentation
        ):
            detected.update(
                {
                    "device_class": SensorDeviceClass.CURRENT,
                    "unit": UnitOfElectricCurrent.AMPERE,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → CURRENT (UnitType: {unit_type})")

        # Voltage detection
        elif unit_type in ["volt", "v"] or "v" in unit_presentation or "volt" in unit_presentation:
            detected.update(
                {
                    "device_class": SensorDeviceClass.VOLTAGE,
                    "unit": UnitOfElectricPotential.VOLT,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → VOLTAGE (UnitType: {unit_type})")

        # Water/Volume detection
        elif (
            unit_type in ["m3", "cubicmeter", "liter", "litre"]
            or "m³" in unit_presentation
            or "m3" in unit_presentation
            or "l" in unit_presentation
            or any(water_word in clear_text_name for water_word in ["water", "vatten", "volume"])
            or any(water_word in sensor_name for water_word in ["water", "consumed"])
        ):
            if "m3" in unit_presentation or "m³" in unit_presentation or "cubicmeter" in unit_type:
                unit = UnitOfVolume.CUBIC_METERS
            else:
                unit = UnitOfVolume.LITERS
            detected.update(
                {
                    "device_class": SensorDeviceClass.WATER,
                    "unit": unit,
                    "state_class": SensorStateClass.TOTAL_INCREASING,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → WATER (UnitType: {unit_type})")

        # Humidity detection
        elif (
            unit_type in ["percent", "percentage", "rh"]
            or "%" in unit_presentation
            or "rh" in unit_presentation
            or any(humidity_word in clear_text_name for humidity_word in ["humidity", "fuktighet"])
            or any(humidity_word in sensor_name for humidity_word in ["humidity", "rh"])
        ):
            detected.update(
                {
                    "device_class": SensorDeviceClass.HUMIDITY,
                    "unit": PERCENTAGE,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → HUMIDITY (UnitType: {unit_type})")

        # Boolean detection
        elif (
            unit_type in ["boolean", "booleanonoff", "booleanyesno"]
            or any(bool_word in clear_text_name for bool_word in ["active", "on", "off", "alarm"])
            or any(bool_word in sensor_name for bool_word in ["active", "alarm", "status"])
        ):
            detected.update(
                {
                    "device_class": None,
                    "unit": None,
                    "state_class": None,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.debug(f"Dynamic detection: {sensor_name} → BOOLEAN (UnitType: {unit_type})")

        # Generic numeric fallback
        elif not self._is_boolean and not self._is_string:
            # Use the raw unit presentation if available
            unit = self._sensor_unit if self._sensor_unit else None
            detected.update(
                {
                    "device_class": None,
                    "unit": unit,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "name": (clear_text_name.title() if clear_text_name else sensor_name.title()),
                }
            )
            _LOGGER.info(
                f"Dynamic detection: {sensor_name} → GENERIC NUMERIC "
                f"(UnitType: {unit_type}, Unit: {unit})"
            )

        # Log when we couldn't detect anything useful
        if not detected:
            _LOGGER.warning(
                f"Dynamic detection failed for sensor {sensor_name} "
                f"(UnitType: {unit_type}, UnitPresentation: {unit_presentation})"
            )

        return detected

    def _set_sensor_attributes(self):
        """Set device class, state class, and unit of measurement based on sensor type."""  # noqa: E501
        # Handle organization sensors specially
        if self.is_organization:
            if self.sensor_name == "device_count":
                # Device count sensor should be trackable as a measurement
                self._attr_device_class = None
                self._attr_state_class = SensorStateClass.MEASUREMENT
                self._attr_native_unit_of_measurement = "devices"
                self._attr_icon = "mdi:counter"
            else:
                # Other organization sensors have no device class, units, or detection
                self._attr_device_class = None
                self._attr_state_class = None
                self._attr_native_unit_of_measurement = None
            return

        # Set icon for boolean alarm sensors
        if self._is_boolean and self.sensor_name == "alarmActive":
            if self.value_data.get("Value", "").lower() == "true":
                self._attr_icon = "mdi:alert-circle"
            else:
                self._attr_icon = "mdi:alert-circle-outline"

        # Set icon for string alarm text
        if self._is_string and self.sensor_name == "alarmInClearText":
            self._attr_icon = "mdi:alert-box"

        # For boolean and string values, no need for device class or units
        if self._is_boolean or self._is_string:
            self._attr_device_class = None
            self._attr_state_class = None
            self._attr_native_unit_of_measurement = None
            return

        # For numeric values, try to determine device class and units
        sensor_info = SENSOR_MAP.get(self.sensor_name, {})

        # If not found in hardcoded map, try dynamic detection
        if not sensor_info:
            sensor_info = self._detect_sensor_attributes_dynamically()
            if sensor_info:
                _LOGGER.info(f"Used dynamic detection for unknown sensor: {self.sensor_name}")

        # Set device class if available in mapping
        self._attr_device_class = sensor_info.get("device_class")

        # Set state class if available
        self._attr_state_class = sensor_info.get("state_class")

        # Set unit of measurement
        if "unit" in sensor_info:
            self._attr_native_unit_of_measurement = sensor_info["unit"]
        else:
            self._attr_native_unit_of_measurement = self._sensor_unit

    def _get_organization_sensor_value(self):
        """Get the value for organization sensors."""
        if self.sensor_name == "device_count":
            devices = self.coordinator.data.get("devices", [])
            return len(devices)
        elif self.sensor_name == "organization_count":
            organizations_data = self.coordinator.data.get("organizations", [])
            return len(organizations_data)
        elif self.sensor_name == "child_organizations":
            return self._get_child_organizations_count()
        elif self.sensor_name == "parent_organization":
            return self._get_parent_organization_name()
        elif self.sensor_name == "user_count":
            return self._get_user_count()
        elif self.sensor_name == "member_count":
            return self._get_member_count()
        elif self.sensor_name == "is_parent_organization":
            return self._get_child_organizations_count() > 0
        return None

    def _get_child_organizations_count(self):
        """Get the count of child organizations."""
        organizations_data = self.coordinator.data.get("organizations", [])
        if self.api.organization_id and organizations_data:
            child_orgs_count = len(
                [
                    org
                    for org in organizations_data
                    if org.get("ParentId") == self.api.organization_id
                ]
            )
            return child_orgs_count
        return 0

    def _get_parent_organization_name(self):
        """Get the parent organization name."""
        organizations_data = self.coordinator.data.get("organizations", [])
        if self.api.organization_id and organizations_data:
            current_org = next(
                (org for org in organizations_data if org["Id"] == self.api.organization_id),
                None,
            )
            if current_org and current_org.get("ParentId", 0) != 0:
                parent_org = next(
                    (org for org in organizations_data if org["Id"] == current_org["ParentId"]),
                    None,
                )
                if parent_org:
                    return parent_org["Name"]
        return "None"

    def _get_user_count(self):
        """Get the user count for the current organization."""
        organizations_data = self.coordinator.data.get("organizations", [])
        if self.api.organization_id and organizations_data:
            current_org = next(
                (org for org in organizations_data if org["Id"] == self.api.organization_id),
                None,
            )
            if current_org:
                user_count = current_org.get("UserCount", current_org.get("Users", 0))
                if isinstance(current_org.get("UserList"), list):
                    user_count = len(current_org["UserList"])
                return user_count
        return 0

    def _get_member_count(self):
        """Get the member count for the current organization."""
        organizations_data = self.coordinator.data.get("organizations", [])
        if self.api.organization_id and organizations_data:
            current_org = next(
                (org for org in organizations_data if org["Id"] == self.api.organization_id),
                None,
            )
            if current_org:
                member_count = current_org.get("MemberCount", current_org.get("Members", 0))
                if isinstance(current_org.get("MemberList"), list):
                    member_count = len(current_org["MemberList"])
                return member_count
        return 0

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Get the latest data from the coordinator
        if not self.coordinator.data or "device_data" not in self.coordinator.data:
            return None

        # Handle organization device sensor
        if self.is_organization:
            return self._get_organization_sensor_value()

        # Determine which data source to use based on sensor type
        if self.is_raw_data:
            # For RawData sensors, look in the rawdata_{device_id} key
            data_key = f"rawdata_{self.device_id}"
        else:
            # For standard sensors, use device_id directly
            data_key = self.device_id

        device_data = self.coordinator.data["device_data"].get(data_key)
        if not device_data:
            # Try string version of data_key as fallback
            device_data = self.coordinator.data["device_data"].get(str(data_key))

        if not device_data or "Data" not in device_data or "Values" not in device_data["Data"]:
            return None

        # Find our specific sensor value in the latest data
        sensor_name = self.sensor_name
        for value in device_data["Data"]["Values"]:
            if value.get("Name") == sensor_name:
                raw_value = value.get("Value", "")

                # Update icon if this is an alarm sensor
                if self._is_boolean and self.sensor_name == "alarmActive":
                    is_active = (
                        raw_value.lower() == "true"
                        if isinstance(raw_value, str)
                        else bool(raw_value)
                    )
                    self._attr_icon = (
                        "mdi:alert-circle" if is_active else "mdi:alert-circle-outline"
                    )

                # Use the _parse_value method to handle different value types
                return self._parse_value(raw_value)

        # If we didn't find our sensor, return None
        return None

    @property
    def device_info(self):
        """Return device info."""
        # Determine suggested area based on device type
        suggested_area = None
        if self.device_type == "PowerMeter":
            suggested_area = "Energy"
        elif self.device_type == "WaterMeter":
            suggested_area = "Utility"
        elif self.device_type == "RoomSensor":
            suggested_area = "Climate"
        elif self.device_type in ["HeatPump", "CoolingUnit"]:
            suggested_area = "HVAC"

        # Handle organization device differently
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
            suggested_area=suggested_area,
        )

    def _is_organization_sensor_available(self):
        """Check if organization sensor is available."""
        if self.sensor_name == "device_count":
            return "devices" in self.coordinator.data
        return True

    def _get_device_data_key(self):
        """Get the data key for device data lookup."""
        if self.is_raw_data:
            return f"rawdata_{self.device_id}"
        return self.device_id

    def _find_device_data(self, data_key):
        """Find device data using the given key."""
        device_data = self.coordinator.data["device_data"].get(data_key)
        if not device_data:
            # Try string version of data_key as fallback
            device_data = self.coordinator.data["device_data"].get(str(data_key))
        return device_data

    def _has_sensor_value(self, device_data):
        """Check if the specific sensor value exists in device data."""
        if "Data" not in device_data or "Values" not in device_data["Data"]:
            return False

        for value in device_data["Data"]["Values"]:
            if value.get("Name") == self.sensor_name:
                return True
        return False

    @property
    def available(self):
        """Return if entity is available."""
        # Check if coordinator has data
        if not self.coordinator.data:
            return False

        # Handle organization sensors separately
        if self.is_organization:
            return self._is_organization_sensor_available()

        # For regular sensors, check device_data
        if "device_data" not in self.coordinator.data:
            return False

        # Get device data and check if sensor value exists
        data_key = self._get_device_data_key()
        device_data = self._find_device_data(data_key)

        if not device_data:
            return False

        return self._has_sensor_value(device_data)
