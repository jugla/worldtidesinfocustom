# worldtidesinfocustom
## Description
world tides info custom component for [Home Assistant](https://home-assistant.io/).


![GitHub release](https://img.shields.io/github/release/jugla/worldtidesinfocustom)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

This component is used to retrieve tide information for a dedicated location (all over the world) : [https://www.worldtides.info/](https://www.worldtides.info/)

This component allows to :
- display the tide curve (height)
- give the current height
- give the next tide
- give tide tendancy, amplitude
- display location on default map
- display tide prediction over user defined period
- add calendar to monitor tide extrema (over user defined period)

==> the monitored location is either static, either given by GPS data (tracker)

In static, refresh rate (Scan Interval) is every 15minutes with refresh of data from server once a day

In motion, refresh rate (Scan Interval) is every 15minutes with refresh of data from server once a day, or if the position has moved more than a user parameter defined in UI

## Other information
Detail information on use, breaking change, example are given at [worldtidesinfocustom repository](https://github.com/jugla/worldtidesinfocustom)
