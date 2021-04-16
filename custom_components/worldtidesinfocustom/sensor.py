"""Sensor worldtides.info."""
# Python library
import logging
import time
from datetime import datetime, timedelta

# HA library
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    LENGTH_FEET,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_MILES,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.distance import convert as dist_convert
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

KM_PER_MI = dist_convert(1, LENGTH_MILES, LENGTH_KILOMETERS)
MI_PER_KM = dist_convert(1, LENGTH_KILOMETERS, LENGTH_MILES)
FT_PER_M = dist_convert(1, LENGTH_METERS, LENGTH_FEET)

_LOGGER = logging.getLogger(__name__)

from .const import (
    ATTRIBUTION,
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    CONF_WORLDTIDES_REQUEST_INTERVAL,
    DEBUG_FLAG,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DEFAULT_WORLDTIDES_REQUEST_INTERVAL,
    FORCE_FETCH_INIT_DATA_INTERVAL,
    HA_CONF_UNIT,
    IMPERIAL_CONF_UNIT,
    METRIC_CONF_UNIT,
    ROUND_HEIGTH,
    ROUND_STATION_DISTANCE,
    SCAN_INTERVAL_SECONDS,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
    WWW_PATH,
)

# Component Library
# import .storage_mngt
from .py_worldtidesinfo import WorldTidesInfo_server,PLOT_CURVE_UNIT_FT,PLOT_CURVE_UNIT_M
from .storage_mngt import File_Data_Cache, File_Picture

# Sensor HA parameter
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
        vol.Optional(CONF_UNIT, default=DEFAULT_CONF_UNIT): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""

    # Get data from configuration.yaml
    name = config.get(CONF_NAME)

    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)
    key = config.get(CONF_API_KEY)
    vertical_ref = config.get(CONF_VERTICAL_REF)
    worldides_request_interval = config.get(CONF_WORLDTIDES_REQUEST_INTERVAL)
    tide_station_distance = config.get(CONF_STATION_DISTANCE)
    # prepare the tide picture management
    tide_picture_file = File_Picture(
        hass.config.path(WWW_PATH), hass.config.path(WWW_PATH, name + ".png")
    )

    tide_cache_file = File_Data_Cache(
        hass.config.path(
            STORAGE_DIR, WORLD_TIDES_INFO_CUSTOM_DOMAIN + "." + name + ".ser"
        ),
        key,
    )

    plot_color = config.get(CONF_PLOT_COLOR)
    plot_background = config.get(CONF_PLOT_BACKGROUND)
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    if unit_to_display == IMPERIAL_CONF_UNIT:
       server_tide_station_distance = tide_station_distance * KM_PER_MI
       unit_curve_picture = PLOT_CURVE_UNIT_FT
    else:
       server_tide_station_distance = tide_station_distance
       unit_curve_picture = PLOT_CURVE_UNIT_M

    worldtidesinfo_server = WorldTidesInfo_server (key, lat, lon, vertical_ref,
       server_tide_station_distance, plot_color, plot_background, unit_curve_picture)

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")

    # create the sensor
    tides = WorldTidesInfoCustomSensor(
        name,
        lat,
        lon,
        key,
        vertical_ref,
        worldides_request_interval,
        tide_station_distance,
        tide_picture_file,
        tide_cache_file,
        worldtidesinfo_server,
        plot_color,
        plot_background,
        unit_to_display,
    )
    # tides.retrieve_tide_station()
    tides.update()
    if tides.data == None:
        _LOGGER.error("No data available for this location")
        return

    add_entities([tides])


class TidesInfoData:
    """Class to store."""

    # This class will wrap up all data to be stored
    def __init__(self):

        # Initialize the data.
        # Parameter i.e. configuration.yaml
        self._name = None
        self._lat = None
        self._lon = None
        self._vertical_ref = None
        self._tide_station_distance = None
        self._plot_color = None
        self._plot_background = None
        self._unit_to_display = None

        # Data retrieve from server
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.init_data_request_time = None
        self.data_datums_offset = None
        self.next_day_midnight = None
        self.next_month_midnight = None

    def store_parameters(
        self,
        name,
        lat,
        lon,
        vertical_ref,
        tide_station_distance,
        plot_color,
        plot_background,
        unit_to_display,
    ):
        """Store the parameters."""
        self._name = name
        self._lat = lat
        self._lon = lon
        self._vertical_ref = vertical_ref
        self._tide_station_distance = tide_station_distance
        self._plot_color = plot_color
        self._plot_background = plot_background
        self._unit_to_display = unit_to_display

    def store_init_info(self, init_data, init_data_request_time):
        """Store data use at initialisation : part 1/2."""
        self.init_data = init_data
        self.init_data_request_time = init_data_request_time

    def store_init_offset(self, data_datums_offset):
        """Store data use at initialisation : part 2/2."""
        self.data_datums_offset = data_datums_offset

    def store_data_info(self, data, data_request_time):
        """Store periodic data."""
        self.data = data
        self.data_request_time = data_request_time

    def store_next_midnight(self, next_day_midnight, next_month_midnight):
        """Store next midnight trigger."""
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
        unit_to_display,
    ):
        """Condition to say if retrieve data match the current parameter."""
        if (
            self._name == name
            and self._lat == lat
            and self._lon == lon
            and self._vertical_ref == vertical_ref
            and self._tide_station_distance == tide_station_distance
            and self._plot_color == plot_color
            and self._plot_background == plot_background
            and self._unit_to_display == unit_to_display
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
        tide_picture_file,
        tide_cache_file,
        worldtidesinfo_server,
        plot_color,
        plot_background,
        unit_to_display,
    ):
        """Initialize the sensor."""

        # Parameters from configuration.yaml
        self._name = name
        self._lat = lat
        self._lon = lon
        self._key = key
        self._vertical_ref = vertical_ref
        self._worldides_request_interval = worldides_request_interval
        if unit_to_display == IMPERIAL_CONF_UNIT:
            self._tide_station_distance = tide_station_distance * KM_PER_MI
        else:
            self._tide_station_distance = tide_station_distance
        self._plot_color = plot_color
        self._plot_background = plot_background
        self._unit_to_display = unit_to_display

        # Picture data
        self._tide_picture_file = tide_picture_file

        # World Tide Info Server
        self._worldtidesinfo_server = worldtidesinfo_server

        # Internal data use to manage request to server
        self.init_data = None
        self.data = None
        self.data_request_time = None
        self.init_data_request_time = None
        self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA_INTERVAL) + (
            datetime.today()
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        self.credit_used = 0
        self.data_datums_offset = None
        # Initialize the data to store
        self._tide_cache_file = tide_cache_file
        self.TidesInfoData = TidesInfoData()
        # Store parameter
        self.TidesInfoData.store_parameters(
            self._name,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
            self._plot_color,
            self._plot_background,
            self._unit_to_display,
        )
        self.TidesInfoData.store_next_midnight(
            self.next_day_midnight, self.next_month_midnight
        )

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

        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            convert_meter_to_feet = FT_PER_M
            convert_km_to_miles = MI_PER_KM
        else:
            convert_meter_to_feet = 1
            convert_km_to_miles = 1

        # Unit system
        attr["Unit displayed"] = self._unit_to_display

        if self.data == None or self.init_data == None:
            return attr

        # The vertical reference used : LAT, ...
        attr["vertical_reference"] = self.data["responseDatum"]

        # Tide station characteristics
        if "station" in self.data:
            attr["tidal_station_used"] = self.data["station"]
        else:
            attr["tidal_station_used"] = "no reference station used"

        # Next tide
        next_tide = 0
        for tide_index in range(len(self.data["extremes"])):
            if self.data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index

        # Managed the case where next_tide has not been updated : if next_tide=0 perform a check
        if self.data["extremes"][next_tide]["dt"] < current_time:
            next_tide = next_tide + 1

        if "High" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["high_tide_height"] = round(
                self.data["extremes"][next_tide]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["low_tide_height"] = round(
                self.data["extremes"][next_tide + 1]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            diff_high_tide_next_low_tide = (
                self.data["extremes"][next_tide]["height"]
                - self.data["extremes"][next_tide + 1]["height"]
            )
        elif "Low" in str(self.data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = self.data["extremes"][next_tide + 1]["date"]
            attr["high_tide_height"] = round(
                self.data["extremes"][next_tide + 1]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            attr["low_tide_time_utc"] = self.data["extremes"][next_tide]["date"]
            attr["low_tide_height"] = round(
                self.data["extremes"][next_tide]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            # diff_high_tide_next_low_tide = (
            #    self.data["extremes"][next_tide + 1]["height"]
            #    - self.data["extremes"][next_tide + 2]["height"]
            # )
            diff_high_tide_next_low_tide = (
                self.data["extremes"][next_tide + 1]["height"]
                - self.data["extremes"][next_tide]["height"]
            )

        # The height
        current_height = 0
        for height_index in range(len(self.data["heights"])):
            if self.data["heights"][height_index]["dt"] < current_time:
                current_height = height_index
        attr["current_height"] = round(
            self.data["heights"][current_height]["height"] * convert_meter_to_feet,
            ROUND_HEIGTH,
        )
        attr["current_height_utc"] = self.data["heights"][current_height]["date"]

        # The coeff tide_highlow_over the Mean Water Spring
        MHW_index = 0
        MLW_index = 0
        for ref_index in range(len(self.data_datums_offset)):
            if self.data_datums_offset[ref_index]["name"] == "MHWS":
                MHW_index = ref_index
            if self.data_datums_offset[ref_index]["name"] == "MLWS":
                MLW_index = ref_index

        attr["Coeff_resp_MWS"] = round(
            (
                diff_high_tide_next_low_tide
                / (
                    self.data_datums_offset[MHW_index]["height"]
                    - self.data_datums_offset[MLW_index]["height"]
                )
            )
            * 100,
            1,
        )

        # Display the current
        attr["tide_amplitude"] = round(diff_high_tide_next_low_tide, ROUND_HEIGTH)

        # The credit used to display the update
        attr["CreditCallUsed"] = self.credit_used

        # Time where are trigerred the request
        attr["Data_request_time"] = time.strftime(
            "%H:%M:%S %d/%m/%y", time.localtime(self.data_request_time)
        )
        # KEEP FOR DEBUG:
        if DEBUG_FLAG:
            attr["Init_data_request_time"] = time.strftime(
                "%H:%M:%S %d/%m/%y", time.localtime(self.init_data_request_time)
            )
            attr["next day midnight"] = self.next_day_midnight.strftime(
                "%H:%M:%S %d/%m/%y"
            )
            attr["next month midnight"] = self.next_month_midnight.strftime(
                "%H:%M:%S %d/%m/%y"
            )

        # Filename of tide picture
        attr["plot"] = self._tide_picture_file.full_filename()

        # Tide detailed characteristic
        attr["station_around_nb"] = len(self.init_data["stations"])
        attr["station_distance"] = round(
            self._tide_station_distance * convert_km_to_miles, ROUND_STATION_DISTANCE
        )
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

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        if self.data:
            # Get next tide time
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
        """Update of sensors."""
        data_to_require = False
        init_data_to_require = False
        force_init_data_to_require = False
        init_data_fetched = False
        self.credit_used = 0
        current_time = time.time()

        # Init data (initialisation or refresh or retrieve from a file)
        if self.init_data == None:
            init_data_to_require = True
        elif datetime.fromtimestamp(current_time) >= self.next_month_midnight:
            init_data_to_require = True
            force_init_data_to_require = True
        else:
            init_data_to_require = False

        if init_data_to_require:
            previous_data_decode = False
            if self._tide_cache_file.Fetch_Stored_Data():
                TidesInfoData_read = self._tide_cache_file.Data_Read()
                try:
                    # The data is sure only after the following test
                    if self.TidesInfoData.data_usable(
                        TidesInfoData_read._name,
                        TidesInfoData_read._lat,
                        TidesInfoData_read._lon,
                        TidesInfoData_read._vertical_ref,
                        TidesInfoData_read._tide_station_distance,
                        TidesInfoData_read._plot_color,
                        TidesInfoData_read._plot_background,
                        TidesInfoData_read._unit_to_display,
                    ):

                        # Fetch data from file
                        self.init_data = TidesInfoData_read.init_data
                        self.data_datums_offset = TidesInfoData_read.data_datums_offset
                        self.data = TidesInfoData_read.data
                        self.data_request_time = TidesInfoData_read.data_request_time
                        self.init_data_request_time = (
                            TidesInfoData_read.init_data_request_time
                        )
                        self.next_day_midnight = TidesInfoData_read.next_day_midnight
                        self.next_month_midnight = (
                            TidesInfoData_read.next_month_midnight
                        )

                        # Ok!
                        previous_data_decode = True

                except:
                    _LOGGER.debug(
                        "Error in decoding data file at: %s", int(current_time)
                    )

                    # something is wrong : reinit data from server
                    self.init_data = None
                    self.data_datums_offset = None
                    self.data = None
                    self.data_request_time = None
                    self.init_data_request_time = None
                    self.next_day_midnight = timedelta(days=1) + (
                        datetime.today()
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
                    self.next_month_midnight = timedelta(
                        days=FORCE_FETCH_INIT_DATA_INTERVAL
                    ) + (datetime.today()).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    # KO !!
                    previous_data_decode = False

            if previous_data_decode == True:

                # Set data to store
                # The read file has been trusted

                self.TidesInfoData.store_init_info(
                    self.init_data, self.init_data_request_time
                )
                self.TidesInfoData.store_init_offset(self.data_datums_offset)
                self.TidesInfoData.store_data_info(self.data, self.data_request_time)
                self.TidesInfoData.store_next_midnight(
                    self.next_day_midnight, self.next_month_midnight
                )

            if previous_data_decode == False or force_init_data_to_require == True:
                # Retrieve station from server
                self.retrieve_tide_station()
                init_data_fetched = True

        # Update: normal process
        if init_data_fetched:
            data_to_require = True
        elif self.data_request_time == None:
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
            self.next_month_midnight = timedelta(
                days=FORCE_FETCH_INIT_DATA_INTERVAL
            ) + (datetime.today()).replace(hour=0, minute=0, second=0, microsecond=0)

        # Store next midnight
        self.TidesInfoData.store_next_midnight(
            self.next_day_midnight, self.next_month_midnight
        )

        if data_to_require:
            self.retrieve_height_station(init_data_fetched)
        else:
            _LOGGER.debug(
                "Tide data not need to be requeried at: %s", int(current_time)
            )

    def retrieve_tide_station(self):
        """TIDE STATION : Get the latest data from WorldTidesInfo."""
        if self._worldtidesinfo_server.retrieve_tide_station():
            _LOGGER.debug("Init data queried at: %s", self._worldtidesinfo_server.retrieve_tide_station_request_time)
            self.credit_used = self.credit_used + self._worldtidesinfo_server.retrieve_tide_station_credit()
            self.init_data =  self._worldtidesinfo_server.retrieve_tide_station_raw_data()
            self.init_data_request_time =  self._worldtidesinfo_server.retrieve_tide_station_request_time()
            self.TidesInfoData.store_init_info(self.init_data, self.init_data_request_time)
        else:
            _LOGGER.error("Error retrieving data from WorldTidesInfo: %s",  self._worldtidesinfo_server.retrieve_tide_station_err_value)


    def retrieve_height_station(self, init_data_fetched):
        """HEIGTH : Get the latest data from WorldTidesInfo."""
        datum_flag = (self.data_datums_offset == None or init_data_fetched == True)
        if  self._worldtidesinfo_server.retrieve_tide_height_over_one_day(datum_flag):
            _LOGGER.debug("Data queried at: %s",  self._worldtidesinfo_server.retrieve_tide_request_time)
            self.data =  self._worldtidesinfo_server.retrieve_tide_raw_data()
            self.data_request_time =  self._worldtidesinfo_server.retrieve_tide_request_time()
            self.credit_used = self.credit_used +  self._worldtidesinfo_server.retrieve_tide_credit()
            #process information
            self.TidesInfoData.store_data_info(self.data, self.data_request_time)
            if "datums" in self.data:
                self.data_datums_offset = self.data["datums"]
                self.TidesInfoData.store_init_offset(self.data_datums_offset)
            if "plot" in self.data:
                std_string = "data:image/png;base64,"
                str_to_convert = self.data["plot"][
                    len(std_string) : len(self.data["plot"])
                ]
                self._tide_picture_file.store_picture_base64(str_to_convert)
            else:
                self._tide_picture_file.remove_previous_picturefile()
            self._tide_cache_file.store_data(self.TidesInfoData)

        else:
            _LOGGER.error("Error retrieving data from WorldTidesInfo: %s",  self._worldtidesinfo_server.retrieve_tide_err_value)

