"""gather function objects thal allow to manage Word Tides Info server API V2"""
# python library
import requests
import time
# Component library
PLOT_CURVE_UNIT_FT = "feet"
PLOT_CURVE_UNIT_M = "meters"

class WorldTidesInfo_server:
    """Class to manage the Word Tide Info serer"""

    def __init__(self, key, lat, lon, vertical_ref,
         tide_station_distance, plot_color, plot_background, unit_curve_picture):
       #parameter
       self._key = key
       self._lat = lat
       self._lon = lon
       self._vertical_ref = vertical_ref
       self._tide_station_distance = tide_station_distance
       self._plot_color = plot_color
       self._plot_background = plot_background
       self._unit_curve_picture = unit_curve_picture
       #information from server
       self.last_tide_station_raw_data = None
       self.last_tide_station_request_time = None
       self.last_tide_station_request_credit = 0
       self.last_tide_station_request_error_value = None
       #information from server
       self.last_tide_raw_data = None
       self.last_tide_raw_data_request_time = None
       self.last_tide_request_credit = 0
       self.last_tide_request_error_value = None

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
        ).format(self._key, self._lat, self._lon, self._tide_station_distance)
        try:
            data = requests.get(resource, timeout=10).json()
            data_has_been_received = True
            error_value = None

        except ValueError as err:
            error_value = err.args
            data_has_been_received = False
            data = None

        #information from server
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

    def retrieve_tide_height_over_one_day(self,datum_flag):
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
            self._key,
            self._lat,
            self._lon,
            self._vertical_ref,
            self._tide_station_distance,
            self._plot_color,
            self._plot_background,
            self._unit_curve_picture,
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
        #information from server
        self.last_tide_raw_data = data
        self.last_tide_request_time = current_time
        if data_has_been_received:
            self.last_tide_request_credit = data["callCount"]
        else:
            self.last_tide_request_credit = 0
        self.last_tide_request_error_value = error_value

        return data_has_been_received
