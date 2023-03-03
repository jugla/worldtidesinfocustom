"""Camera worldtides.info."""
# Python library
import logging

_LOGGER = logging.getLogger(__name__)

import os
import time
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
    CONF_SOURCE,
)
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.unit_system import IMPERIAL_SYSTEM
from pyworldtidesinfo.worldtidesinfo_server import SERVER_API_VERSION

# Component Library
from . import give_persistent_filename
from .const import (
    ATTRIBUTION,
    CAMERA_CURVE_PICTURE_SUFFIX,
    CAMERA_PLOT_PICTURE_SUFFIX,
    CONF_LIVE_LOCATION,
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
    DEVICE_CONF_URL,
    DEVICE_SERVER_SUFFIX,
    DOMAIN,
    HA_CONF_UNIT,
    HALF_TIDE_SLACK_DURATION,
    IMPERIAL_CONF_UNIT,
    METRIC_CONF_UNIT,
    SCAN_INTERVAL_SECONDS,
    SENSOR_NEXT_TIDE_SUFFIX,
    STATIC_CONF,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
)
from .sensor_service import worldtidesinfo_unique_id

# Sensor HA parameter
SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)
ATTR_GENERATED_AT = "generated_at"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
    }
)


def setup_camera(
    hass,
    name,
    lat,
    lon,
    live_position_management,
    source,
):
    """setup camera"""
    unique_id = worldtidesinfo_unique_id(lat, lon, live_position_management, source)
    filename = give_persistent_filename(hass, name)

    curve_picture = TidesCurvePicture(
        hass, name, unique_id, filename.get("curve_filename")
    )

    plot_picture = TidesPlotPicture(
        hass, name, "", unique_id, filename.get("plot_filename")
    )

    long_plot_picture = TidesPlotPicture(
        hass, name, "_long", unique_id, filename.get("plot_long_prediction_filename")
    )

    return [curve_picture, plot_picture, long_plot_picture]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""

    # Get data from configuration.yaml
    name = config.get(CONF_NAME)
    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)

    live_position_management = STATIC_CONF
    source = None

    # what is the unit used
    tides_cameras = setup_camera(
        hass,
        name,
        lat,
        lon,
        live_position_management,
        source,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    # for camera in tides_cameras:
    #    camera.update()

    add_entities(tides_cameras)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up WorldTidesInfo sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][DATA_COORDINATOR][config_entry.entry_id]

    config = config_entry.data

    # Get data from config flow
    name = config.get(CONF_NAME)
    lat = config.get(CONF_LATITUDE)
    lon = config.get(CONF_LONGITUDE)

    live_position_management = config.get(CONF_LIVE_LOCATION)
    source = config.get(CONF_SOURCE)

    tides_cameras = setup_camera(
        hass,
        name,
        lat,
        lon,
        live_position_management,
        source,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    # for camera in tides_cameras:
    #    await camera.async_update()

    async_add_entities(tides_cameras)


class TidesPicture_FromFile(Camera):
    """Curve Picture."""

    def __init__(
        self,
        hass,
        name,
        unique_id,
        image_filename,
    ):
        """Initialize Curve Picture."""
        super().__init__()
        self._hass = hass

        # Parameters from configuration.yaml
        self._name = name
        self._image_filename = image_filename
        self._unique_id = unique_id

        # DATA
        self._generated_at = None
        self._last_requested_date = None
        self._image = None

    @property
    def device_info(self):
        """Device info for WorldTideInfo Server."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._unique_id)},
            manufacturer="WorldTidesInfo",
            sw_version=SERVER_API_VERSION,
            name=self._name + DEVICE_SERVER_SUFFIX,
            model="WorldTidesInfoAPI",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=DEVICE_CONF_URL,
        )

    def no_data(self):
        return self._image is None

    def _async_worldtidesinfo_follower_sensor_state_listener(self, event):
        # retrieve state
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        self.schedule_update_ha_state(force_refresh=True)

    async def async_added_to_hass(self):
        """Handle added to Hass."""
        await super().async_added_to_hass()

        entity_id_main_sensor = None

        # Fetch the name of sensor
        registry = async_get(self.hass)
        entity_id_main_sensor = registry.async_get_entity_id(
            "sensor", DOMAIN, self._unique_id + SENSOR_NEXT_TIDE_SUFFIX
        )
        _LOGGER.debug("Camera: entity main sensor %s", entity_id_main_sensor)

        if entity_id_main_sensor is None:
            entity_id_main_sensor = "sensor." + self._name + SENSOR_NEXT_TIDE_SUFFIX

        async_track_state_change_event(
            self._hass,
            [entity_id_main_sensor],
            self._async_worldtidesinfo_follower_sensor_state_listener,
        )

        _LOGGER.debug("Camera: listen main sensor %s", entity_id_main_sensor)
        # pure async i.e. wait for update of main sensor
        # no need to call self.schedule_update_ha_state
        # be robust to be sure to be update
        self.schedule_update_ha_state(force_refresh=True)

    def _get_image(self):
        """Read the contents of the file."""
        current_time = time.time()
        read_ok = False
        read_image = None
        _LOGGER.debug(
            "Camera: Sync Fetch new picture image from %s", self._image_filename
        )
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

    def camera_image(self, width, height):
        """Return image response."""
        _LOGGER.debug("Camera : Sync Image Tides sensor %s", self._name)
        return self._image

    async def async_camera_image(self, width, height):
        """Fetch new image."""
        _LOGGER.debug("Camera : Async Image Tides sensor %s", self._name)
        return self._image

    def update(self):
        """Read the contents of the file."""
        self._get_image()
        _LOGGER.debug("Camera update :  %s", self._image_filename)

    async def async_update(self):
        """Fetch new state data for the camera."""
        _LOGGER.debug("Camera Async Update %s", self._name)
        ##Watch Out : only method name is given to function i.e. without ()
        await self._hass.async_add_executor_job(self.update)

    # name and unique_id function shall be implemented

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


class TidesCurvePicture(TidesPicture_FromFile):
    """Curve Picture."""

    @property
    def name(self):
        """Return the name."""
        return self._name + CAMERA_CURVE_PICTURE_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + CAMERA_CURVE_PICTURE_SUFFIX


class TidesPlotPicture(TidesPicture_FromFile):
    """Plot Picture."""

    def __init__(
        self,
        hass,
        name,
        suffix_name,
        unique_id,
        image_filename,
    ):
        """Initialize Curve Picture."""
        super().__init__(hass, name, unique_id, image_filename)
        self._suffix_name = suffix_name

    @property
    def name(self):
        """Return the name."""
        return self._name + self._suffix_name + CAMERA_PLOT_PICTURE_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + self._suffix_name + CAMERA_PLOT_PICTURE_SUFFIX
