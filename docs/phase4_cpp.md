# Phase 4 C++ graph

Phase 4 is merged into `main` through PR #5 (`4cbf979`).
This phase covers graph storage, loading, generic BFS, CLI, CMake and tests.
Question 1 is added in [Phase 5](phase5_q1.md), and Question 2 in
[Phase 6](phase6_q2.md). GUI/map remains future work.

## Build in the VS Code terminal

Requirements: a C++17 compiler, CMake 3.16+, and Python 3.10+ for tests.
The C++ implementation and unit tests use only the C++ standard library.
The CLI subprocess tests use Python's standard library. The existing Phase 3
Python suite additionally requires `requirements-import.lock`.

On Linux, or in a Windows Visual Studio developer terminal:

```text
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --config Debug --parallel 2
ctest --test-dir build -C Debug --output-on-failure --no-tests=error
```

On this Windows machine, GCC is available through MSYS2 UCRT64. The tested
PowerShell configuration uses CMake installed into the repository's `.venv`:

```powershell
# If CMake is not already installed:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install cmake
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-import.lock

$pythonPath = (Resolve-Path .venv/Scripts/python.exe).Path
.\.venv\Scripts\cmake.exe -S . -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_COMPILER=C:/msys64/ucrt64/bin/g++.exe -DCMAKE_MAKE_PROGRAM=C:/msys64/ucrt64/bin/mingw32-make.exe "-DPython3_EXECUTABLE:FILEPATH=$pythonPath"
.\.venv\Scripts\cmake.exe --build build --parallel 2
.\.venv\Scripts\ctest.exe --test-dir build --output-on-failure --no-tests=error
```

Keep `C:\msys64\ucrt64\bin` on PATH so GCC runtime DLLs are available.
MSVC Debug builds use a separate CLI linker PDB name so parallel builds do
not collide with the graph library's compiler PDB.
Use a separate `build-release` directory with `-DCMAKE_BUILD_TYPE=Release` to
repeat with optimizations. For Visual Studio generators, also pass
`--config Release` to build and `-C Release` to CTest. Production-only builds
can set `-DBUILD_TESTING=OFF` and need no Python.

## Verify the official dataset

Reuse the existing Phase 3 generated directory or follow
[TEAM_DATASET_SETUP.md](../TEAM_DATASET_SETUP.md) to reproduce it. Do not replace
it with a synthetic fixture, overwrite its files or commit raw/generated data.
Enable the additional global CTest targets explicitly:

```powershell
.\.venv\Scripts\cmake.exe -S . -B build -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build --parallel 2
.\.venv\Scripts\ctest.exe --test-dir build --output-on-failure --no-tests=error -V
.\.venv\Scripts\python.exe scripts/run_tests.py
```

Relative global paths resolve against the repository root. CTest first verifies
all five tables, attribution and license against the committed Phase 3 lock,
including provenance and count accounting. The global graph and CLI tests
depend on that verification; a missing or altered dataset fails the run.
Phase 4 introduced six CTest targets with global verification and three
otherwise. Phase 5 expands these totals to ten and five respectively; Phase 6
expands them to fourteen and seven. The global
graph test checks paths and shortest-distance
certificates from all 819 sources, including unreachable vertices. Tests use
explicit checks that remain active in Release mode.

GitHub Actions runs the offline C++/CLI tests on Ubuntu 24.04 (GCC) and Windows
2022 (MSVC), in Debug and Release. The existing 46 Python tests continue in
their separate jobs. Normal CI does not download the 1 GB historical source or
claim to run global tests; use the explicit configuration above for those.

## CLI

From the repository root (Visual Studio builds put the executable under
`build/Debug/` or `build/Release/`):

```powershell
.\build\airline_graph.exe --data-dir data/sample --expect-cities 12 --expect-routes 20
.\build\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --to "Auckland, New Zealand"
.\build\airline_graph.exe --expect-cities 819 --expect-routes 19283
```

The default data directory is `data/generated/2026-q3`, relative to the current
working directory. City labels match exactly and are case-sensitive. Both
`--from` and `--to` are required for a path query. Counts accept only unsigned
decimal digits fitting `size_t`. Usage/input errors return 1. An unreachable
destination is a valid result and returns 0; a source-to-itself path has zero
flights. `--help` returns 0 without opening data files.

## Data and graph contract

`cities.tsv` has header `city<TAB>latitude<TAB>longitude`; `flight.txt` contains
headerless `source<TAB>destination` rows. Labels use `City, Country`, with no
extra comma, empty component, surrounding spaces or leading comment marker
in either component. Input is UTF-8; BOM and CRLF are accepted. Route comments
and blank lines are ignored. Decimal coordinates, including exponents, must be
finite and within geographic bounds; hexadecimal values and trailing junk are
rejected. Duplicate cities/routes, self-loops, unknown endpoints, unused
metadata and empty datasets fail with file/line diagnostics. Invalid UTF-8
and embedded ASCII controls are rejected.

City IDs follow metadata insertion order and remain stable when cities are
added. `addEdge` returns false for duplicate edges and rejects self-loops.
The graph itself can contain isolated cities; the dataset loader applies the
stricter Phase 3 rule that every metadata city must be a route endpoint.
Checked accessors and BFS reject invalid IDs. Loaded neighbors are sorted by
city ID, so shortest-path ties follow stable metadata order. BFS is O(V+E),
with O(V) traversal storage; `pathTo` is O(path length), returns an empty vector
for unreachable destinations and a singleton for the source.

Routes describe historical observed connectivity, not current/bookable flights.
Global coordinates remain the Phase 3 representative-airport coordinates.
All Phase 3 source pins, data tables, notices, importer and tests are preserved.
