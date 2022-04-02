"""Calendar worldtides.info."""
# Python library
import logging

_LOGGER = logging.getLogger(__name__)

import os
import time
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv

# PyPy Library
import requests
import voluptuous as vol

# HA library
from homeassistant.components.calendar import PLATFORM_SCHEMA, CalendarEventDevice
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME, CONF_SOURCE
from homeassistant.helpers.entity_registry import async_get_registry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.unit_system import IMPERIAL_SYSTEM
from pyworldtidesinfo.worldtidesinfo_server import give_info_from_raw_data

# Component Library
from . import worldtidesinfo_data_coordinator
from .const import (
    CONF_LIVE_LOCATION,
    CONF_UNIT,
    DATA_COORDINATOR,
    DEFAULT_CONF_UNIT,
    DEFAULT_NAME,
    DOMAIN,
    HA_CONF_UNIT,
    IMPERIAL_CONF_UNIT,
    METRIC_CONF_UNIT,
    ROUND_HEIGTH,
    SCAN_INTERVAL_SECONDS,
    SENSOR_NEXT_TIDE_SUFFIX,
    STATIC_CONF,
)
from .sensor_service import convert_to_perform, get_tide_info, worldtidesinfo_unique_id

# Sensor HA parameter
SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_UNIT, default=DEFAULT_CONF_UNIT): cv.string,
    }
)


def setup_calendar_devices(
    hass,
    name,
    lat,
    lon,
    live_position_management,
    source,
    unit_to_display,
):
    """setup calendar"""
    unique_id = worldtidesinfo_unique_id(lat, lon, live_position_management, source)
    tides_calendar_device = TidesCalendarDevice(hass, name, unique_id, unit_to_display)

    return [tides_calendar_device]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the WorldTidesInfo Custom sensor."""

    # Get data from configuration.yaml
    name = config.get(CONF_NAME)

    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)

    live_position_management = STATIC_CONF
    source = None

    # what is the unit used
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    # what is the unit used
    tides_calendar_devices = setup_calendar_devices(
        hass,
        name,
        lat,
        lon,
        live_position_management,
        source,
        unit_to_display,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    add_entities(tides_calendar_devices)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up WorldTidesInfo sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][DATA_COORDINATOR][config_entry.entry_id]

    config = config_entry.data

    # Get data from config flow
    name = config.get(CONF_NAME)

    lat = config.get(CONF_LATITUDE)
    lon = config.get(CONF_LONGITUDE)

    live_position_management = config.get(CONF_LIVE_LOCATION)
    source = config.get(CONF_SOURCE)

    # what is the unit used
    if config.get(CONF_UNIT) == HA_CONF_UNIT and hass.config.units == IMPERIAL_SYSTEM:
        unit_to_display = IMPERIAL_CONF_UNIT
    elif config.get(CONF_UNIT) == IMPERIAL_CONF_UNIT:
        unit_to_display = IMPERIAL_CONF_UNIT
    else:
        unit_to_display = METRIC_CONF_UNIT

    tides_calendar_devices = setup_calendar_devices(
        hass,
        name,
        lat,
        lon,
        live_position_management,
        source,
        unit_to_display,
    )

    _LOGGER.debug(f"Launch fetching data available for this location: {name}")

    async_add_entities(tides_calendar_devices)


class TidesCalendarDevice(CalendarEventDevice):
    """A device for getting calendar events from entities."""

    def __init__(
        self,
        hass,
        name,
        unique_id,
        unit_to_display,
    ):
        """Initialize Curve Picture."""
        super().__init__()
        self._hass = hass

        # Parameters from configuration.yaml
        self._name = name

        # unique id  to retrieve sensor name
        self._unique_id = unique_id
        # entity
        self._main_entity = None

        # DATA
        self._event_data = TidesCalendarData(name, unit_to_display)

    def _async_worldtidesinfo_follower_sensor_state_listener(self, event):

        # retrieve state
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        self.schedule_update_ha_state(force_refresh=True)

    async def async_added_to_hass(self):
        """Handle added to Hass."""
        await super().async_added_to_hass()

        entity_id_main_sensor = None

        # Fetch the name of sensor
        registry = await async_get_registry(self.hass)
        entity_id_main_sensor = registry.async_get_entity_id(
            "sensor", DOMAIN, self._unique_id + SENSOR_NEXT_TIDE_SUFFIX
        )
        _LOGGER.debug("Calendar: entity main sensor %s", entity_id_main_sensor)

        if entity_id_main_sensor is None:
            entity_id_main_sensor = "sensor." + self._name + SENSOR_NEXT_TIDE_SUFFIX

        # for latter usage
        self._main_entity = entity_id_main_sensor

        async_track_state_change_event(
            self._hass,
            [entity_id_main_sensor],
            self._async_worldtidesinfo_follower_sensor_state_listener,
        )

        _LOGGER.debug("Event: listen main sensor %s", entity_id_main_sensor)
        # pure async i.e. wait for update of main sensor
        # no need to call self.schedule_update_ha_state
        # be robust to be sure to be update
        self.schedule_update_ha_state(force_refresh=True)

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._event_data.event

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    async def async_update(self):
        """Update all Calendars."""
        await self._event_data.async_update(self._main_entity)

    async def async_get_events(self, hass, start_date, end_date):
        """Get all events in a specific time frame."""
        return await self._event_data.async_get_events(self._main_entity, start_date, end_date)


class TidesCalendarData:
    """
    Class used by the Entities Calendar Device service object to handle all entity events.
    """

    def __init__(
        self,
        name,
        unit_to_display,
    ):
        """Initialize an Entities Calendar Project."""
        self.event = None

        self._name = name
        self._unit_to_display = unit_to_display

        convert_meter_to_feet, convert_km_to_miles = convert_to_perform(
            self._unit_to_display
        )
        self._convert_meter_to_feet = convert_meter_to_feet

        if self._unit_to_display == IMPERIAL_CONF_UNIT:
            self._measurement_unit = "ft"
        else:
            self._measurement_unit = "m"

    async def async_get_events(self, entity, start_date, end_date):
        """Get all tasks in a specific time frame."""
        events = []

        worldtide_data_coordinator = worldtidesinfo_data_coordinator.get(self._name)
        if worldtide_data_coordinator is None:
            return events

        # the tide info
        tide_info = give_info_from_raw_data(
            worldtide_data_coordinator.get_data().get("current_data")
        )
        epoch_frame_min = start_date.timestamp()
        epoch_frame_max = end_date.timestamp()

        extrema_data = tide_info.give_tide_extrema_within_time_frame(
            epoch_frame_min, epoch_frame_max
        )

        for index in range(len(extrema_data.get("extrema_epoch"))):
            tide_epoch = datetime.fromtimestamp(
                extrema_data.get("extrema_epoch")[index]
            )
            tide_height = extrema_data.get("extrema_value")[index]
            tide_type = extrema_data.get("extrema_type")[index]
            event = {
                "uid": entity,
                "summary": self._name
                + " "
                + str(tide_type)
                + " "
                + str(round(tide_height * self._convert_meter_to_feet, ROUND_HEIGTH))
                + self._measurement_unit,
                "start": {"date": tide_epoch.strftime("%Y-%m-%d %H:%M")},
                "end": {"date": tide_epoch.strftime("%Y-%m-%d %H:%M")},
                "allDay": False,
            }
            events.append(event)

        return events

    async def async_update(self, entity):
        """Get the latest data."""
        self.event = None

        worldtide_data_coordinator = worldtidesinfo_data_coordinator.get(self._name)
        if worldtide_data_coordinator is None:
            return
        # the tide info
        tide_info = give_info_from_raw_data(
            worldtide_data_coordinator.get_data().get("current_data")
        )
        if tide_info is None:
            return
        current_time = time.time()
        next_tide_data = tide_info.give_next_high_low_tide_in_UTC(current_time)
        if next_tide_data.get("error"):
            return

        if next_tide_data.get("high_tide_time_epoch") > next_tide_data.get(
            "low_tide_time_epoch"
        ):
            tide_epoch = datetime.fromtimestamp(
                next_tide_data.get("low_tide_time_epoch")
            )
            tide_height = next_tide_data.get("low_tide_height")
            tide_type = "Low"
        else:
            tide_epoch = datetime.fromtimestamp(
                next_tide_data.get("high_tide_time_epoch")
            )
            tide_height = next_tide_data.get("high_tide_height")
            tide_type = "High"

        _LOGGER.debug(
            "Tide Calendar %s EpochFound event: %s",
            self._name,
            str(tide_epoch),
        )

        event = {
            "uid": entity,
            "summary": self._name
            + " "
            + str(tide_type)
            + " "
            + str(round(tide_height * self._convert_meter_to_feet, ROUND_HEIGTH))
            + self._measurement_unit,
            "start": {"date": tide_epoch.strftime("%Y-%m-%d %H:%M")},
            "end": {"date": tide_epoch.strftime("%Y-%m-%d %H:%M")},
            "allDay": False,
        }

        _LOGGER.debug(
            "Tide Calendar %s Found event: %s",
            self._name,
            str(event),
        )

        self.event = event
