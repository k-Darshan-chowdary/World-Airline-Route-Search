# Dataset provenance and future sources

Phase 3 now imports verified real observations from MrAirspace 2026 Q3 and
OurAirports metadata. See [Phase 3 source verification and reproducible import](phase3_import.md)
and `data/sources.json`. The notes below retain the original Phase 2 context;
OpenFlights was not used for the Phase 3 observed dataset.

## Included Phase 2 sample

`data/sample/flight.txt` is a manually authored, **synthetic illustrative**
dataset: 12 cities and 20 directed edges. It is a format/integrity fixture for
development, not evidence of an airline operating any route, timetable, fare,
distance, frequency, or present-day connectivity. Directions are independent.

`data/sample/cities.tsv` contains manually entered, approximate city-center
coordinates in decimal degrees (latitude, longitude). They are illustrative map
positions, not airport coordinates, and have not been geospatially verified.
City labels match the edge endpoints exactly. No third-party dataset was
downloaded or imported for this phase. `data/raw/` is reserved and empty except
for its Git placeholder.

## Planned later source: OpenFlights

Official data documentation: <https://openflights.org/data.php>
(also served at <https://nginx.openflights.org/data>).
OpenFlights states that its route-data provider stopped providing updates in
June 2014. Treat that route snapshot as **2014-era historical data**, never as
current airline service. Airport metadata and route records may have different
update dates. These notes do not claim that source files are included here.

A later, separately scoped import should record the download date, exact source
URLs, file hashes, source snapshot dates, license and required attribution.
Follow the source's licensing terms before distributing derived files. Join
airport IDs to airport metadata, handle missing/unknown IDs and coordinates,
map airports to consistent `City, Country` labels, and document any city-name
collisions. Preserve direction, explicitly decide how to handle stop counts and
codeshares, remove city self-loops after aggregation, and deduplicate directed
city pairs. Report retained/rejected rows and resulting city/edge counts.
No importer is implemented in Phases 1 or 2.
