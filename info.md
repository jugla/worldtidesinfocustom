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

Refresh rate (Scan Interval) is every 15minutes with refresh of data from server once a day

The request per day per location uses 3 credits.
So for one location: 20000 credits will last ~18 years

Please refer to [https://www.worldtides.info/developer](https://www.worldtides.info/developer) for pricing (as few requests are done per month, prepaid seems to be the best deal). 

From behaviour point of view it's an enhancement of the 
[integration worldtidesinfo](https://www.home-assistant.io/integrations/worldtidesinfo/) 

## Breaking change
**Version V2.6.1**: After this version, the information given is by default with unit system configured in HA (metric or imperial).
NB: Before the information given is by default in metric.

**Version V2.7.0**: After this version *Coeff* attribute is renamed in *Coeff_resp_MWS* . MWS = mean water spring
