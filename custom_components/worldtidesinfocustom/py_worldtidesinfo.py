"""gather function objects thal allow to manage Word Tides Info server API V2"""
# python library
import time

import requests

# Component library
PLOT_CURVE_UNIT_FT = "feet"
PLOT_CURVE_UNIT_M = "meters"


class Server_Parameter:
    """Parameter"""

    def __init__(
        self,
        key,
        lat,
        lon,
        vertical_ref,
        tide_station_distance,
        plot_color,
        plot_background,
        unit_curve_picture,
    ):
        self._key = key
        self._lat = lat
        self._lon = lon
        self._vertical_ref = vertical_ref
        self._tide_station_distance = tide_station_distance
        self._plot_color = plot_color
        self._plot_background = plot_background
        self._unit_curve_picture = unit_curve_picture

    def compare_parameter(self, parameter):
        if (
            parameter._key == self._key
            and parameter._lat == self._lat
            and parameter._lon == self._lon
            and parameter._vertical_ref == self._vertical_ref
            and parameter._tide_station_distance == self._tide_station_distance
            and parameter._plot_color == self._plot_color
            and parameter._plot_background == self._plot_background
            and parameter._unit_curve_picture == self._unit_curve_picture
        ):
            return True
        else:
            return False


class WorldTidesInfo_server:
    """Class to manage the Word Tide Info serer"""

    def __init__(
        self,
        key,
        lat,
        lon,
        vertical_ref,
        tide_station_distance,
        plot_color,
        plot_background,
        unit_curve_picture,
    ):
        # parameter
        self._Server_Parameter = Server_Parameter(
            key,
            lat,
            lon,
            vertical_ref,
            tide_station_distance,
            plot_color,
            plot_background,
            unit_curve_picture,
        )

        # information from server
        self.last_tide_station_raw_data = None
        self.last_tide_station_request_time = None
        self.last_tide_station_request_credit = 0
        self.last_tide_station_request_error_value = None
        # information from server
        self.last_tide_raw_data = None
        self.last_tide_raw_data_request_time = None
        self.last_tide_request_credit = 0
        self.last_tide_request_error_value = None

    def give_parameter(self):
        return self._Server_Parameter

    def retrieve_tide_station_credit(self):
        return self.last_tide_station_request_credit

    def retrieve_tide_station_err_value(self):
        return self.last_tide_station_request_error_value

    def retrieve_tide_station_raw_data(self):
        return self.last_tide_station_raw_data

    def retrieve_tide_station_request_time(self):
        return self.last_tide_station_request_time

    def retrieve_tide_station(self):
        """retrieve information related tide station only"""
        current_time = time.time()
        data_has_been_received = False
        data = None

        resource = (
            "https://www.worldtides.info/api/v2?stations"
            "&key={}&lat={}&lon={}&stationDistance={}"
        ).format(
            self._Server_Parameter._key,
            self._Server_Parameter._lat,
            self._Server_Parameter._lon,
            self._Server_Parameter._tide_station_distance,
        )
        try:
            data = requests.get(resource, timeout=10).json()
            data_has_been_received = True
            error_value = None

        except ValueError as err:
            error_value = err.args
            data_has_been_received = False
            data = None

        # information from server
        self.last_tide_station_raw_data = data
        self.last_tide_station_request_time = current_time
        if data_has_been_received:
            self.last_tide_station_request_credit = data["callCount"]
        else:
            self.last_tide_station_request_credit = 0
        self.last_tide_station_request_error_value = error_value

        return data_has_been_received

    def retrieve_tide_credit(self):
        return self.last_tide_request_credit

    def retrieve_tide_err_value(self):
        return self.last_tide_request_error_value

    def retrieve_tide_raw_data(self):
        return self.last_tide_raw_data

    def retrieve_tide_request_time(self):
        return self.last_tide_request_time

    def retrieve_tide_height_over_one_day(self, datum_flag):
        """retrieve information related to tide"""
        current_time = time.time()
        data_has_been_received = False
        data = None

        datums_string = ""
        if datum_flag:
            datums_string = "&datums"

        # 3 days --> to manage one day beyond midnight and one before midnight
        resource = (
            "https://www.worldtides.info/api/v2?extremes&days=3&date=today&heights&plot&timemode=24&step=900"
            "&key={}&lat={}&lon={}&datum={}&stationDistance={}&color={}&background={}&units={}{}"
        ).format(
            self._Server_Parameter._key,
            self._Server_Parameter._lat,
            self._Server_Parameter._lon,
            self._Server_Parameter._vertical_ref,
            self._Server_Parameter._tide_station_distance,
            self._Server_Parameter._plot_color,
            self._Server_Parameter._plot_background,
            self._Server_Parameter._unit_curve_picture,
            datums_string,
        )
        try:
            data = requests.get(resource, timeout=10).json()
            data_has_been_received = True
            error_value = None
        except ValueError as err:
            data = None
            data_has_been_received = False
            error_value = err.args
        # information from server
        self.last_tide_raw_data = data
        self.last_tide_request_time = current_time
        if data_has_been_received:
            self.last_tide_request_credit = data["callCount"]
        else:
            self.last_tide_request_credit = 0
        self.last_tide_request_error_value = error_value

        return data_has_been_received


class give_info_from_raw_data:
    def __init__(self, data):
        self._data = data

    def give_next_tide_in_epoch(self, current_epoch_time):
        """ give info from X seconds from epoch"""
        current_time = int(current_epoch_time)
        next_tide = 0
        for tide_index in range(len(self._data["extremes"])):
            if self._data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index
        if self._data["extremes"][next_tide]["dt"] < current_time:
            next_tide = next_tide + 1
        if next_tide >= len(self._data["extremes"]):
            return {"error": "no date in future"}

        tide_time = self._data["extremes"][next_tide]["dt"]

        tide_type = "None"
        if "High" in str(self._data["extremes"][next_tide]["type"]):
            tide_type = "High"
        elif "Low" in str(self._data["extremes"][next_tide]["type"]):
            tide_type = "Low"
        else:
            tide_type = "None"

        return {"tide_type": tide_type, "tide_time": tide_time}

    def give_vertical_ref(self):
        if "responseDatum" in self._data:
            return self._data["responseDatum"]
        else:
            return "no vertical ref"

    def give_tidal_station_used(self):
        if "station" in self._data:
            return self._data["station"]
        else:
            return "no reference station used"

    def give_next_high_low_tide_in_UTC(self, current_epoch_time):
        """ give info from X seconds from epoch"""
        current_time = int(current_epoch_time)

        # Next tide
        next_tide = 0
        for tide_index in range(len(self._data["extremes"])):
            if self._data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index

        # Managed the case where next_tide has not been updated : if next_tide=0 perform a check
        if self._data["extremes"][next_tide]["dt"] < current_time:
            next_tide = next_tide + 1

        if next_tide >= len(self._data["extremes"]):
            return {"error": "no date in future"}

        if "High" in str(self._data["extremes"][next_tide]["type"]):
            high_tide_time_utc = self._data["extremes"][next_tide]["date"]
            high_tide_height = self._data["extremes"][next_tide]["height"]

            low_tide_time_utc = self._data["extremes"][next_tide + 1]["date"]
            low_tide_height = self._data["extremes"][next_tide + 1]["height"]

        elif "Low" in str(self._data["extremes"][next_tide]["type"]):
            high_tide_time_utc = self._data["extremes"][next_tide + 1]["date"]
            high_tide_height = self._data["extremes"][next_tide + 1]["height"]

            low_tide_time_utc = self._data["extremes"][next_tide]["date"]
            low_tide_height = self._data["extremes"][next_tide]["height"]

        return {
            "high_tide_time_utc": high_tide_time_utc,
            "high_tide_height": high_tide_height,
            "low_tide_time_utc": low_tide_time_utc,
            "low_tide_height": low_tide_height,
        }

    def give_current_height_in_UTC(self, current_epoch_time):
        """ give info from X seconds from epoch"""
        current_time = int(current_epoch_time)
        # The height
        current_height_index = 0
        for height_index in range(len(self._data["heights"])):
            if self._data["heights"][height_index]["dt"] < current_time:
                current_height_index = height_index
        current_height = self._data["heights"][current_height_index]["height"]
        current_height_utc = self._data["heights"][current_height_index]["date"]
        return {
            "current_height": current_height,
            "current_height_utc": current_height_utc,
        }

    def give_station_around_info(self):
        """give tidal station around info"""
        station_around_nb = len(self._data["stations"])
        station_around_name = ""
        if len(self._data["stations"]) > 0:
            station_around_name = ""
            for name_index in range(len(self._data["stations"])):
                station_around_name = (
                    station_around_name
                    + "; "
                    + self._data["stations"][name_index]["name"]
                )
        else:
            station_around_name = "None"
        return {
            "station_around_nb": station_around_nb,
            "station_around_name": station_around_name,
        }

    def give_nearest_station_time_zone(self):
        """give the nearest tide station time zone"""
        if len(self._data["stations"]) > 0:
            station_around_time_zone = self._data["stations"][0]["timezone"]
        else:
            station_around_time_zone = "None"
        return station_around_time_zone

    def give_datum(self):
        if "datums" in self._data:
            return self._data["datums"]
        else:
            return None

    def give_plot_picture_without_header(self):
        if "plot" in self._data:
            std_string = "data:image/png;base64,"
            str_to_convert = self._data["plot"][
                len(std_string) : len(self._data["plot"])
            ]
        else:
            str_to_convert = None
        return str_to_convert


class give_info_from_raw_datums_data:
    """retrive datum information"""

    def __init__(self, datums_data):
        self._datums_data = datums_data

    def give_mean_water_spring_datums_offset(self):
        MHW_index = 0
        MLW_index = 0
        for ref_index in range(len(self._datums_data)):
            if self._datums_data[ref_index]["name"] == "MHWS":
                MHW_index = ref_index
            if self._datums_data[ref_index]["name"] == "MLWS":
                MLW_index = ref_index
        datum_offset_MHWS = self._datums_data[MHW_index]["height"]
        datum_offset_MLWS = self._datums_data[MLW_index]["height"]

        return {
            "datum_offset_MHWS": datum_offset_MHWS,
            "datum_offset_MLWS": datum_offset_MLWS,
        }
