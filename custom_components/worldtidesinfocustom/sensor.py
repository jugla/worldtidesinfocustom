"""Support for the worldtides.info API v2."""
import base64
import hashlib
import hmac
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
from homeassistant.helpers.storage import STORAGE_DIR

_LOGGER = logging.getLogger(__name__)

from .const import (
    ATTRIBUTION,
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_VERTICAL_REF,
    CONF_WORLDTIDES_REQUEST_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DEFAULT_WORLDTIDES_REQUEST_INTERVAL,
    FORCE_FETCH_INIT_DATA,
    SCAN_INTERVAL_SECONDS,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
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
        vol.Optional(CONF_PLOT_COLOR, default=DEFAULT_PLOT_COLOR): cv.string,
        vol.Optional(CONF_PLOT_BACKGROUND, default=DEFAULT_PLOT_BACKGROUND): cv.string,
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
    www_path = hass.config.path("www", name + ".png")
    storage_path = hass.config.path(
        STORAGE_DIR, WORLD_TIDES_INFO_CUSTOM_DOMAIN + "." + name + ".ser"
    )
    plot_color = config.get(CONF_PLOT_COLOR)
    plot_background = config.get(CONF_PLOT_BACKGROUND)

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
        storage_path,
        plot_color,
        plot_background,
    )
    # tides.retrieve_tide_station()
    tides.update()
    if tides.data.get("error") == "No location found":
        _LOGGER.error("Location not available")
        return

    add_entities([tides])


class SignedPickle:
    """ Class to save """

    def __init__(self, pickle_data, hmac):
        """Initialize the data."""
        self._pickle_data = pickle_data
        self._hmac = hmac


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
        self._plot_color = None
        self._plot_background = None
        """data from server"""
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.init_data_request_time = None
        self.data_datums_offset = None
        self.next_day_midnight = None
        self.next_month_midnight = None

    def filename(self):
        return self._filename

    def store_parameters(
        self,
        name,
        lat,
        lon,
        vertical_ref,
        tide_station_distance,
        plot_color,
        plot_background,
    ):
        self._name = name
        self._lat = lat
        self._lon = lon
        self._vertical_ref = vertical_ref
        self._tide_station_distance = tide_station_distance
        self._plot_color = plot_color
        self._plot_background = plot_background

    def store_init_info(self, init_data, init_data_request_time):
        self.init_data = init_data
        self.init_data_request_time = init_data_request_time

    def store_init_offset(self, data_datums_offset):
        self.data_datums_offset = data_datums_offset

    def store_data_info(self, data, data_request_time):
        self.data = data
        self.data_request_time = data_request_time

    def store_next_midnight(self, next_day_midnight, next_month_midnight):
        self.next_day_midnight = next_day_midnight
        self.next_month_midnight = next_month_midnight

    def data_usable(
        self,
        name,
        lat,
        lon,
        vertical_ref,
        tide_station_distance,
        plot_color,
        plot_background,
    ):
        if (
            self._name == name
            and self._lat == lat
            and self._lon == lon
            and self._vertical_ref == vertical_ref
            and self._tide_station_distance == tide_station_distance
            and self._plot_color == plot_color
            and self._plot_background == plot_background
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
        storage_path,
        plot_color,
        plot_background,
    ):
        """Initialize the sensor."""
        self._name = name
        self._lat = lat
        self._lon = lon
        self._key = key
        self._vertical_ref = vertical_ref
        self._worldides_request_interval = worldides_request_interval
        self._tide_station_distance = tide_station_distance
        # self.curve_picture_filename = www_path + "/" + self._name + ".png"
        self.curve_picture_filename = www_path
        self._plot_color = plot_color
        self._plot_background = plot_background
        """internal data"""
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.init_data_request_time = None
        self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA) + (
            datetime.today()
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        self.credit_used = 0
        self.data_datums_offset = None
        """ initialize the data to store"""
        # self.TidesInfoData_filename = www_path + "/" + self._name + ".ser"
        self.TidesInfoData_filename = storage_path
        self.TidesInfoData = TidesInfoData(self.TidesInfoData_filename)
        """parameter"""
        self.TidesInfoData.store_parameters(
            self._name,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
            self._plot_color,
            self._plot_background,
        )
        self.TidesInfoData.store_next_midnight(
                    self.next_day_midnight,
                    self.next_month_midnight )

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
        # attr["CreditCallUsedForInit"] = self.init_data["callCount"]

        attr["Data_request_time"] = time.strftime(
            "%H:%M:%S %d/%m/%y", time.localtime(self.data_request_time)
        )
        # attr["Init_data_request_time"] = time.strftime(
        #     "%H:%M:%S %d/%m/%y", time.localtime(self.init_data_request_time)
        # )

        # attr["next day midnight"] = self.next_day_midnight.strftime("%H:%M:%S %d/%m/%y")
        # attr["next month midnight"] = self.next_month_midnight.strftime(
        #     "%H:%M:%S %d/%m/%y"
        # )

        attr["plot"] = self.curve_picture_filename


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
        init_data_to_require = False
        force_init_data_to_require = False
        init_data_fetched = False
        self.credit_used = 0
        current_time = time.time()

        """init """
        if self.init_data == None:
            init_data_to_require = True
        elif datetime.fromtimestamp(current_time) >= self.next_month_midnight:
            init_data_to_require = True
            force_init_data_to_require = True
        else:
            init_data_to_require = False

        if init_data_to_require:
            previous_data_fetched = False
            TidesInfoData_read = None
            """read previous received data"""
            try:
                data_to_read = open(self.TidesInfoData_filename, "rb")
                unpickler = pickle.Unpickler(data_to_read)
                to_load = unpickler.load()
                data_to_read.close()
                previous_data_fetched = True
            except:
                _LOGGER.debug("Init to be performed at: %s", int(current_time))

            previous_data_decode = False
            if previous_data_fetched:
                try:
                    hmac_data = hmac.new(
                        self._key.encode("utf-8"), to_load._pickle_data, hashlib.sha1
                    ).hexdigest()
                    if hmac_data == to_load._hmac:
                        TidesInfoData_read = pickle.loads(to_load._pickle_data)
                        if self.TidesInfoData.data_usable(
                            TidesInfoData_read._name,
                            TidesInfoData_read._lat,
                            TidesInfoData_read._lon,
                            TidesInfoData_read._vertical_ref,
                            TidesInfoData_read._tide_station_distance,
                            TidesInfoData_read._plot_color,
                            TidesInfoData_read._plot_background,
                        ):
                            """fetch data"""
                            self.init_data = TidesInfoData_read.init_data
                            self.data_datums_offset = (
                                TidesInfoData_read.data_datums_offset
                            )
                            self.data = TidesInfoData_read.data
                            self.data_request_time = (
                                TidesInfoData_read.data_request_time
                            )
                            self.init_data_request_time = (
                                TidesInfoData_read.init_data_request_time
                            )
                            self.next_day_midnight = (
                                TidesInfoData_read.next_day_midnight
                            )
                            self.next_month_midnight = (
                                TidesInfoData_read.next_month_midnight
                            )
                            """Ok!"""
                            previous_data_decode = True

                except:
                    _LOGGER.debug(
                        "Error in decoding data file at: %s", int(current_time)
                    )
                    """reinit data from server"""
                    self.init_data = None
                    self.data_datums_offset = None
                    self.data = None
                    self.data_request_time = None
                    self.init_data_request_time = None
                    self.next_day_midnight = timedelta(days=1) + (
                        datetime.today()
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
                    self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA) + (
                        datetime.today()
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
                    """ KO """
                    previous_data_decode = False

            if previous_data_decode == True:
                """set data to store"""
                """ the read file has been trusted """
                self.TidesInfoData.store_init_info(
                    self.init_data, self.init_data_request_time
                )
                self.TidesInfoData.store_init_offset(self.data_datums_offset)
                self.TidesInfoData.store_data_info(self.data, self.data_request_time)
                self.TidesInfoData.store_next_midnight(
                    self.next_day_midnight, self.next_month_midnight
                )

            if previous_data_decode == False or force_init_data_to_require == True:
                """retrieve station"""
                self.retrieve_tide_station()
                init_data_fetched = True

        """ normal process """
        if self.data_request_time == None:
            data_to_require = True
        elif current_time >= (
            self.data_request_time + self._worldides_request_interval
        ):
            data_to_require = True
        elif datetime.fromtimestamp(current_time) >= self.next_day_midnight:
            data_to_require = True
        else:
            data_to_require = False

        if data_to_require:
            self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        if init_data_fetched:
            self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA) + (
                datetime.today()
            ).replace(hour=0, minute=0, second=0, microsecond=0)
        """store next midnight"""
        self.TidesInfoData.store_next_midnight(
            self.next_day_midnight, self.next_month_midnight
        )

        if data_to_require:
            self.retrieve_height_station(force_init_data_to_require)
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
            self.init_data_request_time = current_time
            self.TidesInfoData.store_init_info(
                self.init_data, self.init_data_request_time
            )

    def retrieve_height_station(self, force_init_data_to_require):
        """Get the latest data from WorldTidesInfo API v2."""
        data_has_been_received = False
        current_time = time.time()
        datums_string = ""
        if self.data_datums_offset == None or force_init_data_to_require == True:
            datums_string = "&datums"

        """3 days --> to manage one day beyond midnight and one before midnight"""
        resource = (
            "https://www.worldtides.info/api/v2?extremes&days=3&date=today&heights&plot&timemode=24&step=900"
            "&key={}&lat={}&lon={}&datum={}&stationDistance={}&color={}&background={}{}"
        ).format(
            self._key,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
            self._plot_color,
            self._plot_background,
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
            """ signed pickle """
            data_pickle = pickle.dumps(self.TidesInfoData, pickle.HIGHEST_PROTOCOL)
            hmac_data = hmac.new(
                self._key.encode("utf-8"), data_pickle, hashlib.sha1
            ).hexdigest()
            to_save = SignedPickle(data_pickle, hmac_data)
            """ dump """
            """store received data"""
            data_to_store = open(self.TidesInfoData_filename, "wb")
            pickler = pickle.Pickler(data_to_store, pickle.HIGHEST_PROTOCOL)
            pickler.dump(to_save)
            data_to_store.close()
