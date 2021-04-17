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
    DEBUG_FLAG,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
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
from .py_worldtidesinfo import (
    PLOT_CURVE_UNIT_FT,
    PLOT_CURVE_UNIT_M,
    WorldTidesInfo_server,
)
from .storage_mngt import File_Data_Cache, File_Picture
from .server_request_scheduler import  WorldTidesInfo_server_scheduler

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

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return 

    key = config.get(CONF_API_KEY)
    vertical_ref = config.get(CONF_VERTICAL_REF)
    plot_color = config.get(CONF_PLOT_COLOR)
    plot_background = config.get(CONF_PLOT_BACKGROUND)
    # worldides_request_interval = config.get(CONF_WORLDTIDES_REQUEST_INTERVAL)
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

    #what is the unit used
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    # unit used for display, and convert tide station distance
    if unit_to_display == IMPERIAL_CONF_UNIT:
        server_tide_station_distance = tide_station_distance * KM_PER_MI
        unit_curve_picture = PLOT_CURVE_UNIT_FT
    else:
        server_tide_station_distance = tide_station_distance
        unit_curve_picture = PLOT_CURVE_UNIT_M

    # instanciate server front end
    worldtidesinfo_server = WorldTidesInfo_server(
        key,
        lat,
        lon,
        vertical_ref,
        server_tide_station_distance,
        plot_color,
        plot_background,
        unit_curve_picture,
    )
    worldtidesinfo_server_parameter = worldtidesinfo_server.give_parameter()

    # instantiate scheduler front end
    worldtidesinfo_server_scheduler = WorldTidesInfo_server_scheduler(
        key,
        worldtidesinfo_server_parameter,
    )

    # create the sensor
    tides = WorldTidesInfoCustomSensor(
        name,
        unit_to_display,
        tide_picture_file,
        tide_cache_file,
        worldtidesinfo_server,
        worldtidesinfo_server_scheduler,
    )
    # tides.retrieve_tide_station()
    tides.update()
    if tides._worldtidesinfo_server_scheduler.no_data() :
        _LOGGER.error("No data available for this location")
        return

    add_entities([tides])


class WorldTidesInfoCustomSensor(Entity):
    """Representation of a WorldTidesInfo sensor."""

    def __init__(
        self,
        name,
        unit_to_display,
        tide_picture_file,
        tide_cache_file,
        worldtidesinfo_server,
        worldtidesinfo_server_scheduler,
    ):
        """Initialize the sensor."""

        # Parameters from configuration.yaml
        self._name = name
        self._unit_to_display = unit_to_display

        # Picture data
        self._tide_picture_file = tide_picture_file

        # World Tide Info Server
        self._worldtidesinfo_server = worldtidesinfo_server
        # the scheduler
        self._worldtidesinfo_server_scheduler = worldtidesinfo_server_scheduler
        # set first trigger of scheduler
        self._worldtidesinfo_server_scheduler.setup_next_midnights()
        # Initialize the data to store
        self._tide_cache_file = tide_cache_file

        self.credit_used = 0


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

        if self._worldtidesinfo_server_scheduler.no_data():
            return attr

        data = self._worldtidesinfo_server_scheduler._Data_Retrieve.data
        init_data = self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data
        data_datums_offset = self._worldtidesinfo_server_scheduler._Data_Retrieve.data_datums_offset

        # The vertical reference used : LAT, ...
        attr["vertical_reference"] = data["responseDatum"]

        # Tide station characteristics
        if "station" in data:
            attr["tidal_station_used"] = data["station"]
        else:
            attr["tidal_station_used"] = "no reference station used"

        # Next tide
        next_tide = 0
        for tide_index in range(len(data["extremes"])):
            if data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index

        # Managed the case where next_tide has not been updated : if next_tide=0 perform a check
        if data["extremes"][next_tide]["dt"] < current_time:
            next_tide = next_tide + 1

        if "High" in str(data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = data["extremes"][next_tide]["date"]
            attr["high_tide_height"] = round(
                data["extremes"][next_tide]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            attr["low_tide_time_utc"] = data["extremes"][next_tide + 1]["date"]
            attr["low_tide_height"] = round(
                data["extremes"][next_tide + 1]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            diff_high_tide_next_low_tide = (
                data["extremes"][next_tide]["height"]
                - data["extremes"][next_tide + 1]["height"]
            )
        elif "Low" in str(data["extremes"][next_tide]["type"]):
            attr["high_tide_time_utc"] = data["extremes"][next_tide + 1]["date"]
            attr["high_tide_height"] = round(
                data["extremes"][next_tide + 1]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            attr["low_tide_time_utc"] = data["extremes"][next_tide]["date"]
            attr["low_tide_height"] = round(
                data["extremes"][next_tide]["height"] * convert_meter_to_feet,
                ROUND_HEIGTH,
            )
            # diff_high_tide_next_low_tide = (
            #    data["extremes"][next_tide + 1]["height"]
            #    - data["extremes"][next_tide + 2]["height"]
            # )
            diff_high_tide_next_low_tide = (
                data["extremes"][next_tide + 1]["height"]
                - data["extremes"][next_tide]["height"]
            )

        # The height
        current_height = 0
        for height_index in range(len(data["heights"])):
            if data["heights"][height_index]["dt"] < current_time:
                current_height = height_index
        attr["current_height"] = round(
            data["heights"][current_height]["height"] * convert_meter_to_feet,
            ROUND_HEIGTH,
        )
        attr["current_height_utc"] = data["heights"][current_height]["date"]

        # The coeff tide_highlow_over the Mean Water Spring
        MHW_index = 0
        MLW_index = 0
        for ref_index in range(len(data_datums_offset)):
            if data_datums_offset[ref_index]["name"] == "MHWS":
                MHW_index = ref_index
            if data_datums_offset[ref_index]["name"] == "MLWS":
                MLW_index = ref_index

        attr["Coeff_resp_MWS"] = round(
            (
                diff_high_tide_next_low_tide
                / (
                    data_datums_offset[MHW_index]["height"]
                    - data_datums_offset[MLW_index]["height"]
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
            "%H:%M:%S %d/%m/%y", time.localtime(self._worldtidesinfo_server_scheduler._Data_Retrieve.data_request_time)
        )
        # KEEP FOR DEBUG:
        if DEBUG_FLAG:
            attr["Init_data_request_time"] = time.strftime(
                "%H:%M:%S %d/%m/%y", time.localtime(self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data_request_time)
            )
            attr["next day midnight"] = self._worldtidesinfo_server_scheduler._Data_Scheduling.next_day_midnight.strftime(
                "%H:%M:%S %d/%m/%y"
            )
            attr["next month midnight"] = self._worldtidesinfo_server_scheduler._Data_Scheduling.next_month_midnight.strftime(
                "%H:%M:%S %d/%m/%y"
            )

        # Filename of tide picture
        attr["plot"] = self._tide_picture_file.full_filename()

        # Tide detailed characteristic
        attr["station_around_nb"] = len(init_data["stations"])
        attr["station_distance"] = round(
            self._worldtidesinfo_server_scheduler._Server_Parameter._tide_station_distance * convert_km_to_miles, ROUND_STATION_DISTANCE
        )
        if len(init_data["stations"]) > 0:
            attr["station_around_name"] = ""
            for name_index in range(len(init_data["stations"])):
                attr["station_around_name"] = (
                    attr["station_around_name"]
                    + "; "
                    + init_data["stations"][name_index]["name"]
                )
            attr["station_around_time_zone"] = init_data["stations"][0]["timezone"]
        else:
            attr["station_around_name"] = "None"
            attr["station_around_time_zone"] = "None"

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        data = self._worldtidesinfo_server_scheduler._Data_Retrieve.data
        if data:
            # Get next tide time
            current_time = int(time.time())
            next_tide = 0
            for tide_index in range(len(data["extremes"])):
                if data["extremes"][tide_index]["dt"] < current_time:
                    next_tide = tide_index
            if data["extremes"][next_tide]["dt"] < current_time:
                next_tide = next_tide + 1

            if "High" in str(data["extremes"][next_tide]["type"]):
                tidetime = time.strftime(
                    "%H:%M", time.localtime(data["extremes"][next_tide]["dt"])
                )
                return f"High tide at {tidetime}"
            if "Low" in str(data["extremes"][next_tide]["type"]):
                tidetime = time.strftime(
                    "%H:%M", time.localtime(data["extremes"][next_tide]["dt"])
                )
                return f"Low tide at {tidetime}"
            return None
        return None

    def update(self):
        """Update of sensors."""
        init_data_fetched = False

        self.credit_used = 0
        current_time = time.time()

        # Init data (initialisation or refresh or retrieve from a file)
        if self._worldtidesinfo_server_scheduler.init_data_to_be_fetched(current_time):
            if self._tide_cache_file.Fetch_Stored_Data():
                SchedulerSnapshot = self._tide_cache_file.Data_Read()
                _LOGGER.debug(
                        "Snpashot retrieved data file at: %s ", int(current_time)
                    )
                if self._worldtidesinfo_server_scheduler.scheduler_snapshot_usable(SchedulerSnapshot):
                      _LOGGER.debug(
                          "Snpashot decoding data file at: %s ", int(current_time)
                      )
                      self._worldtidesinfo_server_scheduler.use_scheduler_image_if_possible(SchedulerSnapshot)
                else:
                    _LOGGER.debug(
                        "Error in decoding data file at: %s", int(current_time)
                    )

        #the data read is empty (the snapshot retrieve is not useable) or too old
        if self._worldtidesinfo_server_scheduler.init_data_to_be_fetched(current_time) == True:
             # Retrieve station from server
             self.retrieve_tide_station()
             self._worldtidesinfo_server_scheduler.setup_next_init_data_midnight()
             init_data_fetched = True

        # Update: normal process
        if self._worldtidesinfo_server_scheduler.data_to_be_fetched(init_data_fetched,current_time):
            self.retrieve_height_station(init_data_fetched)
            self._worldtidesinfo_server_scheduler.setup_next_data_midnight()
            self._tide_cache_file.store_data(self._worldtidesinfo_server_scheduler.give_scheduler_image())
        else:
            _LOGGER.debug(
                "Tide data not need to be requeried at: %s", int(current_time)
            )

    def retrieve_tide_station(self):
        """TIDE STATION : Get the latest data from WorldTidesInfo."""
        if self._worldtidesinfo_server.retrieve_tide_station():
            _LOGGER.debug(
                "Init data queried at: %s",
                self._worldtidesinfo_server.retrieve_tide_station_request_time,
            )
            self.credit_used = (
                self.credit_used
                + self._worldtidesinfo_server.retrieve_tide_station_credit()
            )
            self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data = (
                self._worldtidesinfo_server.retrieve_tide_station_raw_data()
            )
            self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data_request_time = (
                self._worldtidesinfo_server.retrieve_tide_station_request_time()
            )
        else:
            _LOGGER.error(
                "Error retrieving data from WorldTidesInfo: %s",
                self._worldtidesinfo_server.retrieve_tide_station_err_value,
            )

    def retrieve_height_station(self, init_data_fetched):
        """HEIGTH : Get the latest data from WorldTidesInfo."""
        data = None
        datum_flag = self._worldtidesinfo_server_scheduler.no_datum() or init_data_fetched == True
        if self._worldtidesinfo_server.retrieve_tide_height_over_one_day(datum_flag):
            _LOGGER.debug(
                "Data queried at: %s",
                self._worldtidesinfo_server.retrieve_tide_request_time,
            )
            data = self._worldtidesinfo_server.retrieve_tide_raw_data()
            self._worldtidesinfo_server_scheduler._Data_Retrieve.data = data
            self._worldtidesinfo_server_scheduler._Data_Retrieve.data_request_time = (
                self._worldtidesinfo_server.retrieve_tide_request_time()
            )
            self.credit_used = (
                self.credit_used + self._worldtidesinfo_server.retrieve_tide_credit()
            )
            # process information
            if "datums" in data:
                self._worldtidesinfo_server_scheduler._Data_Retrieve.data_datums_offset = data["datums"]
            if "plot" in data:
                std_string = "data:image/png;base64,"
                str_to_convert = data["plot"][
                    len(std_string) : len(data["plot"])
                ]
                self._tide_picture_file.store_picture_base64(str_to_convert)
            else:
                self._tide_picture_file.remove_previous_picturefile()

        else:
            _LOGGER.error(
                "Error retrieving data from WorldTidesInfo: %s",
                self._worldtidesinfo_server.retrieve_tide_err_value,
            )
