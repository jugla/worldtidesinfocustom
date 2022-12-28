# import python
import time
from datetime import datetime, timedelta

from homeassistant.const import (
    LENGTH_FEET,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_MILES,
)
from homeassistant.util.unit_conversion import DistanceConverter

# import HA


KM_PER_MI = DistanceConverter.convert(1, LENGTH_MILES, LENGTH_KILOMETERS)
MI_PER_KM = DistanceConverter.convert(1, LENGTH_KILOMETERS, LENGTH_MILES)
FT_PER_M = DistanceConverter.convert(1, LENGTH_METERS, LENGTH_FEET)

# import .storage_mngt
from pyworldtidesinfo.worldtidesinfo_server import (
    give_info_from_raw_data,
    give_info_from_raw_data_N_and_N_1,
    give_info_from_raw_datums_data,
)

from .basic_service import distance_lat_long

# import component
from .const import (
    DEBUG_FLAG,
    HALF_TIDE_SLACK_DURATION,
    IMPERIAL_CONF_UNIT,
    ROUND_COEFF,
    ROUND_DISTANCE,
    ROUND_HEIGTH,
    ROUND_HOUR,
    ROUND_SEC,
    STATIC_CONF,
)

# service
# primary function for sensor (attributes and state)


def worldtidesinfo_unique_id(lat, long, live_position_management, source):
    """give a unique id for sensor"""
    if live_position_management is None:
        return "lat:{}_long:{}".format(lat, long)
    elif live_position_management == STATIC_CONF:
        return "lat:{}_long:{}".format(lat, long)
    else:
        return "motion:{}_sensor{}".format(live_position_management, source)


def convert_to_perform(unit_to_display):
    """compute the conversion value Metric/Imperial"""
    if unit_to_display == IMPERIAL_CONF_UNIT:
        convert_meter_to_feet = FT_PER_M
        convert_km_to_miles = MI_PER_KM
    else:
        convert_meter_to_feet = 1
        convert_km_to_miles = 1
    return convert_meter_to_feet, convert_km_to_miles


def get_all_tide_info(worldtide_data_coordinator):
    """Retrieve the tide data within its decoder"""
    # retrieve tide data (current & previous)
    data_result = worldtide_data_coordinator.get_data()
    data = data_result.get("current_data")
    previous_data = data_result.get("previous_data")
    init_data = data_result.get("init_data")
    data_datums_offset = data_result.get("data_datums_offset")

    # the decoder
    tide_info = give_info_from_raw_data_N_and_N_1(data, previous_data)
    # retrieve init data
    init_tide_info = give_info_from_raw_data(init_data)
    # retrieve the datum
    datums_info = give_info_from_raw_datums_data(data_datums_offset)

    return tide_info, datums_info, init_tide_info


def get_tide_info_and_offset(worldtide_data_coordinator):
    """Retrieve the tide data within its decoder"""
    tide_info, datums_info, init_tide_info = get_all_tide_info(
        worldtide_data_coordinator
    )

    return tide_info, datums_info


def get_tide_info(worldtide_data_coordinator):
    """Retrieve the tide data within its decoder"""
    tide_info, datums_info, init_tide_info = get_all_tide_info(
        worldtide_data_coordinator
    )
    return tide_info


def give_unit_attribute(unit_to_display):
    """give the unit attributes"""
    attr = {}
    attr["Unit displayed"] = unit_to_display
    return attr


def current_height_attribute(tide_info, current_time, convert_meter_to_feet):
    """Compute attributes linked to current height"""
    attr = {}

    current_height_value = tide_info.give_current_height_in_UTC(current_time)
    if current_height_value.get("error") is None:
        attr["current_height_utc"] = current_height_value.get("current_height_utc")
        attr["current_height"] = round(
            current_height_value.get("current_height") * convert_meter_to_feet,
            ROUND_HEIGTH,
        )

    return attr


def current_height_state(tide_info, current_time, convert_meter_to_feet):
    """Compute state linked to current height"""
    state_value = None
    attr = current_height_attribute(tide_info, current_time, convert_meter_to_feet)
    if attr.get("current_height") is not None:
        state_value = attr.get("current_height")
    return state_value


def next_tide_attribute(tide_info, current_time, convert_meter_to_feet):
    """Compute attributes linked to next tide"""
    attr = {}

    next_tide_UTC = tide_info.give_next_high_low_tide_in_UTC(current_time)
    if next_tide_UTC.get("error") is None:
        attr["high_tide_time_utc"] = next_tide_UTC.get("high_tide_time_utc")
        attr["high_tide_time_local"] = time.strftime(
            "%H:%M", time.localtime(next_tide_UTC.get("high_tide_time_epoch"))
        )
        attr["high_tide_height"] = round(
            next_tide_UTC.get("high_tide_height") * convert_meter_to_feet,
            ROUND_HEIGTH,
        )
        attr["low_tide_time_utc"] = next_tide_UTC.get("low_tide_time_utc")
        attr["low_tide_time_local"] = time.strftime(
            "%H:%M", time.localtime(next_tide_UTC.get("low_tide_time_epoch"))
        )
        attr["low_tide_height"] = round(
            next_tide_UTC.get("low_tide_height") * convert_meter_to_feet,
            ROUND_HEIGTH,
        )

    return attr


def next_low_tide_height_state(tide_info, current_time, convert_meter_to_feet):
    """Compute low tide state linked to next tide"""
    state_value = None
    attr = next_tide_attribute(tide_info, current_time, convert_meter_to_feet)
    if attr.get("low_tide_height") is not None:
        state_value = attr.get("low_tide_height")
    return state_value


def next_low_tide_time_state(tide_info, current_time):
    """Compute low tide state linked to next tide"""
    state_value = None
    # do as if no conversion in meter
    convert_meter_to_feet = 1
    attr = next_tide_attribute(tide_info, current_time, convert_meter_to_feet)
    if attr.get("low_tide_time_local") is not None:
        state_value = attr.get("low_tide_time_local")
    return state_value


def next_high_tide_height_state(tide_info, current_time, convert_meter_to_feet):
    """Compute hight tide state linked to next tide"""
    state_value = None
    attr = next_tide_attribute(tide_info, current_time, convert_meter_to_feet)
    if attr.get("high_tide_height") is not None:
        state_value = attr.get("high_tide_height")
    return state_value


def next_high_tide_time_state(tide_info, current_time):
    """Compute hight tide state linked to next tide"""
    state_value = None
    # do as if no conversion in meter
    convert_meter_to_feet = 1
    attr = next_tide_attribute(tide_info, current_time, convert_meter_to_feet)
    if attr.get("high_tide_time_local") is not None:
        state_value = attr.get("high_tide_time_local")
    return state_value


def remaining_time_to_next_tide(tide_info, current_time):
    """Compute the time needed to reach next tide"""
    remaining_time = None
    # time_to_next_tide
    next_tide_in_epoch = tide_info.give_next_tide_in_epoch(current_time)

    # initialize data for delta time
    delta_current_time_to_next = 0

    # compute delta tide to next tide
    if next_tide_in_epoch.get("error") is None:
        delta_current_time_to_next = next_tide_in_epoch.get("tide_time") - current_time
        # convert in second in hour
        remaining_time = round(delta_current_time_to_next / 60 / 60, ROUND_HOUR)

    return remaining_time


def amplitude_attribute(
    next_flag, tide_info, datums_info, current_time, convert_meter_to_feet
):
    """Compute amplitude tide attribute linked to current/next tide"""
    attr = {}
    if next_flag:
        next_string = "next_"
        tide_UTC = tide_info.give_next_high_low_tide_in_UTC(current_time)
    else:
        next_string = ""
        tide_UTC = tide_info.give_current_high_low_tide_in_UTC(current_time)

    diff_high_tide_low_tide = None
    if tide_UTC.get("error") is None:
        diff_high_tide_low_tide = abs(
            tide_UTC.get("high_tide_height") - tide_UTC.get("low_tide_height")
        )
        attr[next_string + "tide_amplitude"] = round(
            diff_high_tide_low_tide * convert_meter_to_feet, ROUND_HEIGTH
        )

        # compute the Mean Water Spring offset
        MWS_datum_offset = datums_info.give_mean_water_spring_datums_offset()

        # The coeff tide_highlow_over the Mean Water Spring
        if MWS_datum_offset.get("error") is None:
            attr[next_string + "Coeff_resp_MWS"] = round(
                (
                    diff_high_tide_low_tide
                    / (
                        MWS_datum_offset.get("datum_offset_MHWS")
                        - MWS_datum_offset.get("datum_offset_MLWS")
                    )
                )
                * 100,
                ROUND_COEFF,
            )
    return attr


def current_amplitude_attribute(
    tide_info, datums_info, current_time, convert_meter_to_feet
):
    """Compute amplitude tide attribute linked to current tide"""
    next_flag = False
    return amplitude_attribute(
        next_flag, tide_info, datums_info, current_time, convert_meter_to_feet
    )


def next_amplitude_attribute(
    tide_info, datums_info, current_time, convert_meter_to_feet
):
    """Compute amplitude tide attribute linked to next tide"""
    next_flag = True
    return amplitude_attribute(
        next_flag, tide_info, datums_info, current_time, convert_meter_to_feet
    )


def current_amplitude_state(
    tide_info, datums_info, current_time, convert_meter_to_feet
):
    """Compute amplitude tide state linked to current tide"""
    state_value = None
    attr = current_amplitude_attribute(
        tide_info, datums_info, current_time, convert_meter_to_feet
    )
    if attr.get("tide_amplitude") is not None:
        state_value = attr.get("tide_amplitude")
    return state_value


def current_coeff_state(tide_info, datums_info, current_time, convert_meter_to_feet):
    """Compute coeff MWS tide state linked to current tide"""
    state_value = None
    attr = current_amplitude_attribute(
        tide_info, datums_info, current_time, convert_meter_to_feet
    )
    if attr.get("Coeff_resp_MWS") is not None:
        state_value = attr.get("Coeff_resp_MWS")
    return state_value


def tide_tendancy_attribute(tide_info, current_time):
    """Compute current tide tendancy attribute"""
    attr = {}
    # Tide Tendancy and time_to_next_tide
    next_tide_in_epoch = tide_info.give_next_tide_in_epoch(current_time)
    previous_tide_in_epoch = tide_info.give_previous_tide_in_epoch(current_time)

    # initialize data for delta time
    delta_current_time_to_next = 0
    delta_current_time_from_previous = 0

    # compute delta tide to next tide
    if next_tide_in_epoch.get("error") is None:
        delta_current_time_to_next = next_tide_in_epoch.get("tide_time") - current_time

    # compute delta time from previous tide
    if previous_tide_in_epoch.get("error") is None:
        delta_current_time_from_previous = current_time - previous_tide_in_epoch.get(
            "tide_time"
        )

    attr["time_to_next_tide"] = "(hours) {}".format(
        timedelta(seconds=round(delta_current_time_to_next, ROUND_SEC))
    )

    # KEEP FOR DEBUG:
    if DEBUG_FLAG:
        attr["time_from_previous_tide"] = "(hours) {}".format(
            timedelta(seconds=delta_current_time_from_previous)
        )

    # compute tide tendancy
    tide_tendancy = ""
    if next_tide_in_epoch.get("tide_type") == "High":
        if delta_current_time_to_next < HALF_TIDE_SLACK_DURATION:
            tide_tendancy = "Tides Slack (Up)"
        elif previous_tide_in_epoch.get("error") is not None:
            # if the previous tide is not found, assume that
            # we are not in slack
            tide_tendancy = "Tides Up"
        elif delta_current_time_from_previous < HALF_TIDE_SLACK_DURATION:
            tide_tendancy = "Tides Slack (Up)"
        else:
            tide_tendancy = "Tides Up"
    else:
        if delta_current_time_to_next < HALF_TIDE_SLACK_DURATION:
            tide_tendancy = "Tides Slack (Down)"
        elif previous_tide_in_epoch.get("error") is not None:
            # if the previous tide is not found, assume that
            # we are not in slack
            tide_tendancy = "Tides Down"
        elif delta_current_time_from_previous < HALF_TIDE_SLACK_DURATION:
            tide_tendancy = "Tides Slack (Down)"
        else:
            tide_tendancy = "Tides Down"
    attr["tide_tendancy"] = f"{tide_tendancy}"

    return attr


def icon_tendancy(tide_info, current_time):
    """Compute icon based on tendancy"""
    attr = tide_tendancy_attribute(tide_info, current_time)
    icon = "mdi:shore"

    if attr.get("tide_tendancy") == "Tides Slack (Up)":
        icon = "mdi:chevron-up"
    elif attr.get("tide_tendancy") == "Tides Up":
        icon = "mdi:chevron-triple-up"
    elif attr.get("tide_tendancy") == "Tides Slack (Down)":
        icon = "mdi:chevron-down"
    elif attr.get("tide_tendancy") == "Tides Down":
        icon = "mdi:chevron-triple-down"
    else:
        icon = "mdi:shore"

    return icon


def schedule_time_attribute(worldtide_data_coordinator):
    """Compute attribute for time scheduler"""
    attr = {}

    schedule_time_result = worldtide_data_coordinator.get_schedule_time()
    # Time where are trigerred the request
    attr["Data_request_time"] = time.strftime(
        "%H:%M:%S %d/%m/%y",
        time.localtime(schedule_time_result.get("data_request_time")),
    )
    # KEEP FOR DEBUG:
    if DEBUG_FLAG:
        if schedule_time_result.get("previous_data_request_time") is not None:
            attr["Previous_Data_request_time"] = time.strftime(
                "%H:%M:%S %d/%m/%y",
                time.localtime(schedule_time_result.get("previous_data_request_time")),
            )
        else:
            attr["Previous_Data_request_time"] = 0
        attr["Init_data_request_time"] = time.strftime(
            "%H:%M:%S %d/%m/%y",
            time.localtime(schedule_time_result.get("init_data_request_time")),
        )
        attr["next day midnight"] = (
            schedule_time_result.get("next_day_midnight")
        ).strftime("%H:%M:%S %d/%m/%y")
        attr["next month midnight"] = (
            schedule_time_result.get("next_month_midnight")
        ).strftime("%H:%M:%S %d/%m/%y")

    return attr


def tide_station_attribute(
    current_lat,
    current_long,
    tide_station_name,
    worldtide_data_coordinator,
    init_tide_info,
    convert_km_to_miles,
):
    """Compute tide station attribute"""
    attr = {}

    # Tide detailed characteristic
    attr["station_distance"] = round(
        (worldtide_data_coordinator.get_server_parameter()).get_tide_station_distance()
        * convert_km_to_miles,
        ROUND_DISTANCE,
    )

    station_around = init_tide_info.give_station_around_info()
    if station_around.get("error") is None:
        attr["station_around_nb"] = station_around.get("station_around_nb")
        attr["station_around_name"] = station_around.get("station_around_name")
    else:
        attr["station_around_nb"] = 0
        attr["station_around_name"] = "No Station"

    tide_station_used_info = init_tide_info.give_used_station_info_from_name(
        tide_station_name
    )
    if tide_station_used_info.get("error") is None:
        attr["station_around_time_zone"] = tide_station_used_info.get(
            "tide_station_timezone"
        )
        attr["tidal_station_used_info_lat"] = tide_station_used_info.get(
            "tide_station_lat"
        )
        attr["tidal_station_used_info_long"] = tide_station_used_info.get(
            "tide_station_long"
        )
        if current_lat is not None and current_long is not None:
            attr["current_distance_to_station"] = round(
                distance_lat_long(
                    (current_lat, current_long),
                    (
                        float(tide_station_used_info.get("tide_station_lat")),
                        float(tide_station_used_info.get("tide_station_long")),
                    ),
                )
                * convert_km_to_miles,
                ROUND_DISTANCE,
            )
        else:
            attr["current_distance_to_station"] = "-"

    else:
        attr["station_around_time_zone"] = "-"
        attr["tidal_station_used_info_lat"] = "-"
        attr["tidal_station_used_info_long"] = "-"
        attr["current_distance_to_station"] = "-"

    return attr


def next_tide_state(tide_info, current_time):
    """Compute next tide state"""
    # Get next tide time
    next_tide = tide_info.give_next_tide_in_epoch(current_time)
    if next_tide.get("error") is None:
        tidetime = time.strftime("%H:%M", time.localtime(next_tide.get("tide_time")))
        tidetype = next_tide.get("tide_type")
        tide_string = f"{tidetype} tide at {tidetime}"
        return tide_string
    else:
        return None
