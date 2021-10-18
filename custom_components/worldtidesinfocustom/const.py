"""Constants for World Tide Info Custom integration."""

WORLD_TIDES_INFO_CUSTOM_DOMAIN = "worldtidesinfocustom"
DOMAIN = WORLD_TIDES_INFO_CUSTOM_DOMAIN

ATTRIBUTION = "Data provided by WorldTides"

DEFAULT_NAME = "WorldTidesInfoCustom"

SCAN_INTERVAL_SECONDS = 900

DATA_COORDINATOR = "coordinator"

# LAT reference as default
DEFAULT_VERTICAL_REF = "LAT"
CONF_VERTICAL_REF = "vertical_ref"

# All vertical ref available from worldtides server
CONF_VERTICAL_REF_TYPES = [
    "LAT",
    "MLLWS",
    "MLWS",
    "MHLWS",
    "MLLW",
    "MLW",
    "MHLW",
    "MLLWN",
    "MLWN",
    "MHLWN",
    "MTL",
    "MSL",
    "MLHWN",
    "MHWN",
    "MHHWN",
    "MLHW",
    "MHW",
    "MHHW",
    "MLHWS",
    "MHWS",
    "MHHWS",
    "HAT",
    "NAVD",
    "STND",
    "CD",
    "NN1954",
    "NN2000",
]

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
CONF_UNIT_TYPES = [HA_CONF_UNIT, METRIC_CONF_UNIT, IMPERIAL_CONF_UNIT]

# external GPS location
CONF_ATTRIBUTE_NAME_LAT = "latitude_attr_name"
CONF_ATTRIBUTE_NAME_LONG = "longitude_attr_name"
DEFAULT_CONF_ATTRIBUTE_NAME_LAT = "latitude"
DEFAULT_CONF_ATTRIBUTE_NAME_LONG = "longitude"
CONF_LIVE_LOCATION = "live_location"
STATIC_CONF = "static"
FROM_SENSOR_CONF = "from_sensor"
DEFAULT_CONF_LIVE_LOCATION = STATIC_CONF
CONF_LIVE_LOCATION_TYPES = [STATIC_CONF, FROM_SENSOR_CONF]

# in km/mile depending of unit used
DEFAULT_SENSOR_UPDATE_DISTANCE = 50
CONF_SENSOR_UPDATE_DISTANCE = "update_sensor_distance"


# Debug Flag
DEBUG_FLAG = False

# Round height, distance, coeff
ROUND_HEIGTH = 3
ROUND_STATION_DISTANCE = 2
ROUND_COEFF = 1
ROUND_SEC = 0
ROUND_HOUR = 2

# Half Tide Slack Duration in seconds
HALF_TIDE_SLACK_DURATION = 3600

# set constant to give suffix to camera and sensor name
CAMERA_PLOT_PICTURE_SUFFIX = "_plot_picture"
CAMERA_CURVE_PICTURE_SUFFIX = "_curve_picture"
SENSOR_CURRENT_TIDE_HEIGHT_SUFFIX = "_current_tide_height"
SENSOR_NEXT_LOW_TIDE_HEIGHT_SUFFIX = "_next_low_tide_height"
SENSOR_NEXT_LOW_TIDE_TIME_SUFFIX = "_next_low_tide_time"
SENSOR_NEXT_HIGH_TIDE_HEIGHT_SUFFIX = "_next_high_tide_height"
SENSOR_NEXT_HIGH_TIDE_TIME_SUFFIX = "_next_high_tide_time"
SENSOR_REMAINING_TIME_FOR_NEXT_TIDE_SUFFIX = "_remaining_time_for_next_tide"
SENSOR_CURRENT_TIDE_AMPLITUDE_SUFFIX = "_current_tide_amplitude"
SENSOR_CURRENT_TIDE_COEFF_RESP_MWS_SUFFIX = "_current_tide_coeff_resp_MWS"
SENSOR_CREDIT_USED_SUFFIX = "_credit_used"
SENSOR_GLOBAL_CREDIT_USED_SUFFIX = "_global_credit_used"
SENSOR_NEXT_TIDE_SUFFIX = ""
