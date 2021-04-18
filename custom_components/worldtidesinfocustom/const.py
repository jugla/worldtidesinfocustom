"""Constants for World Tide Info Custom integration."""

WORLD_TIDES_INFO_CUSTOM_DOMAIN = "worldtidesinfocustom"

ATTRIBUTION = "Data provided by WorldTides"

DEFAULT_NAME = "WorldTidesInfoCustom"

SCAN_INTERVAL_SECONDS = 900

# LAT reference as default
DEFAULT_VERTICAL_REF = "LAT"
CONF_VERTICAL_REF = "vertical_ref"

# in km/mile depending of unit used
DEFAULT_STATION_DISTANCE = 50
CONF_STATION_DISTANCE = "station_distance"

# plot color
DEFAULT_PLOT_COLOR = "2,102,255"
CONF_PLOT_COLOR = "plot_color"

# plot background
DEFAULT_PLOT_BACKGROUND = "255,255,255"
CONF_PLOT_BACKGROUND = "plot_background"

# www directory
WWW_PATH = "www"

# imperial conversion
CONF_UNIT = "unit"
METRIC_CONF_UNIT = "metric"
IMPERIAL_CONF_UNIT = "imperial"
HA_CONF_UNIT = "home_assistant"
DEFAULT_CONF_UNIT = HA_CONF_UNIT

# Debug Flag
DEBUG_FLAG = False

# Round height, distance, coeff
ROUND_HEIGTH = 3
ROUND_STATION_DISTANCE = 2
ROUND_COEFF = 1
