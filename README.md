# World-Airline-Route-Search
C++ and Python airline route search application using graph algorithms and interactive world map visualization.

## Phase 7: Person 1 backend integration and team handoff

Phases 1–6 are merged into `main`, through Phase 6 merge `aaa014a` (PR #7).
Phase 7 is on `feature/phase7-backend-handoff` for separate draft-PR review;
it preserves Q1/Q2 behavior and JSON schema version 1. Person 1's backend
handoff includes:

- [Maintained C++ API and subprocess JSON contract](docs/backend_api_contract.md),
  with field types, statuses, exact CLI examples, map metadata joins and errors.
- [Windows VS Code setup and teammate responsibilities](docs/team_backend_handoff.md).
- A stdlib-only [Python subprocess adapter](examples/backend_client.py) and
  separate CTest contract/integration tests; CI remains offline with six jobs.
- [Phase 7 executed validation and compatibility notes](docs/phase7_validation.md).

Q3/Q4 are Person 2's work; PySide6/Folium/Qt WebEngine are Person 3's work.
Those features remain unimplemented here. Sample routes are synthetic; official
routes are incomplete historical observed connectivity, not bookable service.
The earlier phase sections below retain implementation/setup history.

## Phase 6: Question 2 through two required cities

Person 1's Q2 is implemented in the reusable C++17 `RequiredStops` API and
CLI `--via-b B --via-c C`, with optional `--json`. Three directed BFS traversals
compare A → B → C → D and A → C → B → D and return the walk with the fewest
flights. Repeated visits and aliased endpoints are supported; waypoint order
reports actual first encounters. Connections are `max(flights - 1, 0)`.

See [Phase 6 semantics, correctness, commands and executed validation](docs/phase6_q2.md).
Phase 6 was merged through [PR #7](https://github.com/k-Darshan-chowdary/World-Airline-Route-Search/pull/7)
at `aaa014a`. GUI, maps and teammates' Q3/Q4 remain future work.

```powershell
.\build\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --via-b "London, United Kingdom" --via-c "Tokyo, Japan" --to "Auckland, New Zealand" --json
```

## Phase 5: Question 1 shortest route with a connection limit

Phase 5 adds the reusable C++17 `RouteSearch` API and CLI
`--max-connections X` with optional `--json`. Connections are intermediate
cities: a direct flight has zero, and the limit is strictly `connections < X`.
Same-city queries use zero flights/zero connections; invalid inputs are errors,
while unreachable and over-limit routes are distinct valid no-result statuses.

See [Phase 5 semantics, API, CLI, tests and validation](docs/phase5_q1.md).
Phase 5 is merged into `main` through PR #6 (`0bf8269`). Question 2 is added
in Phase 6 above; GUI/map work remains future work.

## Phase 4: C++17 directed graph and BFS

The existing Phase 4 implementation is completed on
`feature/phase4-cpp-directed-graph`: checked city IDs, coordinates, directed
adjacency lists, strict UTF-8 dataset loading, and unweighted BFS with parent
paths and unreachable results. Reverse routes exist only when present in the
input. Phase 4 did not implement Questions 1/2 or GUI/map features;
Q1 is added in Phase 5 above.

See [build, CLI and test instructions](docs/phase4_cpp.md) and
[actual compilation/test evidence](docs/phase4_validation.md).
Debug and Release builds pass the 12-city/20-route sample and the checksum-locked
819-city/19,283-route dataset, including BFS from every city. CI tests C++17 on
Linux and Windows in both configurations alongside all preserved Python tests.
The following Phase 3 and Phase 1/2 sections retain the earlier setup history.

## Phase 3: real-world dataset importer

**All three teammates:** start with [TEAM_DATASET_SETUP.md](TEAM_DATASET_SETUP.md).
Download the step-by-step [teammate Word guide](docs/Teammate_Dataset_Setup_Guide.docx)
for setup, verification, troubleshooting and the completion checklist.
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
Graph loading, `Graph.cpp` and BFS are now completed in Phase 4 above;
GUI/map code remains future work.

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
