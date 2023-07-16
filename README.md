# OctoPrint FHEM Temp
Adds temperature readings from FHEM (e.g. from an external climate control module) to OctoPrint.
You'll need an extra visualizer to visualize readings aquired by the `octoprint.comm.protocol.temperatures.received` callback,
like [OctoPrint-PlotlyTempGraph](??) as those readings will **not** show up in the default temp graph.

## Setup
- Install the plugin using
  `pip install "https://github.com/nils-org/OctoPrint-FHEM-Temp/archive/main.zip"`
- Configure this plugin
- Watch the temperatures appear in the graph

## Status
Experimental !

## Development
in docker:
* `docker compose up`dev
* connect to http://localhost:8080.
