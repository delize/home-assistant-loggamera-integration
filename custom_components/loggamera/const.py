"""Constants for the Loggamera integration."""

DOMAIN = "loggamera"

# API URLs and endpoints
API_URL = "https://platform.loggamera.se/api/v2"
API_ENDPOINT_ORGANIZATIONS = "Organizations"
API_ENDPOINT_DEVICES = "Devices"
API_ENDPOINT_POWER_METER = "PowerMeter"
API_ENDPOINT_ROOM_SENSOR = "RoomSensor"
API_ENDPOINT_GENERIC_DEVICE = "GenericDevice"
API_ENDPOINT_WATER_METER = "WaterMeter"
API_ENDPOINT_COOLING_UNIT = "CoolingUnit"
API_ENDPOINT_HEAT_PUMP = "HeatPump"
API_ENDPOINT_RAW_DATA = "RawData"
API_ENDPOINT_CAPABILITIES = "Capabilities"
API_ENDPOINT_SCENARIOS = "Scenarios"
API_ENDPOINT_EXECUTE_SCENARIO_ASYNC = "ExecuteScenarioAsync"
API_ENDPOINT_USER_ACCESS = "UserAccess"

# Configuration
CONF_API_KEY = "api_key"
CONF_ORGANIZATION_ID = "organization_id"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_TYPE = "device_type"
DEVICE_TYPES = [
    "HeatPump",
    "PowerMeter",
    "RoomSensor",
    "WaterMeter",
    "CoolingUnit",
    "HeatMeter",
    "ChargingStation",
]
DEFAULT_DEVICE_TYPE = "HeatPump"
CONF_SCAN_INTERVAL = "scan_interval"

# Default 20 minutes (1200 seconds) - optimized for PowerMeter which typically updates every ~30 minutes  # noqa: E501
DEFAULT_SCAN_INTERVAL = 1200

# Attributes
ATTR_DEVICE_TYPE = "device_type"
ATTR_DURATION_MINUTES = "duration_minutes"

# Sensor types for internal use
SENSOR_TEMPERATURE = "temperature"
SENSOR_HUMIDITY = "humidity"
SENSOR_ENERGY = "energy"
SENSOR_POWER = "power"
SENSOR_WATER = "water"
SENSOR_VALUE = "value"

# Platform definitions
PLATFORMS = ["sensor", "binary_sensor", "switch"]
