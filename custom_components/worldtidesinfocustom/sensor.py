"""Support for the worldtides.info API v2."""
import base64
import logging
import os
import pickle
import time
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
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
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

from .const import (
    ATTRIBUTION,
    CONF_STATION_DISTANCE,
    CONF_VERTICAL_REF,
    CONF_WORLDTIDES_REQUEST_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DEFAULT_WORLDTIDES_REQUEST_INTERVAL,
    SCAN_INTERVAL_SECONDS,
)

SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_VERTICAL_REF, default=DEFAULT_VERTICAL_REF): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(
            CONF_WORLDTIDES_REQUEST_INTERVAL,
            default=DEFAULT_WORLDTIDES_REQUEST_INTERVAL,
        ): cv.positive_int,
        vol.Optional(
            CONF_STATION_DISTANCE,
            default=DEFAULT_STATION_DISTANCE,
        ): cv.positive_int,
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
    tide_station_distance = config.get(CONF_STATION_DISTANCE)
    www_path = hass.config.path("www")

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")

    tides = WorldTidesInfoCustomSensor(
        name,
        lat,
        lon,
        key,
        vertical_ref,
        worldides_request_interval,
        tide_station_distance,
        www_path,
    )
    # tides.retrieve_tide_station()
    tides.update()
    if tides.data.get("error") == "No location found":
        _LOGGER.error("Location not available")
        return

    add_entities([tides])


class TidesInfoData:
    """ Class to store  """

    def __init__(
        self,
        filename,
    ):
        """Initialize the data."""
        self._filename = filename
        """parameter"""
        self._name = None
        self._lat = None
        self._lon = None
        self._vertical_ref = None
        self._tide_station_distance = None
        """data from server"""
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.data_datums_offset = None
        self.next_midnight = None

    def filename(self):
        return self._filename

    def store_parameters(self, name, lat, lon, vertical_ref, tide_station_distance):
        self._name = name
        self._lat = lat
        self._lon = lon
        self._vertical_ref = vertical_ref
        self._tide_station_distance = tide_station_distance

    def store_init_info(self, init_data):
        self.init_data = init_data

    def store_init_offset(self, data_datums_offset):
        self.data_datums_offset = data_datums_offset

    def store_data_info(self, data, data_request_time):
        self.data = data
        self.data_request_time = data_request_time

    def store_next_midnight(self, next_midnight):
        self.next_midnight = next_midnight

    def data_usable(self, name, lat, lon, vertical_ref, tide_station_distance):
        if (
            self._name == name
            and self._lat == lat
            and self._lon == lon
            and self._vertical_ref == vertical_ref
            and self._tide_station_distance == tide_station_distance
        ):
            return True
        else:
            return False


class WorldTidesInfoCustomSensor(Entity):
    """Representation of a WorldTidesInfo sensor."""

    def __init__(
        self,
        name,
        lat,
        lon,
        key,
        vertical_ref,
        worldides_request_interval,
        tide_station_distance,
        www_path,
    ):
        """Initialize the sensor."""
        self._name = name
        self._lat = lat
        self._lon = lon
        self._key = key
        self._vertical_ref = vertical_ref
        self._worldides_request_interval = worldides_request_interval
        self._tide_station_distance = tide_station_distance
        self.curve_picture_filename = www_path + "/" + self._name + ".png"
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.next_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.credit_used = 0
        self.data_datums_offset = None
        """ initialize the data to store"""
        self.TidesInfoData_filename = www_path + "/" + self._name + ".ser"
        self.TidesInfoData = TidesInfoData(self.TidesInfoData_filename)
        """parameter"""
        self.TidesInfoData.store_parameters(
            self._name,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
        )
        self.TidesInfoData.store_next_midnight(self.next_midnight)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}

        current_time = int(time.time())

        diff_high_tide_next_low_tide = 0

        next_tide = 0
        for tide_index in range(len(self.data["extremes"])):
            if self.data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index
        """if next_tide=0 perform a check"""
        if self.data["extremes"][next_tide]["dt"] < current_time:
            next_tide = next_tide + 1

        if "High" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["high_tide_height"] = self.data["extremes"][next_tide]["height"]
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["low_tide_height"] = self.data["extremes"][next_tide + 1]["height"]
            diff_high_tide_next_low_tide = (
                self.data["extremes"][next_tide]["height"]
                - self.data["extremes"][next_tide + 1]["height"]
            )
        elif "Low" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["high_tide_height"] = self.data["extremes"][next_tide + 1]["height"]
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["low_tide_height"] = self.data["extremes"][next_tide]["height"]
            diff_high_tide_next_low_tide = (
                self.data["extremes"][next_tide + 1]["height"]
                - self.data["extremes"][next_tide + 2]["height"]
            )
        attr["vertical_reference"] = self.data["responseDatum"]
        if "station" in self.data:
            attr["tidal_station_used"] = self.data["station"]
        else:
            attr["tidal_station_used"] = "no reference station used"
        current_height = 0
        for height_index in range(len(self.data["heights"])):
            if self.data["heights"][height_index]["dt"] < current_time:
                current_height = height_index
        attr["current_height"] = self.data["heights"][current_height]["height"]
        attr["current_height_utc"] = self.data["heights"][current_height]["date"]

        attr["CreditCallUsed"] = self.credit_used
        attr["data_request_time"] = time.strftime(
            "%H:%M:%S %d/%m/%y", time.localtime(self.data_request_time)
        )
        #        attr["next midnight"] = self.next_midnight.strftime("%H:%M:%S %d/%m/%y")

        attr["plot"] = self.curve_picture_filename

        attr["CreditCallUsedForInit"] = self.init_data["callCount"]

        attr["station_around_nb"] = len(self.init_data["stations"])
        attr["station_distance"] = self._tide_station_distance
        if len(self.init_data["stations"]) > 0:
            attr["station_around_name"] = ""
            for name_index in range(len(self.init_data["stations"])):
                attr["station_around_name"] = (
                    attr["station_around_name"]
                    + "; "
                    + self.init_data["stations"][name_index]["name"]
                )
            attr["station_around_time_zone"] = self.init_data["stations"][0]["timezone"]
        else:
            attr["station_around_name"] = "None"
            attr["station_around_time_zone"] = "None"

        # attr["datums"] = self.data_datums_offset

        MHW_index = 0
        MLW_index = 0
        for ref_index in range(len(self.data_datums_offset)):
            if self.data_datums_offset[ref_index]["name"] == "MHWS":
                MHW_index = ref_index
            if self.data_datums_offset[ref_index]["name"] == "MLWS":
                MLW_index = ref_index

        attr["Coeff"] = int(
            (
                diff_high_tide_next_low_tide
                / (
                    self.data_datums_offset[MHW_index]["height"]
                    - self.data_datums_offset[MLW_index]["height"]
                )
            )
            * 100
        )

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
            if self.data["extremes"][next_tide]["dt"] < current_time:
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
        self.credit_used = 0
        current_time = time.time()

        """init """
        if self.init_data == None:
            previous_data_fetched = False
            TidesInfoData_read = None
            """read previous received data"""
            try:
                data_to_read = open(self.TidesInfoData_filename, "rb")
                unpickler = pickle.Unpickler(data_to_read)
                TidesInfoData_read = unpickler.load()
                data_to_read.close()
                previous_data_fetched = True
            except:
                _LOGGER.debug("Init to be performed at: %s", int(current_time))
            if previous_data_fetched:
                if self.TidesInfoData.data_usable(
                    TidesInfoData_read._name,
                    TidesInfoData_read._lat,
                    TidesInfoData_read._lon,
                    TidesInfoData_read._vertical_ref,
                    TidesInfoData_read._tide_station_distance,
                ):
                    """fetch data"""
                    self.init_data = TidesInfoData_read.init_data
                    self.data_datums_offset = TidesInfoData_read.data_datums_offset
                    self.data = TidesInfoData_read.data
                    self.data_request_time = TidesInfoData_read.data_request_time
                    self.next_midnight = TidesInfoData_read.next_midnight
                    """set data to store"""
                    self.TidesInfoData.store_init_info(self.init_data)
                    self.TidesInfoData.store_init_offset(self.data_datums_offset)
                    self.TidesInfoData.store_data_info(
                        self.data, self.data_request_time
                    )
                    self.TidesInfoData.store_next_midnight(self.next_midnight)
                else:
                    """retrieve station"""
                    self.retrieve_tide_station()
            else:
                """retrieve station"""
                self.retrieve_tide_station()

        """ normal process """
        if self.data_request_time == None:
            data_to_require = True
        elif current_time >= (
            self.data_request_time + self._worldides_request_interval
        ):
            data_to_require = True
        elif datetime.fromtimestamp(current_time) >= self.next_midnight:
            data_to_require = True
        else:
            data_to_require = False

        self.next_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        """store next midnight"""
        self.TidesInfoData.store_next_midnight(self.next_midnight)

        if data_to_require:
            self.retrieve_height_station()
        else:
            _LOGGER.debug(
                "Tide data not need to be requeried at: %s", int(current_time)
            )

    def retrieve_tide_station(self):
        current_time = time.time()
        data_has_been_received = False

        """Get the latest data from WorldTidesInfo API v2."""
        resource = (
            "https://www.worldtides.info/api/v2?stations"
            "&key={}&lat={}&lon={}&stationDistance={}"
        ).format(self._key, self._lat, self._lon, self._tide_station_distance)
        try:
            self.init_data = requests.get(resource, timeout=10).json()
            data_has_been_received = True
            _LOGGER.debug("Init Data: %s", self.data)
            _LOGGER.debug("Init data queried at: %s", int(current_time))
        except ValueError as err:
            _LOGGER.error("Error retrieving data from WorldTidesInfo: %s", err.args)
            self.init_data = None

        if data_has_been_received:
            self.credit_used = self.credit_used + self.init_data["callCount"]
            self.TidesInfoData.store_init_info(self.init_data)

    def retrieve_height_station(self):
        """Get the latest data from WorldTidesInfo API v2."""
        data_has_been_received = False
        current_time = time.time()
        datums_string = ""
        if self.data_datums_offset == None:
            datums_string = "&datums"

        """3 days --> to manage one day beyond midnight and one before midnight"""
        resource = (
            "https://www.worldtides.info/api/v2?extremes&days=3&date=today&heights&plot&timemode=24&step=900"
            "&key={}&lat={}&lon={}&datum={}&stationDistance={}{}"
        ).format(
            self._key,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
            datums_string,
        )
        try:
            self.data = requests.get(resource, timeout=10).json()
            data_has_been_received = True
            _LOGGER.debug("Data: %s", self.data)
            _LOGGER.debug("Tide data queried at: %s", int(current_time))
        except ValueError as err:
            _LOGGER.error("Error retrieving data from WorldTidesInfo: %s", err.args)
            self.data = None

        if data_has_been_received:
            self.credit_used = self.credit_used + self.data["callCount"]
            self.data_request_time = current_time
            self.TidesInfoData.store_data_info(self.data, self.data_request_time)
            if "datums" in self.data:
                self.data_datums_offset = self.data["datums"]
                self.TidesInfoData.store_init_offset(self.data_datums_offset)
            if "plot" in self.data:
                filename = self.curve_picture_filename
                std_string = "data:image/png;base64,"
                str_to_convert = self.data["plot"][
                    len(std_string) : len(self.data["plot"])
                ]
                imgdata = base64.b64decode(str_to_convert)
                with open(filename, "wb") as filehandler:
                    filehandler.write(imgdata)
            else:
                if os.path.isfile(self.curve_picture_filename):
                    os.remove(self.curve_picture_filename)
            """store received data"""
            data_to_store = open(self.TidesInfoData_filename, "wb")
            pickler = pickle.Pickler(data_to_store, pickle.HIGHEST_PROTOCOL)
            pickler.dump(self.TidesInfoData)
            data_to_store.close()
