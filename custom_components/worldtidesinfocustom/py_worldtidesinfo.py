"""gather function objects thal allow to manage Word Tides Info server API V2"""
# python library
import time

import requests

# Component library
PLOT_CURVE_UNIT_FT = "feet"
PLOT_CURVE_UNIT_M = "meters"
SERVER_API_VERSION = "V2"


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
        self._version = SERVER_API_VERSION
        self._key = key
        self._lat = lat
        self._lon = lon
        self._vertical_ref = vertical_ref
        self._tide_station_distance = tide_station_distance
        self._plot_color = plot_color
        self._plot_background = plot_background
        self._unit_curve_picture = unit_curve_picture

    def compare_parameter(self, parameter):
        """compare the parameter given to the stored ones"""
        result = False
        try:
            if (
                parameter._version == self._version
                and parameter._key == self._key
                and parameter._lat == self._lat
                and parameter._lon == self._lon
                and parameter._vertical_ref == self._vertical_ref
                and parameter._tide_station_distance == self._tide_station_distance
                and parameter._plot_color == self._plot_color
                and parameter._plot_background == self._plot_background
                and parameter._unit_curve_picture == self._unit_curve_picture
            ):
                result = True
            else:
                result = False
        except:
            result = False
        return result

    def get_latitude(self):
        return self._lat

    def get_longitude(self):
        return self._lon

    def get_tide_station_distance(self):
        return self._tide_station_distance

    def change_ref_point(self, lat, lon):
        self._lat = lat
        self._lon = lon


class WorldTidesInfo_server:
    """Class to manage the Word Tide Info server"""

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

    def change_ref_point(self, lat, lon):
        self._Server_Parameter.change_ref_point(lat, lon)

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
            data_get = requests.get(resource, timeout=10)
            if data_get.status_code == 200:
                data = data_get.json()
                data_has_been_received = True
                error_value = None
            else:
                error_value = data_get.status_code
                data_has_been_received = False
                data = None

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
            data_get = requests.get(resource, timeout=10)
            if data_get.status_code == 200:
                data = data_get.json()
                data_has_been_received = True
                error_value = None
            else:
                error_value = data_get.status_code
                data_has_been_received = False
                data = None

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
    """Give a set of function to decode retrieved data"""

    def __init__(self, data):
        self._data = data

    def give_tide_in_epoch(self, current_epoch_time, next_tide_flag):
        """give info from X seconds from epoch"""

        if self._data == None:
            return {"error": "no data"}

        current_time = int(current_epoch_time)
        next_tide = 0
        for tide_index in range(len(self._data["extremes"])):
            if self._data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index
        if next_tide_flag:
            if self._data["extremes"][next_tide]["dt"] < current_time:
                next_tide = next_tide + 1
        if next_tide >= len(self._data["extremes"]):
            return {"error": "no date in future"}
        if next_tide_flag == False:
            if self._data["extremes"][next_tide]["dt"] > current_time:
                return {"error": "no date in past"}

        tide_time = self._data["extremes"][next_tide]["dt"]

        tide_type = "None"
        if "High" in str(self._data["extremes"][next_tide]["type"]):
            tide_type = "High"
        elif "Low" in str(self._data["extremes"][next_tide]["type"]):
            tide_type = "Low"
        else:
            tide_type = "None"

        return {"tide_type": tide_type, "tide_time": tide_time}

    def give_next_tide_in_epoch(self, current_epoch_time):
        next_tide_flag = True
        return self.give_tide_in_epoch(current_epoch_time, next_tide_flag)

    def give_previous_tide_in_epoch(self, current_epoch_time):
        next_tide_flag = False
        return self.give_tide_in_epoch(current_epoch_time, next_tide_flag)

    def give_vertical_ref(self):
        if self._data == None:
            return {"error": "no data"}
        elif "responseDatum" in self._data:
            return {"vertical_ref": self._data["responseDatum"]}
        else:
            return {"error": "no vertical ref"}

    def give_tidal_station_used(self):
        if self._data == None:
            return {"error": "no data"}
        elif "station" in self._data:
            return {"station": self._data["station"]}
        else:
            return {"error": "no reference station used"}

    def give_high_low_tide_in_UTC(self, current_epoch_time, next_tide_flag):
        """give info from X seconds from epoch"""
        if self._data == None:
            return {"error": "no data"}

        current_time = int(current_epoch_time)

        # Next tide
        next_tide = 0
        for tide_index in range(len(self._data["extremes"])):
            if self._data["extremes"][tide_index]["dt"] < current_time:
                next_tide = tide_index

        # Managed the case where next_tide has not been updated : if next_tide=0 perform a check
        if next_tide_flag:
            if self._data["extremes"][next_tide]["dt"] < current_time:
                next_tide = next_tide + 1

        if next_tide >= len(self._data["extremes"]):
            return {"error": "no date in future"}

        if next_tide_flag == False:
            if self._data["extremes"][next_tide]["dt"] > current_time:
                return {"error": "no date in past"}

        if "High" in str(self._data["extremes"][next_tide]["type"]):
            high_tide_time_utc = self._data["extremes"][next_tide]["date"]
            high_tide_time_epoch = self._data["extremes"][next_tide]["dt"]
            high_tide_height = self._data["extremes"][next_tide]["height"]

            low_tide_time_utc = self._data["extremes"][next_tide + 1]["date"]
            low_tide_time_epoch = self._data["extremes"][next_tide + 1]["dt"]
            low_tide_height = self._data["extremes"][next_tide + 1]["height"]

        elif "Low" in str(self._data["extremes"][next_tide]["type"]):
            high_tide_time_utc = self._data["extremes"][next_tide + 1]["date"]
            high_tide_time_epoch = self._data["extremes"][next_tide + 1]["dt"]
            high_tide_height = self._data["extremes"][next_tide + 1]["height"]

            low_tide_time_utc = self._data["extremes"][next_tide]["date"]
            low_tide_time_epoch = self._data["extremes"][next_tide]["dt"]
            low_tide_height = self._data["extremes"][next_tide]["height"]

        return {
            "high_tide_time_utc": high_tide_time_utc,
            "high_tide_time_epoch": high_tide_time_epoch,
            "high_tide_height": high_tide_height,
            "low_tide_time_utc": low_tide_time_utc,
            "low_tide_time_epoch": low_tide_time_epoch,
            "low_tide_height": low_tide_height,
        }

    def give_next_high_low_tide_in_UTC(self, current_epoch_time):
        next_tide_flag = True
        return self.give_high_low_tide_in_UTC(current_epoch_time, next_tide_flag)

    def give_current_high_low_tide_in_UTC(self, current_epoch_time):
        next_tide_flag = False
        return self.give_high_low_tide_in_UTC(current_epoch_time, next_tide_flag)

    def give_current_height_in_UTC(self, current_epoch_time):
        """give info from X seconds from epoch"""
        current_time = int(current_epoch_time)

        if self._data == None:
            return {"error": "no data"}

        # The height
        current_height_index = 0
        for height_index in range(len(self._data["heights"])):
            if self._data["heights"][height_index]["dt"] < current_time:
                current_height_index = height_index
        current_height = self._data["heights"][current_height_index]["height"]
        current_height_utc = self._data["heights"][current_height_index]["date"]
        current_height_epoch = self._data["heights"][current_height_index]["dt"]

        return {
            "current_height": current_height,
            "current_height_utc": current_height_utc,
            "current_height_epoch": current_height_epoch,
        }

    def give_tide_prediction_within_time_frame(self, epoch_frame_min, epoch_frame_max):
        """retrieve data from frame_min to frame_max"""
        if self._data == None:
            return {"error": "no data"}

        current_height_index = 0
        height_value = []
        height_time = []
        for height_index in range(len(self._data["heights"])):
            height_current_value = self._data["heights"][height_index]["height"]
            height_current_time = self._data["heights"][height_index]["dt"]
            # retrive height and time
            if (height_current_time > epoch_frame_min) and (
                height_current_time < epoch_frame_max
            ):
                height_value.append(height_current_value)
                height_time.append(height_current_time)
        return {
            "height_value": height_value,
            "height_epoch": height_time,
        }

    def give_station_around_info(self):
        """give tidal station around info"""
        if self._data == None:
            return {"error": "no_data"}

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
        if self._data == None:
            return {"error": "no_data"}
        if len(self._data["stations"]) > 0:
            return {"time_zone": self._data["stations"][0]["timezone"]}
        else:
            return {"error": "no station around"}

    def give_datum(self):
        if self._data == None:
            return {"error": "no data"}
        elif "datums" in self._data:
            return {"datums": self._data["datums"]}
        else:
            return {"error": "no_datums"}

    def give_plot_picture_without_header(self):
        """Give picture in base 64 without the format header"""
        if self._data == None:
            return {"error": "no data"}
        elif "plot" in self._data:
            std_string = "data:image/png;base64,"
            str_to_convert = self._data["plot"][
                len(std_string) : len(self._data["plot"])
            ]
            return {"image": str_to_convert}
        else:
            return {"error": "no_image"}


class give_info_from_raw_datums_data:
    """Decode datum information"""

    def __init__(self, datums_data):
        self._datums_data = datums_data

    def give_mean_water_spring_datums_offset(self):
        if self._datums_data == None:
            return {"error": "no data"}
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


class give_info_from_raw_data_N_and_N_1:
    """Give a set of function to decode info from current or previous data"""

    def __init__(self, data, previous_data):
        self._info = give_info_from_raw_data(data)
        self._previous_info = give_info_from_raw_data(previous_data)

    def give_current_height_in_UTC(self, current_epoch_time):
        result = self._info.give_current_height_in_UTC(current_epoch_time)
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_current_height_in_UTC(
                current_epoch_time
            )
            return previous_result

    def give_high_low_tide_in_UTC(self, current_epoch_time, next_tide_flag):
        result = self._info.give_high_low_tide_in_UTC(
            current_epoch_time, next_tide_flag
        )
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_high_low_tide_in_UTC(
                current_epoch_time, next_tide_flag
            )
            return previous_result

    def give_next_high_low_tide_in_UTC(self, current_epoch_time):
        next_tide_flag = True
        return self.give_high_low_tide_in_UTC(current_epoch_time, next_tide_flag)

    def give_current_high_low_tide_in_UTC(self, current_epoch_time):
        next_tide_flag = False
        return self.give_high_low_tide_in_UTC(current_epoch_time, next_tide_flag)

    def give_tide_in_epoch(self, current_epoch_time, next_tide_flag):
        result = self._info.give_tide_in_epoch(current_epoch_time, next_tide_flag)
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_tide_in_epoch(
                current_epoch_time, next_tide_flag
            )
            return previous_result

    def give_next_tide_in_epoch(self, current_epoch_time):
        next_tide_flag = True
        return self.give_tide_in_epoch(current_epoch_time, next_tide_flag)

    def give_previous_tide_in_epoch(self, current_epoch_time):
        next_tide_flag = False
        return self.give_tide_in_epoch(current_epoch_time, next_tide_flag)

    def give_vertical_ref(self):
        result = self._info.give_vertical_ref()
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_vertical_ref()
            return previous_result

    def give_tidal_station_used(self):
        result = self._info.give_tidal_station_used()
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_tidal_station_used()
            return previous_result

    def give_nearest_station_time_zone(self):
        result = self._info.give_nearest_station_time_zone()
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_nearest_station_time_zone()
            return previous_result

    def give_datum(self):
        result = self._info.give_datum()
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_datum()
            return previous_result

    def give_plot_picture_without_header(self):
        result = self._info.give_plot_picture_without_header()
        if result.get("error") == None:
            return result
        else:
            previous_result = self._previous_info.give_plot_picture_without_header()
            return previous_result
