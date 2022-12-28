"""Data Coordinator."""
# Python library
import logging

_LOGGER = logging.getLogger(__name__)

import time
from datetime import datetime, timedelta

# HA library
from homeassistant.const import (
    LENGTH_FEET,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_MILES,
)
from homeassistant.util.unit_conversion import DistanceConverter
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

KM_PER_MI = DistanceConverter.convert(1, LENGTH_MILES, LENGTH_KILOMETERS)
MI_PER_KM = DistanceConverter.convert(1, LENGTH_KILOMETERS, LENGTH_MILES)
FT_PER_M = DistanceConverter.convert(1, LENGTH_METERS, LENGTH_FEET)

from pyworldtidesinfo.worldtidesinfo_server import (
    PLOT_CURVE_UNIT_FT,
    PLOT_CURVE_UNIT_M,
    WorldTidesInfo_server,
    give_info_from_raw_data,
    give_info_from_raw_data_N_and_N_1,
    give_info_from_raw_datums_data,
)

# Component library
from . import give_persistent_filename
from .const import IMPERIAL_CONF_UNIT, WWW_PATH
from .plot_mngt import LONG_DURATION, NORMAL_DURATION, Plot_Manager
from .server_request_scheduler import WorldTidesInfo_server_scheduler
from .storage_mngt import File_Data_Cache, File_Picture


class WordTide_Data_Coordinator:
    """End Point to Fetch Data and to maintain cache"""

    def __init__(
        self,
        hass,
        name,
        lat,
        lon,
        key,
        vertical_ref,
        plot_color,
        plot_background,
        tide_station_distance,
        tide_prediction_duration,
        unit_to_display,
        mat_plot_transparent_background,
    ):
        ### for trace
        self._name = name

        ### Self
        self._tide_picture_file = None
        self._tide_cache_file = None
        self._worldtidesinfo_server = None
        self._worldtidesinfo_server_scheduler = None
        self._credit_used = 0

        # managment og global count
        self.overall_count = 0
        self.overall_count_tmp = 0

        # prepare filename
        filenames = give_persistent_filename(hass, name)

        ### Self
        # prepare the tide picture management
        tide_picture_file = File_Picture(
            hass.config.path(WWW_PATH), filenames.get("curve_filename")
        )
        self._tide_picture_file = tide_picture_file

        ### Self
        # prepare persistent file management
        tide_cache_file = File_Data_Cache(
            filenames.get("persistent_data_filename"),
            key,
        )
        self._tide_cache_file = tide_cache_file
        self._tide_cache_file_first_update = True

        ### Self
        one_day_prediction = 1
        self._plot_manager = Plot_Manager(
            name,
            NORMAL_DURATION,
            unit_to_display,
            one_day_prediction,
            filenames.get("plot_filename"),
            mat_plot_transparent_background,
        )
        self._long_plot_manager = Plot_Manager(
            name,
            LONG_DURATION,
            unit_to_display,
            tide_prediction_duration,
            filenames.get("plot_long_prediction_filename"),
            mat_plot_transparent_background,
        )

        # unit used for display, and convert tide station distance
        if unit_to_display == IMPERIAL_CONF_UNIT:
            server_tide_station_distance = tide_station_distance * KM_PER_MI
            unit_curve_picture = PLOT_CURVE_UNIT_FT
        else:
            server_tide_station_distance = tide_station_distance
            unit_curve_picture = PLOT_CURVE_UNIT_M

        #### Self
        self._unit_to_display = unit_to_display

        # instanciate server front end
        worldtidesinfo_server = WorldTidesInfo_server(
            key,
            lat,
            lon,
            vertical_ref,
            server_tide_station_distance,
            tide_prediction_duration,
            plot_color,
            plot_background,
            unit_curve_picture,
        )
        worldtidesinfo_server_parameter = worldtidesinfo_server.give_parameter()

        ### Self
        self._worldtidesinfo_server = worldtidesinfo_server

        # instantiate scheduler front end
        worldtidesinfo_server_scheduler = WorldTidesInfo_server_scheduler(
            key,
            worldtidesinfo_server_parameter,
        )

        ### Self
        self._worldtidesinfo_server_scheduler = worldtidesinfo_server_scheduler

        #### Init
        # set first trigger of scheduler
        self._worldtidesinfo_server_scheduler.setup_next_midnights()

    def no_data(self):
        return self._worldtidesinfo_server_scheduler.no_data()

    def get_data(self):
        return {
            "current_data": self._worldtidesinfo_server_scheduler._Data_Retrieve.data,
            "previous_data": self._worldtidesinfo_server_scheduler._Data_Retrieve.previous_data,
            "init_data": self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data,
            "data_datums_offset": self._worldtidesinfo_server_scheduler._Data_Retrieve.data_datums_offset,
        }

    def get_credit_used(self):
        return self._credit_used

    def get_schedule_time(self):
        return {
            "data_request_time": self._worldtidesinfo_server_scheduler._Data_Retrieve.data_request_time,
            "previous_data_request_time": self._worldtidesinfo_server_scheduler._Data_Retrieve.previous_data_request_time,
            "init_data_request_time": self._worldtidesinfo_server_scheduler._Data_Retrieve.init_data_request_time,
            "next_day_midnight": self._worldtidesinfo_server_scheduler._Data_Scheduling.next_day_midnight,
            "next_month_midnight": self._worldtidesinfo_server_scheduler._Data_Scheduling.next_month_midnight,
        }

    def get_curve_filename(self):
        return self._tide_picture_file.full_filename()

    def get_server_parameter(self):
        return self._worldtidesinfo_server.give_parameter()

    def _retrieve_tide_station(self):
        """TIDE STATION : Get the latest data from WorldTidesInfo."""
        if self._worldtidesinfo_server.retrieve_tide_station():
            _LOGGER.debug(
                "Init data queried at: %s",
                self._worldtidesinfo_server.retrieve_tide_station_request_time,
            )
            self._credit_used = (
                self._credit_used
                + self._worldtidesinfo_server.retrieve_tide_station_credit()
            )
            init_data = self._worldtidesinfo_server.retrieve_tide_station_raw_data()
            init_data_request_time = (
                self._worldtidesinfo_server.retrieve_tide_station_request_time()
            )
            self._worldtidesinfo_server_scheduler.store_init_data(
                init_data, init_data_request_time
            )

        else:
            _LOGGER.error(
                "Error retrieving tide station data from WorldTidesInfo %s : %s",
                self._name,
                self._worldtidesinfo_server.retrieve_tide_station_err_value(),
            )
            self._worldtidesinfo_server_scheduler.process_no_new_init_data(
                self._worldtidesinfo_server.retrieve_tide_station_request_time()
            )

    def _retrieve_height_station(self, init_data_fetched):
        """HEIGTH : Get the latest data from WorldTidesInfo."""
        data = None
        datum_flag = (
            self._worldtidesinfo_server_scheduler.no_datum() or init_data_fetched
        )
        if self._worldtidesinfo_server.retrieve_tide_height_over_one_day(datum_flag):
            _LOGGER.debug(
                "Data queried at: %s",
                self._worldtidesinfo_server.retrieve_tide_request_time(),
            )

            # update store data
            data = self._worldtidesinfo_server.retrieve_tide_raw_data()
            self._worldtidesinfo_server_scheduler.store_new_data(
                data, self._worldtidesinfo_server.retrieve_tide_request_time()
            )
            self._credit_used = (
                self._credit_used + self._worldtidesinfo_server.retrieve_tide_credit()
            )

            # process information
            tide_info = give_info_from_raw_data(data)
            datum_content = tide_info.give_datum()
            if datum_content.get("error") is None:
                self._worldtidesinfo_server_scheduler._Data_Retrieve.data_datums_offset = datum_content.get(
                    "datums"
                )
            string_picture = tide_info.give_plot_picture_without_header()
            if string_picture.get("error") is None:
                self._tide_picture_file.store_picture_base64(
                    string_picture.get("image")
                )
            else:
                self._tide_picture_file.remove_previous_picturefile()

        else:
            _LOGGER.error(
                "Error retrieving height station data from WorldTidesInfo %s: %s",
                self._name,
                self._worldtidesinfo_server.retrieve_tide_err_value(),
            )
            self._worldtidesinfo_server_scheduler.process_no_new_data(
                self._worldtidesinfo_server.retrieve_tide_request_time()
            )

    def check_if_tide_file_exist_for_init(self, current_time):
        # Init data (initialisation or refresh or retrieve from a file)
        # if self._worldtidesinfo_server_scheduler.init_data_to_be_fetched(current_time):
        if self._tide_cache_file_first_update:
            self._tide_cache_file_first_update = False
            if self._tide_cache_file.Fetch_Stored_Data():
                SchedulerSnapshot = self._tide_cache_file.Data_Read()
                _LOGGER.debug(
                    "Snpashot retrieved data file at: %s for %s",
                    int(current_time),
                    self._name,
                )
                if self._worldtidesinfo_server_scheduler.scheduler_snapshot_usable(
                    SchedulerSnapshot
                ):
                    _LOGGER.debug(
                        "Snpashot decoding data file at: %s for %s",
                        int(current_time),
                        self._name,
                    )
                    self._worldtidesinfo_server_scheduler.use_scheduler_image_if_possible(
                        SchedulerSnapshot
                    )
                else:
                    _LOGGER.debug(
                        "Error in decoding data file at: %s for %s",
                        int(current_time),
                        self._name,
                    )

    def _update_and_fetch_server_data(self):
        init_data_fetched = False

        self._credit_used = 0
        current_time = time.time()

        # no data has been retrieved -at least once- or too old or change ref
        if self._worldtidesinfo_server_scheduler.init_data_to_be_fetched(current_time):
            _LOGGER.debug(
                "Init Tide data need to be requeried at: %s for %s",
                int(current_time),
                self._name,
            )
            # Retrieve station from server
            self._retrieve_tide_station()
            self._worldtidesinfo_server_scheduler.setup_next_init_data_midnight()
            init_data_fetched = True

        # Update: normal process
        if self._worldtidesinfo_server_scheduler.data_to_be_fetched(
            init_data_fetched, current_time
        ):
            self._retrieve_height_station(init_data_fetched)
            self._worldtidesinfo_server_scheduler.setup_next_data_midnight()
            self._tide_cache_file.store_data(
                self._worldtidesinfo_server_scheduler.give_scheduler_image()
            )
        else:
            _LOGGER.debug(
                "Tide data not need to be requeried at: %s for %s",
                int(current_time),
                self._name,
            )

        # generate a plot curve at each update
        # create a plot
        data = self._worldtidesinfo_server_scheduler._Data_Retrieve.data
        self._plot_manager.compute_new_plot(data, current_time)
        self._long_plot_manager.compute_new_plot(data, current_time)

        return True

    def update_server_data(self):
        ### The class is intended to be used by several sensor
        ### but only one is forecast to update at a time
        ### (write of new data during update)
        ### The function is sync (i.e. or used with async and a LOCK)
        result = self._update_and_fetch_server_data()

    def change_reference_point(self, lat, long):
        self._worldtidesinfo_server.change_ref_point(lat, long)
        worldtidesinfo_server_parameter = self._worldtidesinfo_server.give_parameter()
        self._worldtidesinfo_server_scheduler.update_parameter(
            worldtidesinfo_server_parameter
        )
