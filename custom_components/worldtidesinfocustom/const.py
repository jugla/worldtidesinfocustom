"""Constants for World Tide Info Custom integration."""

WORLD_TIDES_INFO_CUSTOM_DOMAIN = "worldtidesinfocustom"

ATTRIBUTION = "Data provided by WorldTides"

DEFAULT_NAME = "WorldTidesInfoCustom"

SCAN_INTERVAL_SECONDS = 900

"""set 25h """
DEFAULT_WORLDTIDES_REQUEST_INTERVAL = 90000
CONF_WORLDTIDES_REQUEST_INTERVAL = "worldtides_request_interval"

"""fetch init every 30 days"""
FORCE_FETCH_INIT_DATA = 30

"""LAT reference as default"""
DEFAULT_VERTICAL_REF = "LAT"
CONF_VERTICAL_REF = "vertical_ref"

"""in km"""
DEFAULT_STATION_DISTANCE = 50
CONF_STATION_DISTANCE = "station_distance"

"""plot color"""
DEFAULT_PLOT_COLOR = "2,102,255"
CONF_PLOT_COLOR = "plot_color"

"""plot background"""
DEFAULT_PLOT_BACKGROUND = "255,255,255"
CONF_PLOT_BACKGROUND = "plot_background"
