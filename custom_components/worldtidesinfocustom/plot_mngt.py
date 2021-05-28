# Python library
import time

# matplot lib
from matplotlib import pyplot as plt

# from component
from .py_worldtidesinfo import give_info_from_raw_data
from .sensor_service import convert_to_perform


class Plot_Manager:
    """End Point to Fetch Data and to maintain cache"""

    def __init__(self, name, unit_to_display, filename):
        ### for trace
        self._name = name
        self._unit_to_display = unit_to_display
        self._filename = filename

        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )
        self._convert_meter_to_feet = convert_meter_to_feet

    def compute_new_plot(self, data, current_time):
        tide_info = give_info_from_raw_data(data)

        # Retrieve plot within time frame
        # draw below 24h : from -6h to 18h
        epoch_frame_min = current_time - 6 * 60 * 60
        epoch_frame_max = current_time + 3 * 6 * 60 * 60
        height_data = tide_info.give_tide_prediction_within_time_frame(
            epoch_frame_min, epoch_frame_max
        )

        height_value = []
        height_time = []
        for height_index in range(len(height_data.get("height_value"))):
            height_current_value = (height_data.get("height_value"))[
                height_index
            ] * self._convert_meter_to_feet
            height_value.append(height_current_value)

            height_current_time = (height_data.get("height_epoch"))[height_index]
            height_relative_current_time = (
                (height_current_time - current_time) / 60 / 60
            )
            height_time.append(height_relative_current_time)

        # current time and height
        current_height_data = tide_info.give_current_height_in_UTC(current_time)

        current_height_value = [
            current_height_data.get("current_height") * self._convert_meter_to_feet
        ]

        current_height_time_sample = current_height_data.get("current_height_epoch")
        height_relative_current_time_sample = (
            (current_height_time_sample - current_time) / 60 / 60
        )
        current_height_time = [height_relative_current_time_sample]

        # name is used as an id --> all coordinators works in //
        fig = plt.figure(self._name)
        fig.clf()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(height_time, height_value)
        ax.plot(current_height_time, current_height_value, color="red", marker="o")
        ax.set_ylabel("height " + self._unit_to_display)
        current_time_string = time.strftime("%H:%M", time.localtime(current_time))
        ax.set_xlabel("time in hour respect to " + current_time_string)
        ax.grid()
        fig.savefig(self._filename)
