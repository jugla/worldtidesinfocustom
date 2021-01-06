# worldtidesinfocustom
world tides info custom component for [Home Assistant](https://home-assistant.io/).

This component is used to retrieve tide information for a dedicate location (all over the world) : [https://www.worldtides.info/](https://www.wor
ldtides.info/)

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

