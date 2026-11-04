# World Airline Route Search

A university Data Structures and Algorithms project featuring a C++17 directed graph, a Python (PySide6) desktop interface, and interactive Folium route maps. Cities are vertices and directed connections are edges: A → B does not imply B → A.

## Four search questions

| Question | Behavior |
| --- | --- |
| **Q1 — Shortest route** | Find the fewest flights from A to B, using strictly fewer than X intermediate connections. |
| **Q2 — Required stops** | Find the fewest flights from A to D while visiting B and C in either order. |
| **Q3 — Round trip** | Start at A, visit every city reachable from A, then return to A **only at the end**. The minimum is exact for up to **18 reachable cities**. On larger graphs, feasibility is decided exactly and a valid route is built where possible, but **the route length may not be minimum**. |
| **Q4 — Meeting city** | Choose a city distinct from all three starting cities that minimizes the sum of directed shortest flight distances, and show the three routes. |

The app provides a readable summary, optional backend JSON, and city-to-city maps. Q4 paths are color-coded.

## Requirements

- CMake 3.16+ and a C++17 compiler (for Windows, Visual Studio C++ Build Tools or compatible MinGW).
- 64-bit Python 3.13 recommended; required to regenerate the locked historical dataset.
- Internet connection for GUI package installation and online map tiles.

## Run the app on Windows (VS Code CMD terminal)

Open the repository root in VS Code. Run:

~~~cmd
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
cmake -S . -B build
cmake --build build --config Release
.\.venv\Scripts\python.exe -m python.gui.app
~~~

The GUI automatically finds the executable under either build\Release\airline_graph.exe (Visual Studio Release) or build\airline_graph.exe (single-configuration compilers). The initial dataset is the bundled sample.

You can also run the C++ backend alone, without Python GUI dependencies. For example (Visual Studio Release):

~~~cmd
build\Release\airline_graph.exe --data-dir data\sample --round-trip "Auckland, New Zealand" --json
~~~

The sample answer is Auckland → Sydney → Auckland, 2 flights. For MinGW, use build\airline_graph.exe instead.

## Datasets

| Dataset | Size | How to use |
| --- | --- | --- |
| Included synthetic sample, data/sample/ | **12 cities, 20 directed edges** | Available immediately for testing and demonstration |
| Historical Q3 2026 observations, data/generated/2026-q3/ | **819 cities, 19,283 directed edges, 85 countries/territories** | Generate locally or reuse previously validated files; omitted from Git because of size |

To reuse an existing historical dataset, copy the **complete** validated 2026-q3 output folder into data/generated/2026-q3/ and run:

~~~cmd
.\.venv\Scripts\python.exe scripts\dataset_lock.py --outputs-only --data-dir data\generated\2026-q3
~~~

To regenerate from pinned public sources (large download, adequate free disk space required), run:

~~~cmd
py -3.13 scripts\setup_dataset.py
~~~

Restart the GUI and select **Historical observations · 819 cities** in its dataset selector.

The importer and verifier are in scripts/. Source file identities and output hashes are pinned in data/sources.json and data/dataset_2026_q3.lock.json. Raw Parquet files and generated tables are ignored by Git.

## Project structure

~~~text
CMakeLists.txt                  C++17 build
cpp/include/                   Graph/routing headers
cpp/src/                       Directed graph loader, BFS, Q1–Q4, JSON CLI
python/gui/                    PySide6 interface, response formatting and maps
data/sample/                   Included synthetic directed graph
data/sources.json              Real-data source metadata
data/dataset_2026_q3.lock.json Checksum-locked dataset details
scripts/                       Historical source download/import/verification
docs/licenses/ODbL-1.0.txt     Historical database license
requirements-gui.txt           GUI dependencies
requirements-import.lock       Pinned historical importer dependency
~~~

## Data provenance and limitations

This is a historical route connectivity analysis, **not a live flight search or booking service**. The worldwide data originates from **MrAirspace Q3 2026 ADS-B observations** combined with **OurAirports** airport metadata. It is incomplete and geographically uneven. Map lines connect representative locations, not actual aircraft tracks. The manually authored sample data is illustrative, not actual airline service.

The adapted historical observation database is covered by **Open Database License (ODbL) 1.0**. Preserve the generated ATTRIBUTION.txt and LICENSE-ODbL.txt with any copies of the real dataset. The source manifest, checksum lock and ODbL license text remain here for reproducibility and proper attribution. This database license does not automatically license the program's C++ or Python source code.

**Q3 limit:** for at most 18 reachable cities, the BFS-on-(city, visited-set) solution proves the fewest flights. For larger graphs, component analysis proves whether a tour exists and constructs a valid tour if feasible, but does not prove it has the shortest flight count.

Extended development tests, CI and earlier documentation are preserved in the Git branch **archive/full-development-before-submission-cleanup**.
