# Phase 3: worldwide observed-data importer

Phase 3 introduced the real observed-data importer. Graph loading, BFS and
Q1/Q2 are now implemented; GUI and maps remain pending. `data/sample/` remains the unchanged
synthetic 12-city/20-edge fixture; it is never replaced with downloaded data.

For the current one-command teammate setup, independent reviewed checksum lock
and offline CI, follow [TEAM_DATASET_SETUP.md](../TEAM_DATASET_SETUP.md).
The 36-test measurement below is the original importer baseline; onboarding
adds 10 regressions for a current total of 46, retaining all original tests.

## Verified full import result

The 2026-10-26 run processed **all 16,018,874 input rows** and retained
1,241,591 qualifying rows (7.75%). It produced **819 cities, 19,283 distinct
directed city routes, 882 airports, and 85 countries/territories**, with 50,327
distinct airport-pair/inferred-airline evidence groups. These are measured
output counts after strict filters, not worldwide totals. Missing countries
or routes do not imply a lack of service.

All **36 tests passed** (13 preserved Phase 2 tests plus 23 Phase 3 tests), with
no skips in the installed PyArrow environment. Independent validation passed
for every output hash, route/city integrity, airport evidence, timestamps,
representative coordinates and rejection accounting. See the committed
[validation snapshot](phase3_validation.json) for every counter and hash.
The actual usable data is local in `data/generated/2026-q3/`, ignored by Git.

## Verified source choice (2026-10-26)

The preferred source is available and was downloaded and inspected:
[MrAirspace 2026 Q3 detailed release](https://github.com/MrAirspace/aircraft-flight-schedules/releases/tag/aircraft_flight_schedules_2026_quarter3),
published 2026-10-13 at 18:43:08 UTC. Asset: `2026_Q3_detailed_github.parquet`,
1,026,954,012 bytes, SHA-256
`d7cf25ffb128b4ceade6a2b898e6901f829ebf8ac065985fcdaf1787ffa1d1c1`.
The actual footer reports 16,018,874 rows in 16 row groups. This is **observed
historical aircraft movement**, not a verified airline timetable, bookable
service, passenger-only network, or proof that every world route is present.

The [publisher's README](https://github.com/MrAirspace/aircraft-flight-schedules)
explains uneven ADSB.lol receiver coverage, ambiguous airports, track gaps,
spoofing, general-aviation assignment errors and possible duplicate tracks.
`Airline` is inferred from the callsign. Three-letter syntax and prefix checks
cannot prove an operating airline; cargo, private, military, charter, training,
positioning and erroneous observations may remain. There are no service dates
or frequencies reliable enough for itinerary planning.

[OurAirports downloads](https://ourairports.com/data/) provide airport and country
metadata, pinned to commit `d97df1673cc5ba61a09b17ab5936091a669a04ca`
(downloaded 2026-10-26). This metadata date differs from the flight quarter.
Source URLs, exact hashes and byte counts are locked in `data/sources.json`.
That manifest also pins the upstream README and database license used for review.
The downloader verifies existing files, streams new files through `.part`, and
checks hashes before publication. A mismatch fails; existing inputs are preserved.
An interrupted transfer restarts from zero when rerun; it does not resume.

OpenFlights is a possible **separate future adapter**, not silently substituted
in this phase. Its [official documentation](https://openflights.org/data.php)
states route updates stopped in June 2014. No OpenFlights data was used in the
observed Q3 output. The older Phase 2 source notes remain historical context.

## Exact input schema and airport matching

The actual Q3 file has 18 Arrow `string` fields (see `data/schema_2026_q3.json`):
`ICAO_Hex`, `Reg`, `AC_Type`, `AC_Type_Description`, `AC_Type_Detailed`, `Airline`,
`Callsign`, plus origin/destination `Lat`, `Lon`, `FL_Ft`, `DateTime_UTC`,
`ApplicableAirports`, and `Route_Validation_Based_on_Callsign`.
The importer projects only its 12 required columns and rejects missing columns
or changed required types. It does not load a whole pandas DataFrame.

Endpoint candidate cells are strings like `['EGLL']`, not scalar airport codes
or Arrow lists. An anchored parser accepts one four-letter uppercase ICAO
candidate only. It never evaluates source text or chooses the first of several
airports. Missing markers (`-`, `nan`), malformed text and multiple candidates
are rejected. Callsign-route enrichment is not used to invent missing endpoints:
it is auxiliary inferred evidence, not independent confirmation.

Join exclusively to OurAirports **`icao_code`**, requiring a unique code in the
airport snapshot. Preserve `ident`, numeric OurAirports `id`, ICAO, IATA and
region in `airports.tsv`. OurAirports `id` is its own internal key; it is **not**
an OpenFlights numeric airport ID. `ident` may be ICAO, local or generated; do
not assume every `ident` is ICAO. `gps_code` is not guaranteed unique. No IATA,
local-code, fuzzy-name or nearest-airport fallback is performed. Code changes,
reassignments and metadata lag can still cause mismatches or missing routes.
See the [OurAirports dictionary](https://ourairports.com/help/data-dictionary.html).

## Retention policy and counts

Each input observation has one disposition, the first failing rule below:

1. Parse both UTC timestamps. Require arrival after departure and at most 36
   hours later (a conservative plausibility bound, not a schedule validation).
2. Keep departures in `[2026-07-01 00:00 UTC, 2026-10-01 00:00 UTC)` only.
   Adjacent-quarter overlaps therefore do not expand the quarter. Arrivals may
   fall just outside the quarter. Naive source timestamps mean UTC by schema.
3. Require a three-letter `Airline` and an alphanumeric callsign of at most eight
   characters, starting with that code and containing a digit in its suffix.
4. Require both endpoint altitude fields to be `ground`. Numeric `0` is not
   assumed to mean ground; flight levels can be misleading above high terrain.
5. Require singleton ICAO candidates and matched usable airport metadata.
6. Require finite geographic coordinates and each track endpoint within **5 km**
   of its airport reference point. This is stricter than upstream's 9 km search;
   it discards valid distant runway positions as well as uncertain assignments.
7. Drop city self-loops after aggregation. Keep direction; never add a reverse
   route unless observed. Collapse all accepted observations to distinct city
   pairs and separately aggregate airport-pair/inferred-airline evidence.

`report.json` records all first-failure counters, accepted rows, unique edges,
airports, countries/territories, and duplicate-collapse counts. Every input row
must equal accepted rows plus rejected rows. `accepted_input_rows` is an input
record count **not a count of unique flights or service frequency**. Repeated
observations and upstream duplicate tracks collapse in the route output; they
can both contribute to that evidence counter. Aircraft registrations/callsigns
are not exported. No weight, fare, flight number or timetable is fabricated.

Airport metadata must have required headers and valid row structure. Duplicate
internal IDs/idents fail the import; duplicate ICAO codes are excluded. Missing
municipality/country, invalid coordinates, closed airports, heliports and
balloonports are excluded. Accepted types: large, medium and small airports,
and seaplane bases. Today's `scheduled_service` is not used to establish a
historical operation. Airport-level rejection counts appear separately.

City labels retain NFC-normalized, trimmed `Municipality, Country` spelling.
To remain compatible with the Phase 2 format, city/country parts containing
commas, tabs, line breaks, or a leading `#` are rejected instead of rewritten.
If the same label appears across different OurAirports `iso_region` values,
exclude that whole label and count it. This deliberately sacrifices coverage
to avoid some homonym merges; region codes describe airports, so multi-region
metro areas can also be excluded. Same-named places within one region can
still collide; case/diacritic variants remain distinct. No metropolitan-area
gazetteer is assumed. A later explicit city-ID mapping can improve this.

Map coordinates are the lexicographically first **retained airport ident** per
city, documented in `city_representatives.tsv`. They are representative airport
coordinates, not verified city centers or an average across distant airports.

## Reproduce on Windows in VS Code

Use Python 3.10+ and about 3 GB free disk for raw data, the environment, generated
files and temporary database. Run from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-import.txt
.\.venv\Scripts\python.exe scripts/download_phase3.py
.\.venv\Scripts\python.exe scripts/import_global.py
.\.venv\Scripts\python.exe scripts/validate_global.py
.\.venv\Scripts\python.exe scripts/check_phase2.py --expect-cities 12 --expect-edges 20
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

No environment activation or PowerShell execution-policy change is needed.
Run commands using the terminal normally; automation may need permission to
access Windows temporary folders. The actual Parquet integration test requires
PyArrow; without it only that test is skipped and the remaining tests still run.

The default output is `data/generated/2026-q3/`. Re-running refuses to overwrite
an existing output; use `--output-dir data/generated/another-run`. Inputs are
verified on every run. `--batch-size` defaults to 32,768 (allowed 1..131,072);
only that batch's rows and grouping dictionary are held in Python alongside the
airport lookup and bounded ICAO parser cache. Distinct airport/airline evidence
and city-pair deduplication use a disk SQLite database with a 16 MiB page cache
and file-backed temporary storage. Arrow can additionally buffer compressed
column chunks; batch size alone is not a hard process memory ceiling.

Exports are sorted deterministically. Batching and source row order do not
change the data tables or counts. A fresh staging directory is renamed to the
requested output only after success; a failed run publishes no partial dataset.
An abrupt process termination may leave an ignored staging directory, which is
not a completed dataset. Concurrent runs must use separate output directories.
SHA-256s in the report identify all five data tables. The validator checks those
hashes, city/edge integrity, provenance links and sums, timestamps and row
accounting. Hashes establish reproducibility, not truth of the observations.

## Output contract and licensing

| File | Meaning |
| --- | --- |
| `flight.txt` | Headerless UTF-8 `source_city<TAB>destination_city`, unique directed edges |
| `cities.tsv` | Existing `city, latitude, longitude` TSV header; one record per route city |
| `airports.tsv` | Retained airport IDs, codes, city labels, regions and coordinates |
| `city_representatives.tsv` | Airport supplying each map marker |
| `route_provenance.tsv` | Airport pair and inferred airline, accepted input rows, first/last departure |
| `report.json` | Pinned sources, thresholds, counters, hashes and limitations |
| `ATTRIBUTION.txt`, `LICENSE-ODbL.txt` | Notices that travel with derived database copies |

The flight database is under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/),
with the publisher's license reproduced at `docs/licenses/ODbL-1.0.txt` and in
each generated output. Credit MrAirspace (Sebastiaan Menger) and ADSB.lol.
OurAirports airport/country data is Public Domain and is credited as well.
On redistribution/public use of the adapted database, preserve attribution,
identify the adaptation and filtering, provide the ODbL notice/license, and
make the adapted database available under ODbL as required by its terms.
This data license does not assert a new license for the project's code.

Raw data, Parquet, generated worldwide files, SQLite and partial downloads are
ignored. Only source lock/schema, importer code, tests, attribution/license and
small validation reports are intended for Git. Generated data is usable locally
and reproducible through the pinned downloads; do not commit the 1 GB input.

## Original review history

Phase 3 was developed on `feature/phase3-global-dataset-importer`, based on
Phase 1/2 commit `340ecd8e471c9b2c6109ebe2161daf0cf2b3319e`. Its original
review targeted `feature/person1-graph-q1-q2` to isolate importer changes.
Those phases are merged; new work starts from current `main`. The measurements
above remain the original Phase 3 evidence.
