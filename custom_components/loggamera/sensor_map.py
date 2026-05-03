"""Static metadata for known Loggamera sensors.

Maps sensor names (or RawData numeric IDs) to Home Assistant device class,
state class, unit, and display name. Lookups not found here fall through to
runtime detection in `sensor._detect_sensor_attributes`.
"""

from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)


def _temp(name: str) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }


def _energy_total(name: str) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": name,
    }


def _power(name: str, unit: str = UnitOfPower.WATT) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.POWER,
        "unit": unit,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }


def _current(name: str) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }


def _voltage(name: str) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }


def _water_total(name: str, unit: str = UnitOfVolume.CUBIC_METERS) -> Dict[str, Any]:
    return {
        "device_class": SensorDeviceClass.WATER,
        "unit": unit,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "name": name,
    }


def _percent(device_class: SensorDeviceClass, name: str) -> Dict[str, Any]:
    return {
        "device_class": device_class,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }


def _label(name: str, icon: Optional[str] = None) -> Dict[str, Any]:
    """Boolean / string / opaque-code sensors with no class or unit."""
    entry: Dict[str, Any] = {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "name": name,
    }
    if icon:
        entry["icon"] = icon
    return entry


def _measurement(name: str, unit: Optional[str], icon: Optional[str] = None) -> Dict[str, Any]:
    """Numeric measurement that doesn't map to a HA device class."""
    entry: Dict[str, Any] = {
        "device_class": None,
        "unit": unit,
        "state_class": SensorStateClass.MEASUREMENT,
        "name": name,
    }
    if icon:
        entry["icon"] = icon
    return entry


SENSOR_MAP: Dict[str, Dict[str, Any]] = {
    # PowerMeter standard endpoint
    "ConsumedTotalInkWh": _energy_total("Total Energy Consumption"),
    "PowerInkW": _power("Current Energy Consumption", UnitOfPower.KILO_WATT),
    "alarmActive": _label("Alarm Status", "mdi:alert-circle"),
    "alarmInClearText": _label("Alarm Context", "mdi:alert-box"),
    # Organization sensors (computed in setup, not from API)
    "device_count": _label("Total Device Count", "mdi:counter"),
    "organization_count": _label("Total Organization Count", "mdi:domain"),
    "parent_organization": _label("Parent Organization ID", "mdi:account-supervisor"),
    "child_organizations": _label("Child Organization Count", "mdi:account-group"),
    "user_count": _label("User Count", "mdi:account"),
    "member_count": _label("Member Count", "mdi:account-multiple"),
    "is_parent_organization": _label("Is Parent Organization", "mdi:account-supervisor-circle"),
    # PowerMeter RawData (energy import / interval / power)
    "544352": _energy_total("Total Energy Consumed"),
    "544353": _energy_total("Total Energy Interval"),
    "544399": _power("Power"),
    # PowerMeter RawData per-phase
    "544463": _energy_total("Energy Phase 1"),
    "544464": _energy_total("Energy Phase 2"),
    "544465": _energy_total("Energy Phase 3"),
    "544391": _current("Current Phase 1"),
    "544393": _current("Current Phase 2"),
    "544394": _current("Current Phase 3"),
    "544395": _voltage("Voltage Phase 1"),
    "544396": _voltage("Voltage Phase 2"),
    "544397": _voltage("Voltage Phase 3"),
    # PowerMeter RawData export / per-phase power
    "549990": _energy_total("Total Energy Generated"),
    "550224": _energy_total("Energy Generated Interval"),
    "550205": _power("Power Phase 1"),
    "550206": _power("Power Phase 2"),
    "550207": _power("Power Phase 3"),
    # Additional PowerMeter RawData
    "543817": _energy_total("Energy"),
    "543801": _power("Power Average"),
    "543802": _voltage("Voltage"),
    "543803": _current("Current Phase 1"),
    "543804": _current("Current Phase 2"),
    "543805": _current("Current Phase 3"),
    "543842": _power("Power Peak"),
    "543821": _energy_total("Consumption Interval"),
    # HeatPump RawData temperature sensors
    "541388": _temp("Hot Water Temperature"),
    "541125": _temp("Set Room Temperature"),
    "541119": _temp("Outdoor Temperature"),
    "541655": _temp("Hot Gas Temperature"),
    "541104": _temp("Heat Carrier 1"),
    "541646": _temp("Heat Carrier Outgoing"),
    "541647": _temp("Heat Carrier Incoming"),
    "541651": _temp("Brine Incoming"),
    "541648": _temp("Brine Outgoing"),
    # HeatPump endpoint named sensors
    "heatCarrierInTempInDeg": _temp("Heat Carrier Inlet Temperature"),
    "heatCarrierOutTempInDeg": _temp("Heat Carrier Outlet Temperature"),
    "brineInTempInDeg": _temp("Brine Inlet Temperature"),
    "brineOutTempInDeg": _temp("Brine Outlet Temperature"),
    "reducedModeActive": _label("Reduced Mode", "mdi:power-sleep"),
    "pumpActivity": _label("Pump Activity", "mdi:pump"),
    "filterAlarmIsActive": _label("Filter Alarm", "mdi:air-filter"),
    # HeatMeter RawData sensors
    "544310": _energy_total("Total Energy"),
    "544311": _measurement("Total Volume", UnitOfVolume.CUBIC_METERS),
    "544320": _measurement("Flow Rate", "m³/h"),
    "544321": _temp("Flow Temperature"),
    "544322": _temp("Return Temperature"),
    "544323": _temp("Temperature Difference"),
    "544324": _measurement("Error Code", None, "mdi:alert-circle-outline"),
    # ChargingStation voltage (corrects API typo "Voltate")
    "544426": _voltage("Voltage Phase 1"),
    "544427": _voltage("Voltage Phase 2"),
    "544428": _voltage("Voltage Phase 3"),
    # ChargingStation RawData
    "544424": _energy_total("Total Consumption"),
    "544434": _energy_total("Session Consumption"),
    "544429": _current("Current Phase 1"),
    "544430": _current("Current Phase 2"),
    "544431": _current("Current Phase 3"),
    "544425": _energy_total("Consumption Interval"),
    "544432": _label("Charging State", "mdi:ev-station"),
    "544443": _label("Load Balanced", "mdi:scale-balance"),
    "544441": _label("Firmware Version", "mdi:chip"),
    "544442": _label("Hardware Version", "mdi:chip"),
    "544436": _label("Status Code A", "mdi:information"),
    "544437": _label("Status Code B", "mdi:information"),
    # RoomSensor RawData
    "543700": _temp("Temperature"),
    "543701": _percent(SensorDeviceClass.HUMIDITY, "Humidity"),
    "543709": _percent(SensorDeviceClass.BATTERY, "Battery"),
    "543836": {
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "unit": "dBm",
        "state_class": SensorStateClass.MEASUREMENT,
        "name": "Signal Strength RSSI",
        "icon": "mdi:wifi",
    },
    "543838": _measurement("Spreading Factor", None, "mdi:radio-tower"),
    "543837": _measurement("Signal to Noise Ratio", "dB", "mdi:signal"),
    # WaterMeter RawData
    "422568": _measurement("Meter Value", UnitOfVolume.CUBIC_METERS),  # not classed as WATER
    "542175": _water_total("Consumption Since Midnight", UnitOfVolume.LITERS),
    "542176": _measurement("Current Flow", "L/min"),
    "544316": _water_total("Consumption Interval", UnitOfVolume.LITERS),
    # Generic alarm sensors available on all devices
    "alarmCodeNumber": _label("Alarm Code Number", "mdi:numeric"),
    "alarmClassification": _label("Alarm Classification", "mdi:alert-decagram"),
    # Standard endpoint named sensors (TEMP_MAPPINGS / WATER_MAPPINGS in the original)
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
    "ConsumedTotalInm3": _water_total("Total Water Consumption"),
    "ConsumedTotalInM3": _water_total("Total Water Consumption"),  # capitalization variant
    "ConsumedSinceMidnightInLiters": _water_total("Water Used Since Midnight", UnitOfVolume.LITERS),
}
