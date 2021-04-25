"""Server request scheduler."""

# python library
import time
from datetime import datetime, timedelta

# Component library

# internal const
## fetch init data every 30 days
FORCE_FETCH_INIT_DATA_INTERVAL = 30
# set 25h : wacth dog to retrieve data
DEFAULT_WORLDTIDES_REQUEST_INTERVAL = 90000

# snapshot_version
# snapshot 1 : 1rst one
# snapshot 2 : add previous data
snapshot_version = 2


class Data_Retrieve:
    """Data retrieve from server."""

    def __init__(self):
        self.init_data = None
        self.init_data_request_time = None
        self.data_datums_offset = None
        self.data = None
        self.data_request_time = None
        # in order to manage midnight (ie. switch between 2 requests)
        self.previous_data = None
        self.previous_data_request_time = None

    def store_read_input(self, read_data):
        self.init_data = read_data.init_data
        self.init_data_request_time = read_data.init_data_request_time
        self.data_datums_offset = read_data.data_datums_offset
        self.data = read_data.data
        self.data_request_time = read_data.data_request_time
        # in order to manage midnight (ie. switch between 2 requests)
        self.previous_data = read_data.previous_data
        self.previous_data_request_time = read_data.previous_data_request_time


class Data_Scheduling:
    """ Scheduling """

    def __init__(self):
        self.next_day_midnight = None
        self.next_month_midnight = None

    def setup_next_data_midnight(self):
        self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def setup_next_init_data_midnight(self):
        self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA_INTERVAL) + (
            datetime.today()
        ).replace(hour=0, minute=0, second=0, microsecond=0)

    def setup_next_midnights(self):
        self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA_INTERVAL) + (
            datetime.today()
        ).replace(hour=0, minute=0, second=0, microsecond=0)

    def store_read_input(self, read_data):
        self.next_day_midnight = read_data.next_day_midnight
        self.next_month_midnight = read_data.next_month_midnight


class WorldTidesInfo_server_scheduler:
    """Class to manage the schedule of Word Tide Info serer"""

    def __init__(
        self,
        key,
        worldtidesinfo_server_parameter,
    ):

        self._Server_Parameter = worldtidesinfo_server_parameter

        self._Data_Retrieve = Data_Retrieve()
        self._Data_Scheduling = Data_Scheduling()

    def no_data(self):
        return self._Data_Retrieve.data == None or self._Data_Retrieve.data == None

    def no_datum(self):
        return self._Data_Retrieve.data_datums_offset == None

    def store_new_data(self, data, data_request_time):
        # in order to manage midnight (ie. switch between 2 requests)
        self.previous_data = self._Data_Retrieve.data
        self.previous_data_request_time = self._Data_Retrieve.data_request_time
        # normal process
        self._Data_Retrieve.data = data
        self._Data_Retrieve.data_request_time = data_request_time

    def setup_next_midnights(self):
        """update all midnights"""
        self._Data_Scheduling.setup_next_midnights()

    def setup_next_data_midnight(self):
        self._Data_Scheduling.setup_next_data_midnight()

    def setup_next_init_data_midnight(self):
        self._Data_Scheduling.setup_next_init_data_midnight()

    def init_data_to_be_fetched(self, current_time):
        init_data_to_require = False
        if self._Data_Retrieve.init_data == None:
            init_data_to_require = True
        elif (
            datetime.fromtimestamp(current_time)
            >= self._Data_Scheduling.next_month_midnight
        ):
            init_data_to_require = True
        else:
            init_data_to_require = False
        return init_data_to_require

    def give_scheduler_image(self):
        snapshot = {"Version": snapshot_version}
        snapshot["Parameter"] = self._Server_Parameter
        snapshot["Scheduling"] = self._Data_Scheduling
        snapshot["Data"] = self._Data_Retrieve
        return snapshot

    def scheduler_snapshot_usable(self, snapshot_read):
        Usable = False
        try:
            if snapshot_read.get("Version") != None:
                if snapshot_read.get("Version") == snapshot_version:
                    if snapshot_read.get("Parameter") != None:
                        if self._Server_Parameter.compare_parameter(
                            snapshot_read.get("Parameter")
                        ):
                            Usable = True
        except:
            Usable = False
        return Usable

    def use_scheduler_image_if_possible(self, snapshot_read):
        scheduler_image_usable = False
        scheduler_image_used = False
        try:
            Read_Data_Scheduling = snapshot_read.get("Scheduling")
            Read_Data_Retrieve = snapshot_read.get("Data")
            scheduler_image_usable = True
        except:
            scheduler_image_usable = False
        if scheduler_image_usable:
            if Read_Data_Scheduling != None and Read_Data_Retrieve != None:
                self._Data_Scheduling.store_read_input(Read_Data_Scheduling)
                self._Data_Retrieve.store_read_input(Read_Data_Retrieve)
                scheduler_image_used = True
        return scheduler_image_used

    def data_to_be_fetched(self, init_data_has_been_fetched, current_time):
        data_to_require = False
        if init_data_has_been_fetched:
            data_to_require = True
        elif self._Data_Retrieve.data_request_time == None:
            data_to_require = True
        elif current_time >= (
            self._Data_Retrieve.data_request_time + DEFAULT_WORLDTIDES_REQUEST_INTERVAL
        ):
            data_to_require = True
        elif (
            datetime.fromtimestamp(current_time)
            >= self._Data_Scheduling.next_day_midnight
        ):
            data_to_require = True
        else:
            data_to_require = False
        return data_to_require
