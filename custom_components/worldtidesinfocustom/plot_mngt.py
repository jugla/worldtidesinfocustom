# Python library
import time

# matplot lib
from matplotlib import pyplot as plt

# from component
from pyworldtidesinfo.worldtidesinfo_server import give_info_from_raw_data

from .sensor_service import convert_to_perform

# duration type
LONG_DURATION = "Long"
NORMAL_DURATION = "Normal"


class Plot_Manager:
    """Class to manage MatPlotLib"""

    def __init__(
        self,
        name,
        duration_type,
        unit_to_display,
        tide_prediction_duration,
        filename,
        transparent_background,
    ):
        ### for trace
        self._name = name + duration_type
        self._duration_type = duration_type
        self._unit_to_display = unit_to_display
        self._tide_prediction_duration = tide_prediction_duration
        self._filename = filename
        self._transparent_background = transparent_background

        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )
        self._convert_meter_to_feet = convert_meter_to_feet

        if self._duration_type == NORMAL_DURATION:
            # 1 hour
            self._time_scale = 60 * 60
            self._time_scale_string = "hour"
        else:
            # 1 day
            self._time_scale = 60 * 60 * 24
            self._time_scale_string = "day"

    def convert_to_unit_to_display(self, heigh_array):
        heigh_value = []
        for index in range(len(heigh_array)):
            converted_heigh = heigh_array[index] * self._convert_meter_to_feet
            heigh_value.append(converted_heigh)
        return heigh_value

    def convert_to_relative_time(self, epoch_array, current_time):
        relative_time_value = []
        for index in range(len(epoch_array)):
            converted_time = (epoch_array[index] - current_time) / self._time_scale
            relative_time_value.append(converted_time)
        return relative_time_value

    def compute_new_plot(self, data, current_time):
        if data is None:
            return

        tide_info = give_info_from_raw_data(data)

        # Retrieve plot within time frame
        # draw below 24h : from -6h to 18h (for one day)
        # otherwise : from -6h to 18h (+ time of prediction - 1)
        epoch_frame_min = current_time - 6 * 60 * 60
        epoch_frame_max = (
            current_time
            + 3 * 6 * 60 * 60
            + ((self._tide_prediction_duration - 1) * 24 * 60 * 60)
        )

        # Retrieve heigh within time frame
        height_data = tide_info.give_tide_prediction_within_time_frame(
            epoch_frame_min, epoch_frame_max
        )

        height_value = self.convert_to_unit_to_display(height_data.get("height_value"))
        height_time = self.convert_to_relative_time(
            height_data.get("height_epoch"), current_time
        )

        # current time and height
        current_height_data = tide_info.give_current_height_in_UTC(current_time)
        current_height_value = self.convert_to_unit_to_display(
            [current_height_data.get("current_height")]
        )
        current_height_time = self.convert_to_relative_time(
            [current_height_data.get("current_height_epoch")], current_time
        )

        # Retrieve extrema within time frame
        extrema_data = tide_info.give_tide_extrema_within_time_frame(
            epoch_frame_min, epoch_frame_max
        )

        extrema_value = self.convert_to_unit_to_display(
            extrema_data.get("extrema_value")
        )
        extrema_time = self.convert_to_relative_time(
            extrema_data.get("extrema_epoch"), current_time
        )

        # color to draw
        extrema_color = "firebrick"
        current_height_color = "black"

        ### Perform plotting
        # name is used as an id --> all coordinators works in //
        fig = plt.figure(self._name)
        fig.clf()
        ax = fig.add_subplot(1, 1, 1)
        # trace the predict tides
        ax.plot(height_time, height_value, color="cornflowerblue")
        # plot the current position
        ax.plot(
            current_height_time,
            current_height_value,
            color=current_height_color,
            marker="o",
        )
        # plot the next tide
        ax.plot(
            extrema_time,
            extrema_value,
            color=extrema_color,
            marker="o",
            linestyle="none",
        )
        # label on axis
        ax.set_ylabel("height " + self._unit_to_display)
        current_time_string = time.strftime("%a %H:%M", time.localtime(current_time))
        ax.set_xlabel(
            "time in " + self._time_scale_string + " respect to " + current_time_string
        )
        # grid + filling
        ax.grid()
        ax.fill_between(height_time, 0, height_value, color="lightblue")
        # annotate the current position
        label = "{:.2f}\n@ {}".format(current_height_value[0], current_time_string)
        ax.annotate(
            label,  # this is the text
            (
                current_height_time[0],
                current_height_value[0],
            ),  # this is the point to label
            textcoords="offset points",  # how to position the text
            xytext=(0, 15),  # distance from text to points (x,y)
            ha="center",  # horizontal alignment can be left, right or center
            color=current_height_color,
        )  # color
        # annotate the next tide
        for extrema_index in range(len(extrema_value)):
            extrema_time_string = time.strftime(
                "%a %H:%M",
                time.localtime(
                    (extrema_time[extrema_index] * self._time_scale) + current_time
                ),
            )
            label = "{:.2f}\n@ {}".format(
                extrema_value[extrema_index], extrema_time_string
            )
            if (extrema_index % 4) == 0 or (extrema_index % 4) == 1:
                y_label_offset = -28
            else:
                y_label_offset = 16
            ax.annotate(
                label,  # this is the text
                (
                    extrema_time[extrema_index],
                    extrema_value[extrema_index],
                ),  # this is the point to label
                textcoords="offset points",  # how to position the text
                xytext=(0, y_label_offset),  # distance from text to points (x,y)
                ha="center",  # horizontal alignment can be left, right or center
                color=extrema_color,
            )  # color

        # save the figure
        fig.savefig(self._filename, transparent=self._transparent_background)
