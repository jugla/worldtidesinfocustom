"""The worldtidesinfo custom component."""

# python library
import asyncio
import os

# HA python
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_SHOW_ON_MAP,
    CONF_SOURCE,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

# internal library
from .const import (
    CONF_DAY_TIDE_PREDICTION,
    CONF_LIVE_LOCATION,
    CONF_MAT_PLOT_TRANS_BCKGROUND,
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    DATA_COORDINATOR,
    DEFAULT_CONF_LIVE_LOCATION,
    DEFAULT_CONF_UNIT,
    DEFAULT_DAY_TIDE_PREDICTION,
    DEFAULT_MAT_PLOT_TRANS_BCKGROUND,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DOMAIN,
    FROM_SENSOR_CONF,
    STATIC_CONF,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
    WWW_PATH,
)

PLATFORMS = ["sensor", "camera", "calendar"]

DATA_LISTENER = "listener"

worldtidesinfo_data_coordinator = {}


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

    if not config_dict.get(CONF_LIVE_LOCATION):
        return ", ".join(
            (str(config_dict[CONF_LATITUDE]), str(config_dict[CONF_LONGITUDE]))
        )

    if config_dict[CONF_LIVE_LOCATION] == STATIC_CONF:
        return ", ".join(
            (str(config_dict[CONF_LATITUDE]), str(config_dict[CONF_LONGITUDE]))
        )

    if config_dict[CONF_LIVE_LOCATION] == FROM_SENSOR_CONF:
        return ", ".join(
            (str(config_dict[CONF_LIVE_LOCATION]), str(config_dict[CONF_SOURCE]))
        )

    return


@callback
def async_get_used_api_key(hass):
    """Go through coordinator to find a used API key."""
    # first time the entry does not exist and so nothing is created
    if hass.data.get(DOMAIN) is None:
        return None

    # look for existing key
    for entry_id, coordinator in hass.data[DOMAIN][DATA_COORDINATOR].items():
        config_entry = hass.config_entries.async_get_entry(entry_id)
        if config_entry.data.get(CONF_API_KEY) is not None:
            return config_entry.data.get(CONF_API_KEY)

    # nothing found
    return None


async def async_setup(hass, config):
    """Set up the World Tide Custom component."""
    # hass.data[DOMAIN] = {DATA_COORDINATOR: {}, DATA_LISTENER: {}}
    return True


@callback
def _standardize_config_entry(hass, config_entry):
    """Ensure that geography config entries have appropriate properties."""
    entry_updates = {}

    # Shall not occur
    if not config_entry.unique_id:
        # If the config entry doesn't already have a unique ID, set one:
        entry_updates["unique_id"] = config_entry.data[CONF_API_KEY]

    # Set every field with default value
    if not config_entry.options:
        # If the config entry doesn't already have any options set, set defaults:
        entry_updates["options"] = {CONF_SHOW_ON_MAP: True}

    entry_updates["data"] = {**config_entry.data}

    if not config_entry.data.get(CONF_VERTICAL_REF):
        entry_updates["data"][CONF_VERTICAL_REF] = DEFAULT_VERTICAL_REF
    if not config_entry.data.get(CONF_STATION_DISTANCE):
        entry_updates["data"][CONF_STATION_DISTANCE] = DEFAULT_STATION_DISTANCE
    if not config_entry.data.get(CONF_DAY_TIDE_PREDICTION):
        entry_updates["data"][CONF_DAY_TIDE_PREDICTION] = DEFAULT_DAY_TIDE_PREDICTION
    if not config_entry.data.get(CONF_PLOT_COLOR):
        entry_updates["data"][CONF_PLOT_COLOR] = DEFAULT_PLOT_COLOR
    if not config_entry.data.get(CONF_PLOT_BACKGROUND):
        entry_updates["data"][CONF_PLOT_BACKGROUND] = DEFAULT_PLOT_BACKGROUND
    if not config_entry.data.get(CONF_UNIT):
        entry_updates["data"][CONF_UNIT] = DEFAULT_CONF_UNIT
    if not config_entry.data.get(CONF_MAT_PLOT_TRANS_BCKGROUND):
        entry_updates["data"][
            CONF_MAT_PLOT_TRANS_BCKGROUND
        ] = DEFAULT_MAT_PLOT_TRANS_BCKGROUND
    if not config_entry.data.get(CONF_LIVE_LOCATION):
        entry_updates["data"][CONF_LIVE_LOCATION] = DEFAULT_CONF_LIVE_LOCATION

    if not entry_updates:
        # Do no thing !
        return

    hass.config_entries.async_update_entry(config_entry, **entry_updates)


async def async_setup_entry(hass, config_entry):
    """Set up WorldTidesInfo as config entry."""
    hass.data.setdefault(DOMAIN, {DATA_COORDINATOR: {}, DATA_LISTENER: {}})

    _standardize_config_entry(hass, config_entry)

    # just to initialize (this code will be replace by evolution to have global count)
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
    """Unload an WorldTidesInfo config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        # remove global cooordinator
        worldtidesinfo_data_coordinator.pop(config_entry.data[CONF_NAME])

        # remove config flow coordinator
        hass.data[DOMAIN][DATA_COORDINATOR].pop(config_entry.entry_id)
        remove_listener = hass.data[DOMAIN][DATA_LISTENER].pop(config_entry.entry_id)
        remove_listener()

    return unload_ok


async def async_reload_entry(hass, config_entry):
    """Handle an options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


def give_persistent_filename(hass, name):
    """give persistent data filename"""
    curve_filename = hass.config.path(WWW_PATH, name + ".png")
    plot_filename = hass.config.path(WWW_PATH, name + "_plot.png")
    plot_long_prediction_filename = hass.config.path(WWW_PATH, name + "_plot_long.png")

    persistent_data_filename = hass.config.path(
        STORAGE_DIR, WORLD_TIDES_INFO_CUSTOM_DOMAIN + "." + name + ".ser"
    )

    return {
        "curve_filename": curve_filename,
        "plot_filename": plot_filename,
        "plot_long_prediction_filename": plot_long_prediction_filename,
        "persistent_data_filename": persistent_data_filename,
    }


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""

    # remove persistent data
    config = config_entry.data
    name = config.get(CONF_NAME)

    filenames = give_persistent_filename(hass, name)

    ## picture from server
    if os.path.isfile(filenames.get("curve_filename")):
        os.remove(filenames.get("curve_filename"))
    ## picture compute with matplotlib
    if os.path.isfile(filenames.get("plot_filename")):
        os.remove(filenames.get("plot_filename"))
    if os.path.isfile(filenames.get("plot_long_prediction_filename")):
        os.remove(filenames.get("plot_long_prediction_filename"))
    ## persistent data
    if os.path.isfile(filenames.get("persistent_data_filename")):
        os.remove(filenames.get("persistent_data_filename"))
