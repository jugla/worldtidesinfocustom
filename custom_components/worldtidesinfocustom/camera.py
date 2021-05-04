"""Camera worldtides.info."""
# Python library
import logging

_LOGGER = logging.getLogger(__name__)

import os
import time
import os
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv

# PyPy Library
import requests
import voluptuous as vol

# HA library
from homeassistant.components.camera import PLATFORM_SCHEMA, Camera
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_SHOW_ON_MAP,
)
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

# Component Library
from . import give_persistent_filename
from .const import (
    ATTRIBUTION,
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    DATA_COORDINATOR,
    DEBUG_FLAG,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DOMAIN,
    HA_CONF_UNIT,
    HALF_TIDE_SLACK_DURATION,
    IMPERIAL_CONF_UNIT,
    METRIC_CONF_UNIT,
    SCAN_INTERVAL_SECONDS,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
)

# Sensor HA parameter
SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)
ATTR_GENERATED_AT = "generated_at"
GET_IMAGE_TIMEOUT = 10


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_camera(
    hass,
    name,
):
    """setup camera"""

    curve_picture = TidesCurvePicture(
        hass,
        name,
    )

    return [curve_picture]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""

    # Get data from configuration.yaml
    name = config.get(CONF_NAME)

    # what is the unit used
    tides_cameras = setup_camera(
        hass,
        name,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    for camera in tides_cameras:
        camera.update()

    add_entities(tides_cameras)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up WorldTidesInfo sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][DATA_COORDINATOR][config_entry.entry_id]

    config = config_entry.data

    # Get data from config flow
    name = config.get(CONF_NAME)

    tides_cameras = setup_camera(
        hass,
        name,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    for camera in tides_cameras:
        await camera.async_update()

    async_add_entities(tides_cameras)


class TidesCurvePicture(Camera):
    """Curve Picture."""

    def __init__(
        self,
        hass,
        name,
    ):
        """Initialize Curve Picture."""
        super().__init__()
        self._hass = hass
        # Parameters from configuration.yaml
        self._name = name

        # DATA
        self._generated_at = None
        self._last_requested_date = None
        self._image = None

        self._image_filename = (give_persistent_filename(hass, name)).get(
            "curve_filename"
        )

    def no_data(self):
        return self._image == None

    def camera_image(self):
        """Return image response."""
        self.update()
        return self._image

    def update(self):
        """Read the contents of the file."""
        current_time = time.time()
        read_ok = False
        read_image = None
        _LOGGER.debug("Sync Fetch new picture image from %s", self._name)
        """Return image response."""
        try:
            with open(self._image_filename, "rb") as file:
                read_image = file.read()
            read_ok = True
        except FileNotFoundError:
            _LOGGER.warning(
                "Could not read camera %s image from file: %s",
                self._name,
                self._image_filename,
            )
        if read_ok:
            self._image = read_image
            self._last_requested_date = current_time
            self._generated_at = time.ctime(os.path.getmtime(self._image_filename))

    async def async_update(self):
        """Fetch new state data for the camera."""
        _LOGGER.debug("Async Update Tides sensor %s", self._name)
        ##Watch Out : only method name is given to function i.e. without ()
        await self._hass.async_add_executor_job(self.update)

    @property
    def name(self):
        """Return the name."""
        return self._name + "_curve_picture"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}

        current_time = time.time()

        if self.no_data():
            return attr

        if self._generated_at is not None:
            attr[ATTR_GENERATED_AT] = self._generated_at
        if self._last_requested_date is not None:
            attr["last_requested_date"] = time.strftime(
                "%H:%M:%S %d/%m/%y", time.localtime(self._last_requested_date)
            )
        return attr
