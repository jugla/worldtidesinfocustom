"""Define a config flow manager for WorldTidesInfoCustom."""

import voluptuous as vol

from homeassistant.helpers import  config_validation as cv
from homeassistant import config_entries

from homeassistant.core import callback

from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)

from .const import (
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DOMAIN,
)

from . import async_get_config_id

CONF_INTEGRATION_TYPE = "integration_type"

INTEGRATION_TYPE_STD = "standard_definition"
INTEGRATION_TYPE_EXPERT = "expert_definition"

BASIC_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
    }
)



INTEGRATION_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required("type"): vol.In(
            [
                INTEGRATION_TYPE_STD,
                INTEGRATION_TYPE_EXPERT,
            ]
        )
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class WorldTidesInfoCustomFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an WorldTidesInfoCustom config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._config_id = None

    def config_standard_schema(self):
        """Return the data schema for the cloud API."""
        return BASIC_DATA_SCHEMA.extend(
            {
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
            }
        )

    def config_expert_schema(self):
        """Return the data schema for the cloud API."""
        return BASIC_DATA_SCHEMA.extend(
            {
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
                vol.Optional(
                    CONF_VERTICAL_REF, default=DEFAULT_VERTICAL_REF
                ): cv.string,
                vol.Optional(
                    CONF_STATION_DISTANCE, default=DEFAULT_STATION_DISTANCE
                ): cv.positive_int,
                vol.Optional(
                    CONF_PLOT_COLOR, default=DEFAULT_PLOT_COLOR
                ): cv.string,
                vol.Optional(
                    CONF_PLOT_BACKGROUND, default=DEFAULT_PLOT_BACKGROUND
                ): cv.string,
                vol.Optional(
                    CONF_UNIT, default=DEFAULT_CONF_UNIT
                ): cv.string,
            }
        )

    async def _async_finish_config_definition(self, user_input, integration_type):
        """Validate a Cloud API key."""

        existing_entry = await self.async_set_unique_id(self._config_id)
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=user_input)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(
            title=f"World Tides Info Custom Cloud API ({self._config_id})",
            data={**user_input, CONF_INTEGRATION_TYPE: integration_type},
        )

    async def _async_init_config_definition(self, user_input, integration_type):
        """Handle the initialization of the integration via the cloud API."""
        self._config_id = async_get_config_id(user_input)
        await self._async_set_unique_id(self._config_id)
        self._abort_if_unique_id_configured()
        return await self._async_finish_config_definition(user_input, integration_type)


    async def _async_set_unique_id(self, unique_id):
        """Set the unique ID of the config flow and abort if it already exists."""
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return WorldTidesInfoCustomOptionsFlowHandler(config_entry)


    async def async_step_config_def_std(self, user_input=None):
        """Handle the initialization of the cloud API based on latitude/longitude."""
        if not user_input:
            new_schema = self.config_standard_schema()
            return self.async_show_form(
                step_id="config_def_std", data_schema=new_schema
            )

        return await self._async_init_config_definition(
            user_input, INTEGRATION_TYPE_STD
        )

    async def async_step_config_def_expert(self, user_input=None):
        """Handle the initialization of the cloud API based on lat/long/tuning parameter."""
        if not user_input:
            new_schema = self.config_expert_schema()
            return self.async_show_form(
                step_id="config_def_expert", data_schema=new_schema
            )

        return await self._async_init_config_definition(
            user_input, INTEGRATION_TYPE_EXPERT
        )

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        if not user_input:
            return self.async_show_form(
                step_id="user", data_schema=INTEGRATION_TYPE_SCHEMA
            )

        if user_input["type"] == INTEGRATION_TYPE_STD:
            return await self.async_step_config_def_std()
        elif user_input["type"] == INTEGRATION_TYPE_EXPERT:
            return await self.async_step_config_def_expert()
        #shall not occur
        else:
            return await self.async_step_config_def_expert()



class WorldTidesInfoCustomOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an WorldTidesInfoCustom options flow."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SHOW_ON_MAP,
                        default=self.config_entry.options.get(CONF_SHOW_ON_MAP),
                    ): bool
                }
            ),
        )

