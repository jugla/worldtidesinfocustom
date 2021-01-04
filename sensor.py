"""Support for the worldtides.info API v2."""
import base64
from datetime import timedelta
from datetime import datetime
import logging
import time

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by WorldTides"

DEFAULT_NAME = "WorldTidesInfoCustom"

SCAN_INTERVAL = timedelta(seconds=900)

DEFAULT_WORLDTIDES_REQUEST_INTERVAL = 43200
CONF_WORLDTIDES_REQUEST_INTERVAL =  "worldtides_request_interval"

DEFAULT_VERTICAL_REF = "LAT"
CONF_VERTICAL_REF = "vertical_ref"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_VERTICAL_REF, default=DEFAULT_VERTICAL_REF): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_WORLDTIDES_REQUEST_INTERVAL, default=DEFAULT_WORLDTIDES_REQUEST_INTERVAL): cv.positive_int, 
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""
    name = config.get(CONF_NAME)

    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)
    key = config.get(CONF_API_KEY)
    vertical_ref = config.get(CONF_VERTICAL_REF)
    worldides_request_interval = config.get(CONF_WORLDTIDES_REQUEST_INTERVAL)
    www_path = hass.config.path("www") 

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")

    tides = WorldTidesInfoCustomSensor(name, lat, lon, key, vertical_ref, worldides_request_interval, www_path)
    tides.update()
    if tides.data.get("error") == "No location found":
        _LOGGER.error("Location not available")
        return

    add_entities([tides])


class WorldTidesInfoCustomSensor(Entity):
    """Representation of a WorldTidesInfo sensor."""

    def __init__(self, name, lat, lon, key, vertical_ref, worldides_request_interval, www_path):
        """Initialize the sensor."""
        self._name = name
        self._lat = lat
        self._lon = lon
        self._key = key
        self._vertical_ref = vertical_ref
        self._worldides_request_interval = worldides_request_interval 
        self.data = None
        self.data_request_time = None
        self.next_midnight = (timedelta(days=1) + (datetime.today()).replace(hour=0,minute=0,second=0,microsecond=0))
        self.credit_used = False
        self.curve_picture_filename = www_path + "/" + self._name + ".png"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}

        current_time = int(time.time())
        next_tide = 0
        for tide_index in range(len(self.data["extremes"])):
            if self.data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index

        next_tide = next_tide + 1

        if "High" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["high_tide_height"] = self.data["extremes"][next_tide]["height"]
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["low_tide_height"] = self.data["extremes"][next_tide + 1]["height"]
        elif "Low" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["high_tide_height"] = self.data["extremes"][next_tide + 1]["height"]
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["low_tide_height"] = self.data["extremes"][next_tide]["height"]
        attr["vertical_reference"] = self.data["responseDatum"]

        current_height = 0
        for height_index in range(len(self.data["heights"])):
            if self.data["heights"][height_index]["dt"] < current_time:
                current_height = height_index
        attr["current_height"] = self.data["heights"][current_height]["height"]
        attr["current_height_utc"] = self.data["heights"][current_height]["date"]


        if self.credit_used:
            attr["CreditCallUsed"] = self.data["callCount"]
        else:
            attr["CreditCallUsed"] = 0
        attr["data_request_time"] = time.strftime("%H:%M:%S %d/%m/%y", time.localtime(self.data_request_time))
#        attr["next midnight"] = self.next_midnight.strftime("%H:%M:%S %d/%m/%y")

        attr["plot"] = self.curve_picture_filename

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        if self.data:
            current_time = int(time.time())
            next_tide = 0
            for tide_index in range(len(self.data["extremes"])):
                if self.data["extremes"][tide_index]["dt"] < current_time:
                    next_tide = tide_index
            next_tide = next_tide + 1
            if "High" in str(self.data["extremes"][next_tide]["type"]):
                tidetime = time.strftime(
                    "%H:%M", time.localtime(self.data["extremes"][next_tide]["dt"])
                )
                return f"High tide at {tidetime}"
            if "Low" in str(self.data["extremes"][next_tide]["type"]):
                tidetime = time.strftime(
                    "%H:%M", time.localtime(self.data["extremes"][next_tide]["dt"])
                )
                return f"Low tide at {tidetime}"
            return None
        return None

    def update(self):
        data_to_require = False
        data_has_been_received = False
        current_time = time.time()
        self.credit_used = False

        if self.data_request_time == None:
            data_to_require = True
        elif (current_time >= (self.data_request_time + self._worldides_request_interval)):
            data_to_require = True
        elif (datetime.fromtimestamp(current_time) >= self.next_midnight):
            data_to_require = True
        else:
            data_to_require = False 

        self.next_midnight = (timedelta(days=1) + (datetime.today()).replace(hour=0,minute=0,second=0,microsecond=0))

        if data_to_require:
            """Get the latest data from WorldTidesInfo API v2."""
            resource = (
                "https://www.worldtides.info/api/v2?extremes&days=2&date=today&heights&plot&step=900"
                "&key={}&lat={}&lon={}&datum={}"
            ).format(self._key, self._lat, self._lon,self._vertical_ref)
            try:
                self.data = requests.get(resource, timeout=10).json()
                data_has_been_received = True
                _LOGGER.debug("Data: %s", self.data)
                _LOGGER.debug("Tide data queried at: %s", int(current_time))
            except ValueError as err:
                _LOGGER.error("Error retrieving data from WorldTidesInfo: %s", err.args)
                self.data = None

            if data_has_been_received:
                self.credit_used = True
                self.data_request_time = current_time

                filename = self.curve_picture_filename
                std_string = "data:image/png;base64,"
                str_to_convert = self.data["plot"][len(std_string) : len(self.data["plot"])]
                imgdata = base64.b64decode(str_to_convert)
                with open(filename, "wb") as filehandler:
                    filehandler.write(imgdata)

        else:
           _LOGGER.debug("Tide data not need to be requeried at: %s", int(current_time))
