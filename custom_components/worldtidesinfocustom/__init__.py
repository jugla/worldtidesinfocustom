"""The worldtidesinfo custom component."""

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_IP_ADDRESS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_SHOW_ON_MAP,
    CONF_STATE,
)

from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)


from .const import (
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    DATA_COORDINATOR,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DOMAIN,
)


PLATFORMS = ["sensor"]

DATA_LISTENER = "listener"

class WorldTidesInfoCoordinator:
    """Define the coordinator."""

    def __init__(self, config_id):
        """Initialize."""
        self._config_id = None

    def get_config_id(self):
        """Return the device state attributes."""
        return self._config_id


@callback
def async_get_config_id(config_dict):
    """Generate a unique ID from a tide config dict."""
    if not config_dict:
        return

    return ", ".join(
        (str(config_dict[CONF_LATITUDE]), str(config_dict[CONF_LONGITUDE]))
    )


async def async_setup(hass, config):
    """Set up the World Tide Custom component."""
    hass.data[DOMAIN] = {DATA_COORDINATOR: {}, DATA_LISTENER: {}}
    return True

@callback
def _standardize_config_entry(hass, config_entry):
    """Ensure that geography config entries have appropriate properties."""
    entry_updates = {}

    #Shall not occur
    if not config_entry.unique_id:
        # If the config entry doesn't already have a unique ID, set one:
        entry_updates["unique_id"] = config_entry.data[CONF_API_KEY]

    #Set every field with default value
    if not config_entry.options:
        # If the config entry doesn't already have any options set, set defaults:
        entry_updates["options"] = {CONF_SHOW_ON_MAP: True}

    entry_updates["data"] = {**config_entry.data}

    if not config_entry.data.get(CONF_VERTICAL_REF):
        entry_updates["data"][CONF_VERTICAL_REF] = DEFAULT_VERTICAL_REF
    if not config_entry.data.get(CONF_STATION_DISTANCE):
        entry_updates["data"][CONF_STATION_DISTANCE] = DEFAULT_STATION_DISTANCE
    if not config_entry.data.get(CONF_PLOT_COLOR):
        entry_updates["data"][CONF_PLOT_COLOR] = DEFAULT_PLOT_COLOR
    if not config_entry.data.get(CONF_PLOT_BACKGROUND):
        entry_updates["data"][CONF_PLOT_BACKGROUND] = DEFAULT_PLOT_BACKGROUND
    if not config_entry.data.get(CONF_UNIT):
        entry_updates["data"][CONF_UNIT] = DEFAULT_CONF_UNIT

    if not entry_updates:
        #Do no thing !
        return

    hass.config_entries.async_update_entry(config_entry, **entry_updates)


async def async_setup_entry(hass, config_entry):
    """Set up AirVisual as config entry."""
    _standardize_config_entry(hass, config_entry)

    #just to initialize (this code will be replace by evolution to have global count)
    coordinator = WorldTidesInfoCoordinator(config_entry.entry_id) 

    # To manage options
    hass.data[DOMAIN][DATA_LISTENER][
            config_entry.entry_id
        ] = config_entry.add_update_listener(async_reload_entry)

    hass.data[DOMAIN][DATA_COORDINATOR][config_entry.entry_id] = coordinator

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload an AirVisual config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][DATA_COORDINATOR].pop(config_entry.entry_id)
        remove_listener = hass.data[DOMAIN][DATA_LISTENER].pop(config_entry.entry_id)
        remove_listener()

    return unload_ok


async def async_reload_entry(hass, config_entry):
    """Handle an options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)



