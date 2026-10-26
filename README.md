# World-Airline-Route-Search
C++ and Python airline route search application using graph algorithms and interactive world map visualization.


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
