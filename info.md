# worldtidesinfocustom
world tides info custom component for [Home Assistant](https://home-assistant.io/).


![GitHub release](https://img.shields.io/github/release/jugla/worldtidesinfocustom)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)


This component is used to retrieve tide information for a dedicate location (all over the world) : [https://www.worldtides.info/](https://www.worldtides.info/)

This component allows to :
- display the tide curve (height)
- gives the current height
- gives the next tide

Refresh rate (Scan Interval) is every 15minutes with refresh of data from server once a day

The service has to be paid. So the component :
- trigger, few times a day , a request to server : save bandwith and save credit

E.g. implementation request once a day per location: 1*3=6 credits. 20000 credits will last ~18 years

From behaviour point of view it's an enhancement of the 
[integration worldtidesinfo](https://www.home-assistant.io/integrations/worldtidesinfo/) 


