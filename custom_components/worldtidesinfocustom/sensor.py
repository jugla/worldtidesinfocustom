"""Sensor worldtides.info."""
# Python library
import logging

_LOGGER = logging.getLogger(__name__)

import time
from datetime import datetime, timedelta

# HA library
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_SHOW_ON_MAP,
    CONF_SOURCE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.entity import Entity

# HA library
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

# Component Library
from . import give_persistent_filename, worldtidesinfo_data_coordinator

# Live Position Management
from .basic_service import distance_lat_long
from .const import (
    ATTR_REF_LAT,
    ATTR_REF_LONG,
    ATTRIBUTION,
    CONF_ATTRIBUTE_NAME_LAT,
    CONF_ATTRIBUTE_NAME_LONG,
    CONF_LIVE_LOCATION,
    CONF_PLOT_BACKGROUND,
    CONF_PLOT_COLOR,
    CONF_SENSOR_UPDATE_DISTANCE,
    CONF_STATION_DISTANCE,
    CONF_UNIT,
    CONF_VERTICAL_REF,
    DATA_COORDINATOR,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DEFAULT_PLOT_BACKGROUND,
    DEFAULT_PLOT_COLOR,
    DEFAULT_SENSOR_UPDATE_DISTANCE,
    DEFAULT_STATION_DISTANCE,
    DEFAULT_VERTICAL_REF,
    DOMAIN,
    FROM_SENSOR_CONF,
    HA_CONF_UNIT,
    IMPERIAL_CONF_UNIT,
    METRIC_CONF_UNIT,
    ROUND_DISTANCE,
    SCAN_INTERVAL_SECONDS,
    SENSOR_CREDIT_USED_SUFFIX,
    SENSOR_CURRENT_TIDE_AMPLITUDE_SUFFIX,
    SENSOR_CURRENT_TIDE_COEFF_RESP_MWS_SUFFIX,
    SENSOR_CURRENT_TIDE_HEIGHT_SUFFIX,
    SENSOR_GLOBAL_CREDIT_USED_SUFFIX,
    SENSOR_NEXT_HIGH_TIDE_HEIGHT_SUFFIX,
    SENSOR_NEXT_HIGH_TIDE_TIME_SUFFIX,
    SENSOR_NEXT_LOW_TIDE_HEIGHT_SUFFIX,
    SENSOR_NEXT_LOW_TIDE_TIME_SUFFIX,
    SENSOR_NEXT_TIDE_SUFFIX,
    SENSOR_REMAINING_TIME_FOR_NEXT_TIDE_SUFFIX,
    STATIC_CONF,
    WORLD_TIDES_INFO_CUSTOM_DOMAIN,
)

# Live Position Management
from .live_position_management import Live_Position_Management

# import .storage_mngt
from .py_worldtidesinfo import (
    SERVER_API_VERSION,
    give_info_from_raw_data,
    give_info_from_raw_data_N_and_N_1,
    give_info_from_raw_datums_data,
)

# sensor_service
from .sensor_service import (
    convert_to_perform,
    current_amplitude_attribute,
    current_amplitude_state,
    current_coeff_state,
    current_height_attribute,
    current_height_state,
    get_all_tide_info,
    get_tide_info,
    get_tide_info_and_offset,
    give_unit_attribute,
    icon_tendancy,
    next_amplitude_attribute,
    next_high_tide_height_state,
    next_high_tide_time_state,
    next_low_tide_height_state,
    next_low_tide_time_state,
    next_tide_attribute,
    next_tide_state,
    remaining_time_to_next_tide,
    schedule_time_attribute,
    tide_station_attribute,
    tide_tendancy_attribute,
    worldtidesinfo_unique_id,
)
from .server_request_scheduler import WorldTidesInfo_server_scheduler
from .storage_mngt import File_Data_Cache, File_Picture

# WorlTidesDataCoordinator
from .worldtides_data_coordinator import WordTide_Data_Coordinator

# Sensor HA parameter
SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)

# override HA behaviour no parallelism during update
PARALLEL_UPDATES = 1

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_VERTICAL_REF, default=DEFAULT_VERTICAL_REF): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(
            CONF_STATION_DISTANCE,
            default=DEFAULT_STATION_DISTANCE,
        ): cv.positive_int,
        vol.Optional(CONF_PLOT_COLOR, default=DEFAULT_PLOT_COLOR): cv.string,
        vol.Optional(CONF_PLOT_BACKGROUND, default=DEFAULT_PLOT_BACKGROUND): cv.string,
        vol.Optional(CONF_UNIT, default=DEFAULT_CONF_UNIT): cv.string,
    }
)


def format_receive_value(value):
    """format if pb then return None"""
    if value == None or value == STATE_UNKNOWN:
        return None
    else:
        return float(value)


def setup_sensor(
    hass,
    name,
    lat,
    lon,
    key,
    vertical_ref,
    plot_color,
    plot_background,
    tide_station_distance,
    unit_to_display,
    show_on_map,
    live_position_management,
    live_position_sensor_update_distance,
    source,
    source_attr_lat,
    source_attr_long,
):
    """setup sensor with server, server scheduler in async or sync configuration"""
    unique_id = worldtidesinfo_unique_id(lat, lon, live_position_management, source)

    live_position_management = Live_Position_Management(
        lat,
        lon,
        live_position_management,
        live_position_sensor_update_distance,
        unit_to_display,
        source,
        source_attr_lat,
        source_attr_long,
    )

    worldtide_data_coordinator = WordTide_Data_Coordinator(
        hass,
        name,
        lat,
        lon,
        key,
        vertical_ref,
        plot_color,
        plot_background,
        tide_station_distance,
        unit_to_display,
    )
    worldtidesinfo_data_coordinator[name] = worldtide_data_coordinator

    # create the sensor
    tides = WorldTidesInfoCustomSensor(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    # create height
    tides_current_height = WorldTidesInfoCustomSensorCurrentHeight(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    # next tide
    tides_next_low_tide_height = WorldTidesInfoCustomSensorNextLowTideHeight(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_next_low_tide_time = WorldTidesInfoCustomSensorNextLowTideTime(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_next_high_tide_height = WorldTidesInfoCustomSensorNextHighTideHeight(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_next_high_tide_time = WorldTidesInfoCustomSensorNextHighTideTime(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_next_remaining_time = WorldTidesInfoCustomSensorNextRemainingTideTime(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    # amplitude
    tides_current_amplitude = WorldTidesInfoCustomSensorCurrentAmplitude(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_current_coeff_resp_MWS = WorldTidesInfoCustomSensorCurrentCoeffMWS(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    # create credit used
    tides_credit_used = WorldTidesInfoCustomSensorCreditUsed(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    tides_global_credit_used = WorldTidesInfoCustomSensorGlobalCreditUsed(
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    )

    return [
        tides,
        tides_current_height,
        tides_next_low_tide_height,
        tides_next_low_tide_time,
        tides_next_high_tide_height,
        tides_next_high_tide_time,
        tides_next_remaining_time,
        tides_current_amplitude,
        tides_current_coeff_resp_MWS,
        tides_credit_used,
        tides_global_credit_used,
    ]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""

    # Get data from configuration.yaml
    name = config.get(CONF_NAME)
    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)

    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return

    key = config.get(CONF_API_KEY)
    vertical_ref = config.get(CONF_VERTICAL_REF)
    plot_color = config.get(CONF_PLOT_COLOR)
    plot_background = config.get(CONF_PLOT_BACKGROUND)
    # worldides_request_interval = config.get(CONF_WORLDTIDES_REQUEST_INTERVAL)
    tide_station_distance = config.get(CONF_STATION_DISTANCE)

    # what is the unit used
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    show_on_map = True

    live_position_management = STATIC_CONF
    live_position_sensor_update_distance = DEFAULT_SENSOR_UPDATE_DISTANCE
    source = None
    source_attr_lat = None
    source_attr_long = None

    tides_sensors = setup_sensor(
        hass,
        name,
        lat,
        lon,
        key,
        vertical_ref,
        plot_color,
        plot_background,
        tide_station_distance,
        unit_to_display,
        show_on_map,
        live_position_management,
        live_position_sensor_update_distance,
        source,
        source_attr_lat,
        source_attr_long,
    )

    for tides in tides_sensors:
        tides.update()
        if tides._worldtide_data_coordinator.no_data():
            _LOGGER.error(f"No data available for this location: {name}")
            return

    add_entities(tides_sensors)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up WorldTidesInfo sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][DATA_COORDINATOR][config_entry.entry_id]
    unique_id = config_entry.unique_id

    config = config_entry.data

    # Get data from config flow
    name = config.get(CONF_NAME)
    lat = config.get(CONF_LATITUDE)
    lon = config.get(CONF_LONGITUDE)

    # shall not occur
    if None in (lat, lon):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return

    key = config.get(CONF_API_KEY)
    vertical_ref = config.get(CONF_VERTICAL_REF)
    plot_color = config.get(CONF_PLOT_COLOR)
    plot_background = config.get(CONF_PLOT_BACKGROUND)
    tide_station_distance = config.get(CONF_STATION_DISTANCE)

    # what is the unit used
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    if config_entry.options[CONF_SHOW_ON_MAP]:
        show_on_map = True
    else:
        show_on_map = False

    live_position_management = config.get(CONF_LIVE_LOCATION)
    live_position_sensor_update_distance = config.get(CONF_SENSOR_UPDATE_DISTANCE)
    source = config.get(CONF_SOURCE)
    source_attr_lat = config.get(CONF_ATTRIBUTE_NAME_LAT)
    source_attr_long = config.get(CONF_ATTRIBUTE_NAME_LONG)

    tides_sensors = setup_sensor(
        hass,
        name,
        lat,
        lon,
        key,
        vertical_ref,
        plot_color,
        plot_background,
        tide_station_distance,
        unit_to_display,
        show_on_map,
        live_position_management,
        live_position_sensor_update_distance,
        source,
        source_attr_lat,
        source_attr_long,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    for tides in tides_sensors:
        await tides.async_update()

        if tides._worldtide_data_coordinator.no_data():
            _LOGGER.error(f"No data available for this location: {name}")
            return

    async_add_entities(tides_sensors)


class WorldTidesInfoCustomSensorGeneric(SensorEntity):
    """Representation of a WorldTidesInfo sensor."""

    def __init__(
        self,
        hass,
        name,
        unit_to_display,
        show_on_map,
        worldtide_data_coordinator,
        live_position_management,
        unique_id,
    ):
        """Initialize the sensor."""

        self._hass = hass
        # Parameters from configuration.yaml
        self._name = name
        self._unit_to_display = unit_to_display
        self._show_on_map = show_on_map

        # DATA
        self._worldtide_data_coordinator = worldtide_data_coordinator
        self._live_position_management = live_position_management

        self._unique_id = unique_id

    # Name : to be defined by class
    # unit_of_measurement : to be defined by class
    # device_state_attributes : to be defined by class

    @property
    def device_info(self):
        """Device info for WorldTideInfo Server."""
        return {
            "identifiers": {(DOMAIN, self._unique_id)},
            "manufacturer": "WorldTidesInfo",
            "sw_version": SERVER_API_VERSION,
            "name": self._name + "_server",
            "model": "WorldTidesInfoAPI",
            "entry_type": "service",
        }

    @property
    def icon(self):
        """return icon tendancy"""
        current_time = time.time()
        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        return icon_tendancy(tide_info, current_time)

    # state : to be defined by class

    async def async_update(self):
        """Fetch new state data for this sensor."""
        _LOGGER.debug("Async Update Tides sensor %s", self._name)
        # Watch Out : only method name is given to function i.e. without ()
        await self._hass.async_add_executor_job(self.update)

    def update(self):
        """Update of sensors."""
        # Only one sensor has the liability to update
        return


class WorldTidesInfoCustomSensorCurrentHeight(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_CURRENT_TIDE_HEIGHT_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_CURRENT_TIDE_HEIGHT_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            return "ft"
        else:
            return "m"

    @property
    def state_class(self):
        """Return the state class for long term statistics."""
        _LOGGER.debug(
            "StateClass Tides sensor %s %s", self._name, STATE_CLASS_MEASUREMENT
        )
        return STATE_CLASS_MEASUREMENT

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # The height
        attr.update(
            current_height_attribute(tide_info, current_time, convert_meter_to_feet)
        )

        return attr

    @property
    def state(self):
        """Return the state of the device."""

        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # The height
        return current_height_state(tide_info, current_time, convert_meter_to_feet)


class WorldTidesInfoCustomSensorNextLowTideHeight(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_NEXT_LOW_TIDE_HEIGHT_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_NEXT_LOW_TIDE_HEIGHT_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            return "ft"
        else:
            return "m"

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next tide
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = 0
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next low tide Height
        state_value = next_low_tide_height_state(
            tide_info, current_time, convert_meter_to_feet
        )
        return state_value


class WorldTidesInfoCustomSensorNextLowTideTime(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_NEXT_LOW_TIDE_TIME_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_NEXT_LOW_TIDE_TIME_SUFFIX

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next tide
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = ""
        current_time = time.time()

        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next low tide time
        state_value = next_low_tide_time_state(tide_info, current_time)
        return state_value


class WorldTidesInfoCustomSensorNextHighTideHeight(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_NEXT_HIGH_TIDE_HEIGHT_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_NEXT_HIGH_TIDE_HEIGHT_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            return "ft"
        else:
            return "m"

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next tide
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = 0
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next low tide Height
        state_value = next_high_tide_height_state(
            tide_info, current_time, convert_meter_to_feet
        )

        return state_value


class WorldTidesInfoCustomSensorNextHighTideTime(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_NEXT_HIGH_TIDE_TIME_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_NEXT_HIGH_TIDE_TIME_SUFFIX

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next tide
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = ""
        current_time = time.time()

        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next high tide time
        state_value = next_high_tide_time_state(tide_info, current_time)
        return state_value


class WorldTidesInfoCustomSensorNextRemainingTideTime(
    WorldTidesInfoCustomSensorGeneric
):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_REMAINING_TIME_FOR_NEXT_TIDE_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_REMAINING_TIME_FOR_NEXT_TIDE_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "h"

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Next tide
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        current_time = time.time()
        state_value = 0

        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # Compute remainig time
        state_value = remaining_time_to_next_tide(tide_info, current_time)
        return state_value


class WorldTidesInfoCustomSensorCurrentAmplitude(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_CURRENT_TIDE_AMPLITUDE_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_CURRENT_TIDE_AMPLITUDE_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            return "ft"
        else:
            return "m"

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info : coeff and amplitude
        tide_info, datums_info = get_tide_info_and_offset(
            self._worldtide_data_coordinator
        )
        attr.update(
            current_amplitude_attribute(
                tide_info, datums_info, current_time, convert_meter_to_feet
            )
        )

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = 0
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info : amplitude
        tide_info, datums_info = get_tide_info_and_offset(
            self._worldtide_data_coordinator
        )
        state_value = current_amplitude_state(
            tide_info, datums_info, current_time, convert_meter_to_feet
        )

        return state_value


class WorldTidesInfoCustomSensorCurrentCoeffMWS(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_CURRENT_TIDE_COEFF_RESP_MWS_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_CURRENT_TIDE_COEFF_RESP_MWS_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "%"

    @property
    def state_class(self):
        """Return the state class for long term statistics."""
        _LOGGER.debug(
            "StateClass Tides sensor %s %s", self._name, STATE_CLASS_MEASUREMENT
        )
        return STATE_CLASS_MEASUREMENT

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info: compute amplitude and coeff
        tide_info, datums_info = get_tide_info_and_offset(
            self._worldtide_data_coordinator
        )
        attr.update(
            current_amplitude_attribute(
                tide_info, datums_info, current_time, convert_meter_to_feet
            )
        )

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        state_value = 0
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        if self._worldtide_data_coordinator.no_data():
            return state_value

        # the tide info : coeff
        tide_info, datums_info = get_tide_info_and_offset(
            self._worldtide_data_coordinator
        )
        state_value = current_coeff_state(
            tide_info, datums_info, current_time, convert_meter_to_feet
        )

        return state_value


class WorldTidesInfoCustomSensorCreditUsed(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_CREDIT_USED_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_CREDIT_USED_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "credit"

    @property
    def state(self):
        """Return the state of the device."""
        # The credit used to display the update
        return self._worldtide_data_coordinator.get_credit_used()

    @property
    def icon(self):
        """return icon tendancy"""
        return "mdi:credit-card-check-outline"


class WorldTidesInfoCustomSensorGlobalCreditUsed(WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_GLOBAL_CREDIT_USED_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_GLOBAL_CREDIT_USED_SUFFIX

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "credit"

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {}

        # managment of global count :  give all locations
        monitored_location = ""
        for name, coordinator in worldtidesinfo_data_coordinator.items():
            monitored_location = monitored_location + "," + name
        attr["monitored_location"] = monitored_location

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        # The credit used to display the update
        return self._worldtide_data_coordinator.overall_count

    @property
    def icon(self):
        """return icon tendancy"""
        return "mdi:credit-card-multiple-outline"


class WorldTidesInfoCustomSensor(RestoreEntity, WorldTidesInfoCustomSensorGeneric):
    """Representation of a WorldTidesInfo sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + SENSOR_NEXT_TIDE_SUFFIX

    @property
    def unique_id(self):
        return self._unique_id + SENSOR_NEXT_TIDE_SUFFIX

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {ATTR_ATTRIBUTION: ATTRIBUTION}
        current_time = time.time()
        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )

        # Unit system
        attr.update(give_unit_attribute(self._unit_to_display))

        if self._worldtide_data_coordinator.no_data():
            return attr

        # the tide info
        tide_info, datums_info, init_tide_info = get_all_tide_info(
            self._worldtide_data_coordinator
        )

        # The vertical reference used : LAT, ...
        vertical_ref = tide_info.give_vertical_ref()
        if vertical_ref.get("error") == None:
            attr["vertical_reference"] = vertical_ref.get("vertical_ref")
        else:
            attr["vertical_reference"] = "No vertical ref"

        # Tide station characteristics
        tide_station_used = tide_info.give_tidal_station_used()
        tide_station_name = None
        if tide_station_used.get("error") == None:
            tide_station_name = tide_station_used.get("station")
            attr["tidal_station_used"] = tide_station_name
        else:
            attr["tidal_station_used"] = "No Tide station used"

        # Next tide : height and time
        attr.update(next_tide_attribute(tide_info, current_time, convert_meter_to_feet))

        # Tide Tendancy and time_to_next_tide
        attr.update(tide_tendancy_attribute(tide_info, current_time))

        # Next Amplitude , Coeff
        attr.update(
            next_amplitude_attribute(
                tide_info, datums_info, current_time, convert_meter_to_feet
            )
        )

        # The height
        attr.update(
            current_height_attribute(tide_info, current_time, convert_meter_to_feet)
        )

        # Current Amplitude , Coeff
        attr.update(
            current_amplitude_attribute(
                tide_info, datums_info, current_time, convert_meter_to_feet
            )
        )

        # The credit used to display the update
        attr["CreditCallUsed"] = self._worldtide_data_coordinator.get_credit_used()

        # Time where are trigerred the request
        attr.update(schedule_time_attribute(self._worldtide_data_coordinator))

        # Filename of tide picture
        attr["plot"] = self._worldtide_data_coordinator.get_curve_filename()

        # Tide detailed characteristic
        attr.update(
            tide_station_attribute(
                self._live_position_management.get_current_lat(),
                self._live_position_management.get_current_long(),
                tide_station_name,
                self._worldtide_data_coordinator,
                init_tide_info,
                convert_km_to_miles,
            )
        )

        # Displaying the geography on the map relies upon putting the latitude/longitude
        # in the entity attributes with "latitude" and "longitude" as the keys.
        if self._show_on_map:
            attr[ATTR_LATITUDE] = (
                self._worldtide_data_coordinator.get_server_parameter()
            ).get_latitude()
            attr[ATTR_LONGITUDE] = (
                self._worldtide_data_coordinator.get_server_parameter()
            ).get_longitude()

        ## Moving sensor or not
        attr[
            "live_location"
        ] = self._live_position_management.get_live_position_management()
        attr["source_id"] = self._live_position_management.get_source_id()
        attr[ATTR_REF_LAT] = self._live_position_management.get_ref_lat()
        attr[ATTR_REF_LONG] = self._live_position_management.get_ref_long()
        attr["current_lat"] = self._live_position_management.get_current_lat()
        attr["current_long"] = self._live_position_management.get_current_long()
        attr["distance_from_ref"] = round(
            self._live_position_management.give_distance_from_ref_point()
            * convert_km_to_miles,
            ROUND_DISTANCE,
        )

        return attr

    @property
    def state(self):
        """Return the state of the device."""
        current_time = time.time()
        # the tide info
        tide_info = get_tide_info(self._worldtide_data_coordinator)
        # give next tide
        return next_tide_state(tide_info, current_time)

    def _async_worldtidesinfo_sensor_state_listener(self, event):
        """Handle sensor state changes."""
        _LOGGER.info("World Tide Update state %s", event.data.get("new_state"))

        new_state_valid = False
        lat = None
        long = None
        # retrieve state
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        try:
            lat = float(
                new_state.attributes.get(
                    self._live_position_management.get_lat_attribute()
                )
            )
            long = float(
                new_state.attributes.get(
                    self._live_position_management.get_long_attribute()
                )
            )
            new_state_valid = True

            _LOGGER.info(
                "World Tide Update %s : lat %s, long %s",
                self._live_position_management.get_source_id(),
                self._live_position_management.get_lat_attribute(),
                self._live_position_management.get_long_attribute(),
            )

        except (ValueError, TypeError):
            _LOGGER.warning(
                "%s : lat %s, long %s is not numerical",
                self._live_position_management.get_source_id(),
                self._live_position_management.get_lat_attribute(),
                self._live_position_management.get_long_attribute(),
            )

        if new_state_valid == True:
            self._live_position_management.update(lat, long)

            # check if too far from former point
            if self._live_position_management.need_to_change_ref(lat, long):
                self._worldtide_data_coordinator.change_reference_point(lat, long)
                self._live_position_management.change_ref(lat, long)
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Handle added to Hass."""
        await super().async_added_to_hass()

        previous_ref_lat = None
        previous_ref_long = None
        state_recorded = await self.async_get_last_state()
        if state_recorded:
            previous_ref_lat = format_receive_value(
                state_recorded.attributes.get(ATTR_REF_LAT)
            )
            previous_ref_long = format_receive_value(
                state_recorded.attributes.get(ATTR_REF_LONG)
            )
            self._worldtide_data_coordinator.change_reference_point(
                previous_ref_lat, previous_ref_long
            )
            self._live_position_management.change_ref(
                previous_ref_lat, previous_ref_long
            )

        # listen to source ID
        if (
            self._live_position_management.get_live_position_management()
            == FROM_SENSOR_CONF
        ):

            _LOGGER.info(
                "World Tide add listener %s",
                self._live_position_management.get_source_id(),
            )

            async_track_state_change_event(
                self.hass,
                [self._live_position_management.get_source_id()],
                self._async_worldtidesinfo_sensor_state_listener,
            )

    def update(self):
        """Update of sensors."""
        _LOGGER.debug("Sync Update Tides sensor %s", self._name)
        self._worldtide_data_coordinator.update_server_data()

        # managment of global count
        for name, coordinator in worldtidesinfo_data_coordinator.items():
            coordinator.overall_count_tmp = (
                coordinator.overall_count_tmp
                + self._worldtide_data_coordinator.get_credit_used()
            )

        self._worldtide_data_coordinator.overall_count = (
            self._worldtide_data_coordinator.overall_count_tmp
        )
        self._worldtide_data_coordinator.overall_count_tmp = 0
