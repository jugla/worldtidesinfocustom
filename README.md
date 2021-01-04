# worldtidesinfocustom
world tides info custom component for [Home Assistant](https://home-assistant.io/).

This component is used to retrieve tide information for a dedicate location (all over the world) : [https://www.worldtides.info/](https://www.worldtides.info/)

This component allows to :
- display the tide curve (height)
- gives the current height
- gives the next tide

Refresh rate (Scan Interval) is every 15minutes with refresh of data from server every 12h

The service has to be paid. So the component :
- trigger, few times a day , a request to server : save bandwith and save credit

E.g. implementation request twice a day : 2*3=6 credits. 20000 credits will last ~9 years

From behaviour point of view it's an enhancement of the 
[integration worldtidesinfo](https://www.home-assistant.io/integrations/worldtidesinfo/) 

[![GitHub Release][releases-shield]][releases-link] [![GitHub Release Date][release-date-shield]][releases-link] [![GitHub Releases][latest-download-shield]][traffic-link] [![GitHub Releases][total-download-shield]][traffic-link]


## Installation
### [HACS](https://hacs.xyz/) (Home Assistant Community Store)  [NOT YET IMPLEMENTED]
1. Go to HACS page on your Home Assistant instance 
1. Select `integration` 
1. Press add icon and search for `worldtidesinfocustom` 
1. Select worldtidesinfocustom repo and install 
1. Force refresh the Home Assistant page (<kbd>Ctrl</kbd> + <kbd>F5</kbd>) 
1. Add worldtidesinfocustom to your page
### Manual
1. Download the folder worldtidesinfocustom from the latest [release](https://github.com/jugla/worldtidesinfocustom/releases) (with right click, save 
link as) 
1. Place the downloaded directory on your Home Assistant machine in the `config/custom_components` folder (when there is no `custom_components` folder in the 
folder where your `configuration.yaml` file is, create it and place the directory there) 
1. restart HomeAssistant
## Using the component
Get API key from https://www.worldtides.info/developer (buy prepaid)
In configuration.yaml, declare :
```yaml
sensor:
  - platform: worldtidesinfocustom
    name: royan_tides
    api_key: YOUR_API_KEY
    latitude: 45.61949378902948
    longitude: -1.0318721687376207
#    vertical_ref : LAT
#    scan_interval: 900
#    worldtides_request_interval: 43200

``` 
where :
- name is name of your sensor
- api_key is the key you get
- latitude, longiude is the place you want to see (hereabove Royan,France)

and  optional parameter
- vertical_ref : the reference you want to use for tide (default is LAT). See [datum ref](https://www.worldtides.info/datums)
- scan_interval : the scan rate to refresh entity (should not be use)
- worldtides_request_interval : the scan rate to fetch data on server (should not be use)

One entity is declared with attibutes. To see them as sensor, please follow the example
```yaml
sensor:
  - platform: template
    sensors:
      tide_royan_next_high:
        value_template: '{{ as_timestamp(states.sensor.royan_tides.attributes.high_tide_time_utc) | timestamp_custom("%a %d/%m/%Y %H:%M") }}'
        friendly_name: "Royan Next High Tide"
      tide_royan_next_low:
        value_template: '{{ as_timestamp(states.sensor.royan_tides.attributes.low_tide_time_utc) | timestamp_custom("%a %d/%m/%Y %H:%M") }}'
        friendly_name: "Royan Next Low Tide"
      tide_royan_next_high_height:
        value_template: "{{ state_attr('sensor.royan_tides','high_tide_height')  }}"
        friendly_name: "Royan Next High Tide Height"
        unit_of_measurement: m
      tide_royan_next_low_height:
        value_template: "{{ state_attr('sensor.royan_tides','low_tide_height')  }}"
        friendly_name: "Royan Next Low Tide Height"
        unit_of_measurement: m
      tide_royan_credit:
        value_template: "{{ state_attr('sensor.royan_tides','CreditCallUsed')  }}"
        friendly_name: "Royan Tide Credit"
        unit_of_measurement: credit
      tide_royan_current_height:
        value_template: "{{ state_attr('sensor.royan_tides','current_height')  }}"
        friendly_name: "Royan Tide Current Height"
        unit_of_measurement: m

## CAMERA
camera:
  - platform: generic
    name: Royan_tides_curve
    still_image_url: https://127.0.0.1:8123/local/royan_tides.png
    verify_ssl: false

```



## Wish/Todo list
- implement UI instead of YAML
- implement asychoneous instead of polling
- make this integration as default in home assistant

## Contact

## Thanks to

## Support
