# Python library
import logging

# python library
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

# internal function
from .basic_service import distance_lat_long

# component library
from .const import DEFAULT_SENSOR_UPDATE_DISTANCE, IMPERIAL_CONF_UNIT, STATIC_CONF

# default time to update in second (6h)
DEFAULT_DISTANCE_TIME_INTERVAL = 21600
_LOGGER = logging.getLogger(__name__)


# class
class Live_Position_Management:
    # Management of Live Position

    def __init__(
        self,
        ref_lat,
        ref_long,
        ref_update_time,
        live_position_management,
        live_position_sensor_update_distance,
        unit_to_display,
        source,
        source_attr_lat,
        source_attr_long,
    ):
        self._ref_lat = ref_lat
        self._ref_long = ref_long
        self._ref_update_time = ref_update_time
        self._current_lat = None
        self._current_long = None
        self._current_update_time = None

        if live_position_management is None:
            self._live_position_management = STATIC_CONF
        else:
            self._live_position_management = live_position_management

        # unit used for display, and convert tide station distance
        if live_position_sensor_update_distance is None:
            live_position_sensor_update_distance = DEFAULT_SENSOR_UPDATE_DISTANCE

        if unit_to_display == IMPERIAL_CONF_UNIT:
            self._max_distance_without_lat_long_update = (
                live_position_sensor_update_distance * KM_PER_MI
            )
        else:
            self._max_distance_without_lat_long_update = (
                live_position_sensor_update_distance
            )

        self._source_id = source
        self._source_attr_lat = source_attr_lat
        self._source_attr_long = source_attr_long

        self._last_distance_from_ref_point = 0

    def get_source_id(self):
        return self._source_id

    def get_lat_attribute(self):
        return self._source_attr_lat

    def get_long_attribute(self):
        return self._source_attr_long

    def get_current_lat(self):
        return self._current_lat

    def get_current_long(self):
        return self._current_long

    def get_current_lat_or_ref_if_static(self):
        if self._live_position_management == STATIC_CONF:
            return self._ref_lat
        else:
            return self._current_lat

    def get_current_long_or_ref_if_static(self):
        if self._live_position_management == STATIC_CONF:
            return self._ref_long
        else:
            return self._current_long

    def get_ref_lat(self):
        return self._ref_lat

    def get_ref_long(self):
        return self._ref_long

    def get_ref_update_time(self):
        return self._ref_update_time

    def get_live_position_management(self):
        return self._live_position_management

    def need_to_change_ref(self, lat, long, current_time):
        need_to_change_ref_flag = False
        if (
            distance_lat_long((self._ref_lat, self._ref_long), (lat, long))
            > self._max_distance_without_lat_long_update
        ):
            need_to_change_ref_flag = True
        elif current_time >= (self._ref_update_time + DEFAULT_DISTANCE_TIME_INTERVAL):
            need_to_change_ref_flag = True
        else:
            need_to_change_ref_flag = False
        return need_to_change_ref_flag

    def update(self, lat, long, current_time):
        _LOGGER.debug(
            "LivePositionUpdate Lat %s Long %s RefLat %s RefLong %s",
            lat,
            long,
            self._ref_lat,
            self._ref_long,
        )

        self._current_lat = lat
        self._current_long = long
        self._current_update_time = current_time
        self._last_distance_from_ref_point = distance_lat_long(
            (self._ref_lat, self._ref_long), (lat, long)
        )

    def give_distance_from_ref_point(self):
        return self._last_distance_from_ref_point

    def change_ref(self, lat, long, current_time):
        self._ref_lat = lat
        self._ref_long = long
        self._ref_update_time = current_time
