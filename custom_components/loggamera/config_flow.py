"""Config flow for Loggamera integration."""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import LoggameraAPI, LoggameraAPIError
from .const import (
    CONF_API_KEY,
    CONF_ORGANIZATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


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

        # Show the form for user input
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
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
            ),
            errors=errors,
        )


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
