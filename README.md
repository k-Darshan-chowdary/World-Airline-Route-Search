# World Airline Route Search

A three-person university DSA project that uses a directed graph to search for
routes between cities. The C++17 backend loads city and route data, finds routes
with BFS, and returns readable output or JSON for the planned Python GUI.

The original Q1/Q2 backend and dataset are complete through Phase 7. Q3/Q4
and a GUI prototype have been implemented in the integration branch. The GUI still needs a Windows visual check. This project studies **historical observed connectivity**;
it does not provide current schedules, fares, available seats or bookings.

## Project status

| Part | Owner | Status |
| --- | --- | --- |
| Dataset importer, graph, BFS and CLI | Person 1 | Complete |
| Q1: shortest route with fewer than `x` connections | Person 1 | Complete |
| Q2: shortest walk through two required cities, in either order | Person 1 | Complete |
| JSON v1 contract and Python adapter | Person 1 | Complete |
| Q3: closed walk visiting reachable cities | Advanced routing | Implemented; exact at small sizes, heuristic at larger sizes |
| Q4: meeting-city search | Advanced routing | Implemented and tested |
| PySide6 GUI and Folium / Qt WebEngine maps | Desktop interface | Implemented; live Windows validation pending |

See the [team roles](Airline_Team_Roles.docx) and
[backend handoff](docs/team_backend_handoff.md) for responsibilities and integration.

## Algorithms and tools

- **C++17:** directed adjacency lists, hash lookup for exact city labels, and
  BFS with a queue, distance array and parent array.
- **Q1:** one BFS finds the fewest flight legs, then checks the strict connection
  limit. Connections are `max(flights - 1, 0)`, so a direct flight has zero.
- **Q2:** three BFS traversals compare A → B → C → D and A → C → B → D.
  The result is a shortest directed walk; repeated cities are allowed.
- **Python:** dataset setup, streaming Parquet import with PyArrow, validation
  and a standard-library subprocess adapter.
- **CMake / CTest and GitHub Actions:** builds and regression tests on Windows
  and Linux. The C++ code has no external library dependencies.

Graph storage is **O(V + E)**. Q1 and Q2 each take **O(V + E)** time and
**O(V)** extra space per query. A → B does not imply B → A.
Ties follow stable metadata city IDs. Details: [Q1](docs/phase5_q1.md),
[Q2](docs/phase6_q2.md), [API contract](docs/backend_api_contract.md).

## Data

| Dataset | Contents | Use |
| --- | --- | --- |
| `data/sample/` | 12 cities, 20 directed routes | Synthetic examples and offline tests; included in Git |
| `data/generated/2026-q3/` | 819 cities, 19,283 unique directed routes, 882 airports, 85 countries/territories | Filtered historical observations; generated locally and ignored by Git |

The real dataset uses pinned **MrAirspace 2026 Q3 ADS-B observations** and
**OurAirports** metadata. Versions, source URLs and checksums are recorded in
[sources.json](data/sources.json) and the independent
[dataset lock](data/dataset_2026_q3.lock.json). Setup verifies source bytes,
generated tables, attribution and license notices against that lock.

Coverage is incomplete and geographically uneven. Airline codes are inferred
from callsigns, and retained record counts are not flight frequencies. Map
coordinates represent one retained airport per city; sample coordinates are
approximate city centers. Missing routes do not prove that no service exists.
Read the [source and filtering notes](docs/phase3_import.md) before using the data.

## Q3/Q4 and the desktop GUI

The project includes Q3/Q4 implementations and an optional desktop interface.
The C++ algorithms are covered by cross-platform tests; live GUI validation
is a separate step.

- **Q3:** an exact shortest round trip visiting every reachable city when the
  reachable graph has at most 14 cities, returning to the start **only at the end**. Larger graphs use a clearly labeled
  **heuristic**; its route is not guaranteed to be the shortest and it can fail to find a valid tour. A route is
  impossible if a reachable city cannot return to the start.
- **Q4:** find a meeting city distinct from all three origins that minimizes
  the sum of directed shortest flight counts from the three origins.
- **GUI:** four always-visible question buttons, concise route results, a separate
  enlarged result/map window, and an optional collapsible JSON view. Searches run
  the compiled C++ backend in a background thread. Q4 routes are colored by
  traveler and labeled in a legend. Map lines connect representative city
  coordinates, not measured aircraft tracks.

CLI examples (after building the C++ program):

```cmd
build\airline_graph.exe --data-dir data/sample --round-trip "Auckland, New Zealand" --json
build\airline_graph.exe --data-dir data/sample --meeting-a "Dallas, United States" --meeting-b "New York, United States" --meeting-c "London, United Kingdom" --json
```

Run the optional GUI from the repository root on Windows after installing the
regular C++ build and Python 3.13 environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m python.gui.app
```

The GUI loads the included small sample by default, and offers the historical
data when `data/generated/2026-q3/cities.tsv` is present. It needs a compiled
`airline_graph` executable in a documented build location. WebEngine and map
tiles may require internet access. If the window or map fails, use the tested
CLI for the final demonstration rather than claim the GUI is verified.

For a guided tour of each question and screenshots, see
[GUI demonstration and testing](docs/gui_walkthrough.md). The interface
distinguishes **flights/edges** from **intermediate connections**, and marks
large-graph Q3 output as heuristic rather than proven shortest.

To print the sample graph's stored input connections for inspection, run
`type data\\sample\\flight.txt` in Windows CMD. The input uses one
tab-separated directed connection per line. The sample and global data
include cities with no outgoing flights when present in the metadata.

To run the repeatable 6, 20 and 50-vertex examples and print measured
end-to-end runtimes (including process startup and file loading), run:

```cmd
.\.venv\Scripts\ctest.exe --test-dir build -V -R cpp_graph_size_checks
```

Actual times depend on the machine; record your own measured output for the
presentation instead of using an estimated runtime.

See [Q3/Q4 algorithm details](docs/q3_q4_algorithms.md).
The professor's Q3 asks for the *minimum*; its exactness restriction must be
disclosed during the demo and in the presentation. Team members should review
and understand their assigned features before submission.

## Quick start

Run all commands from the repository root. To try the sample, you need Git,
CMake 3.16+, a C++17 compiler and Python 3.10+ for CTest. The reproducible
real-data setup requires **64-bit CPython 3.13** and internet access.
CI uses Python 3.13.1.

### Windows: VS Code and MSVC

Install Visual Studio 2022 Build Tools with **Desktop development with C++**
and the Windows SDK. Open an x64 Developer PowerShell terminal in VS Code.

```powershell
git clone https://github.com/k-Darshan-chowdary/World-Airline-Route-Search.git
cd World-Airline-Route-Search

# Optional for the sample; required for the real dataset.
py -3.13 scripts/setup_dataset.py

$backendPython = (py -3.13 -c "import sys; print(sys.executable)").Trim()
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 "-DPython3_EXECUTABLE:FILEPATH=$backendPython"
cmake --build build --config Debug --parallel 2
ctest --test-dir build -C Debug --output-on-failure --no-tests=error
cmake --build build --config Release --parallel 2
ctest --test-dir build -C Release --output-on-failure --no-tests=error
```

Dataset setup creates `.venv`, installs hash-locked dependencies, runs the offline
Python tests, downloads the pinned inputs and verifies the import. Allow at
least **3 GB** of disk space; the flight source alone is about 1 GB. It finishes
with `READY: 819 cities; 19,283 directed routes; 85 countries/territories`.
For an existing verified environment and raw inputs, rerun with `--offline`.
See [dataset setup](TEAM_DATASET_SETUP.md) for recovery and verification commands.

### Linux: GCC

This builds and tests the sample without downloading the real dataset:

```sh
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --parallel 2
ctest --test-dir build-debug --output-on-failure --no-tests=error
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release --parallel 2
ctest --test-dir build-release --output-on-failure --no-tests=error
```

For the real dataset on Linux, run `python3.13 scripts/setup_dataset.py`.
Windows MSYS2/GCC instructions are in the [backend handoff](docs/team_backend_handoff.md#gcc-alternatives).
Use a fresh build directory when changing compiler or CMake generator.

## Try Q1 and Q2

These examples use the included synthetic sample and the MSVC Debug executable:

```powershell
.\build\Debug\airline_graph.exe --data-dir data/sample --expect-cities 12 --expect-routes 20

# Q1: Dallas to New York, with strictly fewer than 1 connection.
.\build\Debug\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --to "New York, United States" --max-connections 1 --json

# Q2: Dallas to Paris through New York and London, in either order.
.\build\Debug\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --via-b "New York, United States" --via-c "London, United Kingdom" --to "Paris, France" --json
```

Q1 returns Dallas → New York: **1 flight, 0 connections**. Q2 returns
Dallas → New York → London → Paris: **3 flights, 2 connections**.
A Q1 limit of `0` cannot qualify, even for a direct flight. An unreachable route
is a valid no-result response; malformed input is an error.

City labels must match `cities.tsv` exactly, including case and accents.
For Linux, use `./build-debug/airline_graph`; MinGW builds use
`.\build-debug\airline_graph.exe`. Remove `--json` for readable output.
After dataset setup, use `--data-dir data/generated/2026-q3` for the real data.
That is also the default directory when `--data-dir` is omitted.

### Call the backend from Python

From the repository root:

```python
from examples.backend_client import query_backend

result = query_backend(
    "build/Debug/airline_graph.exe",
    "data/sample",
    from_city="Dallas, United States",
    to_city="New York, United States",
    exclusive_connection_limit=1,
)
print(result["status"], result["flights"], result["connections"])
# found 1 0
```

The [adapter](examples/backend_client.py) validates JSON schema version 1 and
the echoed query. The [contract](docs/backend_api_contract.md) covers Q2 calls,
statuses, errors, Unicode and metadata joins. GUI integration should run this
blocking call in a worker.

## Tests

After dataset setup, run the separate Python suite:

```powershell
.\.venv\Scripts\python.exe scripts/run_tests.py
.\.venv\Scripts\python.exe scripts/check_phase2.py --expect-cities 12 --expect-edges 20
```

There are **46 offline Python tests**, with network calls blocked and skipped
tests treated as failures. CTest runs **8 offline targets** covering graph
loading, BFS, Q1/Q2, CLI behavior and the Python/JSON contract. Independent
oracles check shortest-route results, including required-city aliases and revisits.

With the verified real dataset available, opt into all **16 CTest targets**:

```powershell
cmake -S . -B build -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
ctest --test-dir build -C Debug --output-on-failure --no-tests=error
ctest --test-dir build -C Release --output-on-failure --no-tests=error
```

The [six-job CI workflow](.github/workflows/dataset-tests.yml) runs Python tests
on Ubuntu and Windows, plus C++ tests on Linux/GCC and Windows/MSVC in Debug
and Release. CI uses small fixtures and does not download or verify the full
real dataset. [Phase 7 validation](docs/phase7_validation.md) records the earlier
full local run; each PR's checks show its own CI results.

## Repository layout

```text
cpp/include/      Graph, BFS, Q1 and Q2 public headers
cpp/src/          Backend implementation and CLI
cpp/tests/        C++ tests and Python subprocess regressions
data/sample/      Committed synthetic fixture
data/             Source manifest, schema and checksum lock
scripts/          Dataset setup, import and validation
tests/            Offline dataset tests
examples/         Python backend adapter
python/gui/       Reserved for Person 3
python/maps/      Reserved for Person 3
docs/             API, handoff, source notes and phase records
```

Start with the [documentation index](docs/README.md),
[dataset setup](TEAM_DATASET_SETUP.md) or [backend contract](docs/backend_api_contract.md).
Raw downloads, generated data, environments and build outputs stay out of Git.

## Attribution and licensing

Flight-derived data comes from MrAirspace / Sebastiaan Menger and ADSB.lol
observations under **ODbL 1.0**. OurAirports metadata is **Public Domain**.
Keep generated attribution, license and provenance files with any shared data,
and follow the [redistribution notes](docs/phase3_import.md)
and [ODbL text](docs/licenses/ODbL-1.0.txt).
These data terms do not establish a license for the project's source code.
