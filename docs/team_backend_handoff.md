# Person 1 final backend handoff (Phase 7)

Phases 1–6 are merged; Phase 6 merge is `aaa014a5abce132e8ba6414566cf54e983f512bc`.
Phase 7 is reviewed separately on `feature/phase7-backend-handoff`, targeting
`main`; do not merge it without the user's separate approval. The supported
backend is C++17 graph/loader/BFS plus Q1/Q2, with JSON schema version 1.
Start integration with [the maintained API contract](backend_api_contract.md)
and [executed Phase 7 validation](phase7_validation.md).

## Clean Windows VS Code setup

Install Git, **CPython 3.13 x64** with the `py` launcher, CMake 3.16+ and Visual
Studio 2022 Build Tools with **Desktop development with C++ / Windows SDK**.
Open an x64 Visual Studio Developer PowerShell terminal in VS Code. Commands
below run from the repository root. Existing checkouts must first inspect
`git status` and preserve local changes; never reset/clean a teammate's work.

```powershell
git clone https://github.com/k-Darshan-chowdary/World-Airline-Route-Search.git
cd World-Airline-Route-Search
git fetch origin
# Until Phase 7 is approved/merged, review this feature branch:
git switch --track origin/feature/phase7-backend-handoff
py -3.13 --version
py -3.13 scripts/setup_dataset.py
```

The setup creates `.venv`, installs hash-locked import dependencies, runs all
46 offline Python tests with zero skips, downloads pinned raw data, imports,
then independently verifies the locked outputs. It needs internet and disk
space for a roughly 1 GB source plus working/generated files; it can take
time. Reuse a verified installation with `py -3.13 scripts/setup_dataset.py
--offline`. An incomplete environment or changed bytes fails rather than
silently overwriting work. See preserved [TEAM_DATASET_SETUP.md](../TEAM_DATASET_SETUP.md)
and [Word dataset guide](Teammate_Dataset_Setup_Guide.docx) for full recovery
and license details. The Word guide is preserved byte-for-byte in Phase 7.

```powershell
$backendPython = (Resolve-Path .venv/Scripts/python.exe).Path
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 "-DPython3_EXECUTABLE:FILEPATH=$backendPython"
cmake --build build --config Debug --parallel 2
ctest --test-dir build -C Debug --output-on-failure --no-tests=error
cmake --build build --config Release --parallel 2
ctest --test-dir build -C Release --output-on-failure --no-tests=error
.\.venv\Scripts\python.exe scripts/run_tests.py
```

Eight offline CTest targets run without worldwide data. To additionally run
all sixteen targets against the local official data, explicitly configure:

```powershell
cmake -S . -B build -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
ctest --test-dir build -C Debug --output-on-failure --no-tests=error -V
ctest --test-dir build -C Release --output-on-failure --no-tests=error -V
.\.venv\Scripts\python.exe scripts/dataset_lock.py --outputs-only --data-dir data/generated/2026-q3
.\.venv\Scripts\python.exe scripts/validate_global.py
```

The global lock fixture verifies five tables plus attribution/license bytes
and provenance/counts before any global CTest consumer. A missing or changed
explicit dataset fails; nothing is skipped or downloaded by CTest.
To return a configured directory to offline mode, use
`-DAIRLINE_GLOBAL_DATA_DIR:PATH=`. Normal CI always uses offline mode.

For a temporary-directory access restriction, use a writable local folder:
`New-Item -ItemType Directory -Force build/tmp`, then
`$env:TEMP=(Resolve-Path build/tmp).Path; $env:TMP=$env:TEMP`.

### GCC alternatives

Linux/GCC, with Python 3.10+ for CTest (3.13 plus the locked dependencies for
the separate 46-test dataset suite):

```sh
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --parallel 2
ctest --test-dir build-debug --output-on-failure --no-tests=error
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release --parallel 2
ctest --test-dir build-release --output-on-failure --no-tests=error
```

Windows MSYS2 UCRT64/GCC: add `C:\msys64\ucrt64\bin` to PATH and use a fresh
build directory with `-G "MinGW Makefiles"`,
`-DCMAKE_CXX_COMPILER=C:/msys64/ucrt64/bin/g++.exe`,
`-DCMAKE_MAKE_PROGRAM=C:/msys64/ucrt64/bin/mingw32-make.exe`, and
`-DCMAKE_BUILD_TYPE=Debug` (repeat Release separately). The executable is at
`build-debug/airline_graph.exe`, without an MSVC configuration subfolder.
See [Phase 4 toolchain details](phase4_cpp.md). Do not reuse a CMake build
directory across generators/compilers. There are no C++ external dependencies;
`-DBUILD_TESTING=OFF` can build production targets without Python.

## Run Q1/Q2 before wiring the GUI

Sample fallback, available in a clean clone without any dataset download:

```powershell
.\build\Debug\airline_graph.exe --data-dir "data/sample" --expect-cities 12 --expect-routes 20
.\build\Debug\airline_graph.exe --data-dir "data/sample" --from "Dallas, United States" --to "New York, United States" --max-connections 1 --json
.\build\Debug\airline_graph.exe --data-dir "data/sample" --from "Dallas, United States" --via-b "New York, United States" --via-c "London, United Kingdom" --to "Paris, France" --json
```

The first query returns `found`, one flight / zero connections. The second
returns Dallas→New York→London→Paris, three flights / two connections and
New York→London waypoint order. Sample routes are synthetic illustrations.
Strict Q1 `connections < x` means a limit of zero never qualifies.

Official local data, after successful setup:

```powershell
.\build\Debug\airline_graph.exe --data-dir "data/generated/2026-q3" --expect-cities 819 --expect-routes 19283
.\build\Debug\airline_graph.exe --data-dir "data/generated/2026-q3" --from "London, United Kingdom" --to "Tokyo, Japan" --max-connections 5 --json
.\build\Debug\airline_graph.exe --data-dir "data/generated/2026-q3" --from "London, United Kingdom" --via-b "Paris, France" --via-c "Dubai, United Arab Emirates" --to "Tokyo, Japan" --json
```

Official locked outputs have **819 cities / 19,283 directed routes / 882
airports / 85 countries/territories**. They describe incomplete MrAirspace
2026 Q3 ADS-B observations with pinned OurAirports metadata. Coordinates are
representative markers, routes are directed city-level connectivity, and
callsign-inferred airlines are not verified operators. No live service,
seat/price availability or bookings may be fabricated. Preserve ODbL 1.0,
attribution, Public Domain metadata notices and all source/checksum locks;
raw/generated tables remain ignored and must not be committed.

## Integration ownership and acceptance checklist

| Owner | Consume / next work |
| --- | --- |
| Person 1 | Graph, UTF-8 import, BFS, Q1/Q2, maintained v1 contract and regressions. This phase completes backend integration/handoff. |
| Person 2 | Link `airline_graph` and pass `const Graph&` to new Q3/Q4 modules. Implement and test shortest closed walk for Q3 (exact small graphs, clearly labeled approximation if needed for large), and directed-distance meeting-city minimization for Q4. Agree on distinct-origin exclusion and deterministic ties; handle no solution. Own algorithm tests and future CLI/schema integration. |
| Person 3 | Own PySide6 GUI, Folium/Qt WebEngine and packaging. Use a worker to invoke the JSON adapter, select the correct executable per platform/configuration, and join response IDs/labels to matching metadata. Own map rendering, cancellation and visible error states. |

Q3/Q4 have **no implemented entry points, CLI flags, JSON outputs or GUI
controls** in this handoff. Define those with the team before extending the
backend. Do not claim the entire application is complete or alter Q1/Q2
algorithms to hold GUI state.

- Build Debug and Release; run all eight offline CTest targets and all 46
  Python tests, zero skips. Run sixteen CTest targets when global data exists.
- Check found, unreachable and strict-limit responses; unknown labels, malformed
  data, empty input, required-city aliases, one-way edges and deterministic ties.
- Parse stdout with Python stdlib `json.loads`; it contains one object. Treat
  exit 1/error separately from valid exit 0/no-result; keep stderr as diagnostics.
- Verify Unicode and spaces in labels and file paths; pass argument lists with
  `shell=False`. Exercise the tested `examples/backend_client.py` first.
- Use the same metadata as the backend; verify each returned ID/label pair and
  latitude/longitude order. Clearly label sample/historical data on maps.
- Preserve teammate files, commit history, dataset locks, source pins and
  licenses. Review the Phase 7 draft PR; the user approves any merge separately.
