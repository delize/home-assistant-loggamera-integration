"""Config flow for Loggamera integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback  # noqa: F401
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import LoggameraAPI, LoggameraAPIError
from .const import (
    API_ENDPOINT_GENERIC_DEVICE,
    API_ENDPOINT_RAW_DATA,
    CONF_API_KEY,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_ORGANIZATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

FALLBACK_ENDPOINTS = (API_ENDPOINT_RAW_DATA, API_ENDPOINT_GENERIC_DEVICE)
# Types with their own endpoint; others (HeatMeter, ChargingStation) are read via RawData
DEDICATED_ENDPOINT_TYPES = {"HeatPump", "PowerMeter", "RoomSensor", "WaterMeter", "CoolingUnit"}


class LoggameraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Loggamera."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LoggameraOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_DEVICE_ID):
                return await self._async_create_device_entry(user_input)

            try:
                # Validate the API key by connecting to the API
                api = LoggameraAPI(user_input[CONF_API_KEY])

                # Try to fetch organizations
                org_response = await self.hass.async_add_executor_job(api.get_organizations)

                # Check if organizations are returned
                if (
                    "Data" in org_response
                    and "Organizations" in org_response["Data"]
                    and org_response["Data"]["Organizations"]
                ):
                    # Get the first organization
                    organization = org_response["Data"]["Organizations"][0]
                    organization_id = organization["Id"]
                    organization_name = organization["Name"]

                    _LOGGER.info(f"Found organization ID: {organization_id}")

                    # Create a new config entry
                    return self.async_create_entry(
                        title=organization_name,
                        data={
                            CONF_API_KEY: user_input[CONF_API_KEY],
                            CONF_ORGANIZATION_ID: organization_id,
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )
                else:
                    errors["base"] = "no_organizations"
            except LoggameraAPIError as err:
                _LOGGER.error(f"Failed to connect to Loggamera API: {err}")
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception(f"Unexpected error: {err}")
                errors["base"] = "unknown"

        return self._show_form(errors, user_input)

    async def _async_create_device_entry(self, user_input: Dict[str, Any]):
        """Validate a device-scoped API key by reading the device directly."""
        # Organizations/Devices are not available to device-scoped keys
        device_id = user_input[CONF_DEVICE_ID]
        device_type = user_input.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
        await self.async_set_unique_id(f"device_{device_id}")
        self._abort_if_unique_id_configured()

        errors: Dict[str, str] = {}
        try:
            api = LoggameraAPI(user_input[CONF_API_KEY])
            data = await self.hass.async_add_executor_job(
                api.get_device_data, device_id, device_type
            )
        except LoggameraAPIError as err:
            _LOGGER.error(f"Failed to read device {device_id}: {err}")
            errors["base"] = "cannot_connect"
        except Exception as err:
            _LOGGER.exception(f"Unexpected error: {err}")
            errors["base"] = "unknown"
        else:
            # A wrong type still "works" via the RawData/GenericDevice fallback
            used = data.get("_endpoint_used")
            if device_type in DEDICATED_ENDPOINT_TYPES and used in FALLBACK_ENDPOINTS:
                errors[CONF_DEVICE_TYPE] = "wrong_device_type"
        if errors:
            return self._show_form(errors, user_input)

        return self.async_create_entry(
            title=f"Loggamera {device_type} {device_id}",
            data={
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_DEVICE_ID: device_id,
                CONF_DEVICE_TYPE: device_type,
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            },
        )

    def _show_form(self, errors: Dict[str, str], user_input: Optional[Dict[str, Any]] = None):
        """Show the user form, keeping previously entered values."""
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_DEVICE_ID): vol.All(int, vol.Range(min=1)),
                vol.Optional(CONF_DEVICE_TYPE, default=DEFAULT_DEVICE_TYPE): vol.In(DEVICE_TYPES),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=60,
                        max=3600,
                        step=60,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="seconds",
                    )
                ),
            }
        )
        if user_input:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class LoggameraOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=60,
                            max=3600,
                            step=60,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="seconds",
                        )
                    ),
                }
            ),
        )
