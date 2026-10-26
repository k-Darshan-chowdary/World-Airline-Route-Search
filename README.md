# World-Airline-Route-Search
C++ and Python airline route search application using graph algorithms and interactive world map visualization.

## Phase 3: real-world dataset importer

**All three teammates:** start with [TEAM_DATASET_SETUP.md](TEAM_DATASET_SETUP.md).
In Windows VS Code PowerShell, run `py -3.13 scripts/setup_dataset.py` for the
environment, all tests, pinned downloads/import and independent checksum checks.
The onboarding branch is `feature/phase3-team-dataset-setup`, stacked on the
importer PR. CI runs all 36 original tests plus 10 setup regressions without
downloading worldwide raw data.

The global observed-data importer is implemented on
`feature/phase3-global-dataset-importer`, stacked onto the Phase 1/2 branch.
It uses the verified **MrAirspace 2026 Q3 ADS-B observations** with pinned
OurAirports airport/country metadata. This is incomplete historical observed
connectivity, not all world routes, current airline service or live schedules.
Airline codes are inferred from callsigns, not verified operating carriers.

See [download/import instructions, schemas, filtering and licensing](docs/phase3_import.md)
and the [locked source manifest](data/sources.json). Large raw and generated
files are ignored. The generated `flight.txt` and `cities.tsv` preserve the
Phase 2 format and add airport/airline provenance and a reproducibility report.
Graph loading, `Graph.cpp`, BFS and GUI/map code come after this phase.

Verified full import: **819 cities, 19,283 directed routes, 882 airports,
85 countries/territories** after conservative filtering of 16,018,874 input
rows. All **36 tests pass**; the synthetic fixture is unchanged. See the
[validation snapshot](docs/phase3_validation.json) for exact counts and hashes.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-import.txt
.\.venv\Scripts\python.exe scripts/download_phase3.py
.\.venv\Scripts\python.exe scripts/import_global.py
.\.venv\Scripts\python.exe scripts/validate_global.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The following Phase 1/2 notes describe the original synthetic fixture and its
historical branch boundary; the fixture and all its tests remain unchanged.

## Person 1 progress: Phases 1 and 2

Repository setup and the sample-data foundation are prepared. The existing
[team responsibilities](Airline_Team_Roles.docx) document is preserved.
See [setup and tool versions](docs/phase1_setup.md) and
[data provenance](docs/data_sources.md).

**The included routes are synthetic illustrative examples, not verified or
current airline service. No OpenFlights dataset has been downloaded.**
The future OpenFlights route source is 2014-era historical data.

### Folder layout

```text
cpp/include/          future C++ headers (placeholder only)
cpp/src/              future C++ source (placeholder only)
data/sample/          synthetic flight.txt and matching cities.tsv
data/raw/             reserved for later source data (placeholder only)
scripts/              standard-library Python data checker
tests/                data validation tests
docs/                 setup and data-source notes
python/gui/           future desktop interface (placeholder only)
python/maps/          future map display (placeholder only)
```

### Dataset format

Files use UTF-8. Labels use the exact form `City, Country` and are
case-sensitive. A tab separates fields; commas inside labels are not delimiters.

`data/sample/flight.txt`: no header; one directed edge per line with exactly two
tab-separated fields, `source<TAB>destination`. `<TAB>` means one actual tab.
Blank lines and lines beginning with `#` (optionally after spaces) are ignored.
`Dallas, United States<TAB>New York, United States` represents only Dallas to
New York. The reverse direction must be a separate row. Duplicate directed
edges and self-loops are rejected. There are no weights, fares or schedules.

`data/sample/cities.tsv`: a tab-separated header
`city<TAB>latitude<TAB>longitude`, followed by one row per city. Coordinates are
finite decimal degrees: latitude in [-90, 90], longitude in [-180, 180]. They
represent approximate city centers, not airports. Every route endpoint must
have exactly one coordinate record, and every sample city must occur in an edge.
The included fixture contains **12 unique cities, 20 directed edges, and 12
coordinate records**. See the source notes for the sample's limitations.

### How to run the Phase 2 checks

Open this folder in VS Code, then open its terminal. Python 3.9+ is sufficient;
the checks need no packages or installation. From the repository root:

```powershell
python scripts/check_phase2.py --expect-cities 12 --expect-edges 20
python -m unittest discover -s tests -v
```

Expected checker result:

```text
PASS: 12 cities; 20 directed edges; 12 matching coordinate records
Integrity checks passed. Sample routes are synthetic; no real-world service is asserted.
```

The checker exits with code 1 and a `FAIL:` diagnostic when integrity or expected
counts do not match. It locates the bundled sample relative to its own file;
`--data-dir PATH` can select another directory containing the same two formats.
Tests cover the fixture counts, directed one-way edges, invalid coordinates,
missing or duplicate metadata, malformed rows, duplicate edges, self-loops,
empty data, unused cities, and a failing command-line count check.

### Branch and phase boundary

Work is on `feature/person1-graph-q1-q2`, based on `main`. Submit changes through
a draft pull request to `main` for review. Phases 1 and 2 do not implement a
graph loader, `Graph.cpp`, BFS, Q1/Q2 routing, GUI, maps or source-data downloads.
There is no runnable route-search application yet.
