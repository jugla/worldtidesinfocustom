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
# snapshot 3 : add last request time
# snapshot 4 : add last init request time
# snapshot 5 : in parameter add prediction time
snapshot_version = 5

# Python library
import logging

_LOGGER = logging.getLogger(__name__)


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
        """Update data from cloud server"""
        self.init_data = read_data.init_data
        self.init_data_request_time = read_data.init_data_request_time
        self.data_datums_offset = read_data.data_datums_offset
        self.data = read_data.data
        self.data_request_time = read_data.data_request_time
        # in order to manage midnight (ie. switch between 2 requests)
        self.previous_data = read_data.previous_data
        self.previous_data_request_time = read_data.previous_data_request_time


class Data_Scheduling:
    """Scheduling"""

    def __init__(self):
        self.next_day_midnight = None
        self.next_month_midnight = None
        self.last_request_time = None
        self.last_init_request_time = None

    def setup_next_data_midnight(self):
        self.next_day_midnight = timedelta(days=1) + (datetime.today()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def setup_next_init_data_midnight(self):
        self.next_month_midnight = timedelta(days=FORCE_FETCH_INIT_DATA_INTERVAL) + (
            datetime.today()
        ).replace(hour=0, minute=0, second=0, microsecond=0)

    def setup_next_midnights(self):
        self.setup_next_data_midnight()
        self.setup_next_init_data_midnight()

    def store_read_input(self, read_data):
        self.next_day_midnight = read_data.next_day_midnight
        self.next_month_midnight = read_data.next_month_midnight
        self.last_request_time = read_data.last_request_time
        self.last_init_request_time = read_data.last_request_time


class WorldTidesInfo_server_scheduler:
    """Class to manage the schedule of Word Tide Info serer"""

    def __init__(
        self,
        key,
        worldtidesinfo_server_parameter,
    ):
        self._Server_Parameter = worldtidesinfo_server_parameter
        self._parameter_updated = False

        self._Data_Retrieve = Data_Retrieve()
        self._Data_Scheduling = Data_Scheduling()

    def update_parameter(self, worldtidesinfo_server_parameter):
        self._Server_Parameter = worldtidesinfo_server_parameter
        # if parameter has been already reinit , no need to reinit
        # whatch out : at init , there is no data. So it's usefull to not go
        # in parameter = True (If doing then it will request data from server)
        if self._Data_Retrieve.init_data is not None:
            self._parameter_updated = True

    def give_parameter(self):
        return self._Server_Parameter

    def no_data(self):
        return self._Data_Retrieve.data is None or self._Data_Retrieve.data is None

    def no_datum(self):
        return self._Data_Retrieve.data_datums_offset is None

    def store_init_data(self, init_data, init_data_request_time):
        self._Data_Retrieve.init_data = init_data
        self._Data_Retrieve.init_data_request_time = init_data_request_time
        self._Data_Scheduling.last_init_request_time = init_data_request_time

    def process_no_new_init_data(self, last_init_request_time):
        if self._parameter_updated:
            self._Data_Retrieve.init_data = None
            self._Data_Retrieve.init_data_request_time = None
            self._Data_Scheduling.last_init_request_time = None
        self._Data_Scheduling.last_init_request_time = last_init_request_time

    def store_new_data(self, data, data_request_time):
        """Store new data and backup previous"""

        if self._parameter_updated:
            self._Data_Retrieve.previous_data = None
            self._Data_Retrieve.previous_data_request_time = None
            self._Data_Scheduling.last_request_time = None
        else:
            # in order to manage midnight (ie. switch between 2 requests)
            self._Data_Retrieve.previous_data = self._Data_Retrieve.data
            self._Data_Retrieve.previous_data_request_time = (
                self._Data_Retrieve.data_request_time
            )
        # normal process
        self._Data_Retrieve.data = data
        self._Data_Retrieve.data_request_time = data_request_time
        self._Data_Scheduling.last_request_time = data_request_time

        self._parameter_updated = False

    def process_no_new_data(self, last_request_time):
        if self._parameter_updated:
            self._Data_Retrieve.previous_data = None
            self._Data_Retrieve.previous_data_request_time = None
            self._Data_Scheduling.last_request_time = None

        self._Data_Scheduling.last_request_time = last_request_time
        self._parameter_updated = False

    def setup_next_midnights(self):
        """update all midnights"""
        self._Data_Scheduling.setup_next_midnights()

    def setup_next_data_midnight(self):
        self._Data_Scheduling.setup_next_data_midnight()

    def setup_next_init_data_midnight(self):
        self._Data_Scheduling.setup_next_init_data_midnight()

    def init_data_to_be_fetched(self, current_time):
        """Decide whether or not Init Data has to be retrieved"""
        init_data_to_require = False
        reason = "No Reason"
        if self._Data_Scheduling.last_init_request_time is None:
            init_data_to_require = True
            reason = "last_init_request_time equal to None"
        elif (
            datetime.fromtimestamp(current_time)
            >= self._Data_Scheduling.next_month_midnight
        ):
            init_data_to_require = True
            reason = "month midnight reached"
        elif self._parameter_updated:
            init_data_to_require = True
            reason = "parameter has changed"
        else:
            init_data_to_require = False
        if init_data_to_require:
            _LOGGER.debug("Init Tide to be fetched due to : %s", reason)

        return init_data_to_require

    def give_scheduler_image(self):
        """Give Scheduler snapshot intended to be saved on disk"""
        snapshot = {"Version": snapshot_version}
        snapshot["Parameter"] = self._Server_Parameter
        snapshot["Scheduling"] = self._Data_Scheduling
        snapshot["Data"] = self._Data_Retrieve
        return snapshot

    def scheduler_snapshot_usable(self, snapshot_read):
        Usable = False
        try:
            if snapshot_read.get("Version") is not None:
                if snapshot_read.get("Version") == snapshot_version:
                    if snapshot_read.get("Parameter") is not None:
                        if self._Server_Parameter.compare_parameter(
                            snapshot_read.get("Parameter")
                        ):
                            Usable = True
        except:
            Usable = False
        return Usable

    def use_scheduler_image_if_possible(self, snapshot_read):
        """Use saved data to re-initialized the scheduler"""
        scheduler_image_usable = False
        scheduler_image_used = False
        try:
            Read_Data_Scheduling = snapshot_read.get("Scheduling")
            Read_Data_Retrieve = snapshot_read.get("Data")
            scheduler_image_usable = True
        except:
            scheduler_image_usable = False
        if scheduler_image_usable:
            if Read_Data_Scheduling is not None and Read_Data_Retrieve is not None:
                self._Data_Scheduling.store_read_input(Read_Data_Scheduling)
                self._Data_Retrieve.store_read_input(Read_Data_Retrieve)
                scheduler_image_used = True
            else:
                _LOGGER.debug("World Tide Disc Image not usable")

        return scheduler_image_used

    def data_to_be_fetched(self, init_data_has_been_fetched, current_time):
        """Decide whether or not data has to be retrieved"""
        data_to_require = False
        reason = "No Reason"
        if init_data_has_been_fetched:
            data_to_require = True
            reason = "Station has been reinit"
        elif self._Data_Scheduling.last_request_time is None:
            data_to_require = True
            reason = "last_request_time is None"
        elif current_time >= (
            self._Data_Scheduling.last_request_time
            + DEFAULT_WORLDTIDES_REQUEST_INTERVAL
        ):
            data_to_require = True
            reason = "Data Scheduling too old"
        elif (
            datetime.fromtimestamp(current_time)
            >= self._Data_Scheduling.next_day_midnight
        ):
            data_to_require = True
            reason = "Midnight is reached"
        else:
            data_to_require = False
        if data_to_require:
            _LOGGER.debug("Tide Height to be fetched due to : %s", reason)
        return data_to_require
