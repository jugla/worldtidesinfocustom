#const (km)
MAX_DISTANCE_TO_CHANGE_REF = 10

from .const import  STATIC_CONF
import math

def distance(origin, destination):
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371 # km

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c

    return abs(d)

#class
class Live_Position_Management:
    #Management of Live Position

   def __init__(self, ref_lat, ref_long, live_position_management, source, source_attr_lat, source_attr_long):
        self._ref_lat = ref_lat
        self._ref_long = ref_long
        self._current_lat = None
        self._current_long = None
        self._max_distance_without_lat_long_update = MAX_DISTANCE_TO_CHANGE_REF
        self._live_position_management = live_position_management
        self._source_id = source
        self._source_attr_lat = source_attr_lat
        self._source_attr_long = source_attr_long

   def get_source_id (self):
        return self._source_id

   def get_lat_attribute (self):
        return self._source_attr_lat

   def get_long_attribute (self):
        return self._source_attr_long

   def get_current_lat (self):
       return self._current_lat

   def get_current_long (self):
       return self._current_long

   def get_ref_lat (self):
       return self._ref_lat

   def get_ref_long (self):
       return self._ref_long


   def get_live_position_management (self) :
       if self._live_position_management == None:
          return STATIC_CONF
       else:
          return self._live_position_management

   def need_to_change_ref(self,lat,long):
        if (distance ((self._ref_lat,self._ref_long),(lat,long)) > self._max_distance_without_lat_long_update):
           return True
        else:
           return False

   def update (self,lat,long):
        self._current_lat = lat
        self._current_long = long

   def change_ref (self,lat,long):
        self._ref_lat = lat
        self._ref_long = long

