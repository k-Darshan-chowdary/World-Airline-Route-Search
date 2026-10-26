# Phase 7 executed validation and compatibility

Executed on **2026-10-26**, in the existing Windows VS Code checkout, starting
from clean Phase 6 work. Fetched `origin/main` at
`aaa014a5abce132e8ba6414566cf54e983f512bc`, then created the new branch
`feature/phase7-backend-handoff` directly from it. No Phase 6 branch was reused,
no user work was reset, and main was not merged/rewritten by Phase 7.
The Phase 6 post-merge [run 40407095285](https://github.com/k-Darshan-chowdary/World-Airline-Route-Search/actions/runs/40407095285)
was independently checked: all six jobs concluded success. That run is the
baseline, not evidence for the new Phase 7 revision.

## Local results

Windows PowerShell, MSYS2 UCRT64 **GCC 16.2.0**, **CMake/CTest 4.4.4**,
**CPython 3.13.1** and the existing hash-locked import environment:

| Check | Debug | Release |
| --- | --- | --- |
| Full CTest suite with official data | **16/16 passed** | **16/16 passed** |
| New offline contract subprocess suite | **14/14 passed** | **14/14 passed** |
| New contract suite including official metadata | **15/15 passed** | **15/15 passed** |
| Existing graph/loader/BFS, Q1/Q2 and CLI regressions | Passed | Passed |
| Existing Q2 small/sample independent oracle | 25,214 queries passed | 25,214 queries passed |
| Existing Q2 global independent oracle | 1,638 queries passed | 1,638 queries passed |

The separate original Python suite passed **46 tests, zero failures/errors/skips**
with network calls blocked by `scripts/run_tests.py`. Source-pin consistency,
sample 12-city/20-edge validation and whitespace checks also passed.

New contract tests launch the actual compiled executable using Python stdlib
`subprocess`/`json`, validate exact current key sets/types, and exercise the
reusable consumer. They check Q1 found/unreachable/strict-limit conditions,
same-city policies, Q2 aliases/waypoint first encounters/revisits, directed
edges, deterministic tie/output behavior, byte-for-byte edge-row reorder
stability, Unicode labels and paths (including a non-BMP label), escaped error
strings, integer boundaries, unknown labels/flags, duplicate options, malformed
and duplicate data, metadata blank-line rejection, route blank/comment lines,
BOM/CRLF, JSON help and failure stdout/stderr/exit codes. All six JSON examples
in the maintained contract are checked against actual subprocess results.
Windows additionally rejects malformed UTF-16 argv; Linux CI tests malformed
UTF-8 argv instead. Neither platform-specific check uses skipped tests.

An independent Python BFS over `(city, required-city visited set)` checks
shortest lengths, independently of C++ Q2's segment decomposition. Returned
nodes join to the matching `cities.tsv` row IDs and real directed edges.
Global checks verify all **819** representative-coordinate joins against
`city_representatives.tsv` and `airports.tsv`, allowing only six-decimal
rounding, plus known Aalborg/EKYT metadata, spread-out returned IDs, an exact
São Paulo Unicode query and real Q1/Q2 London/Tokyo examples.

## Official data evidence and scope

Ran the existing independent lock verifier:

```powershell
.\.venv\Scripts\python.exe scripts/dataset_lock.py --outputs-only --data-dir data/generated/2026-q3
.\.venv\Scripts\python.exe scripts/validate_global.py
.\.venv\Scripts\python.exe scripts/dataset_lock.py --pins-only
.\.venv\Scripts\python.exe scripts/check_phase2.py --expect-cities 12 --expect-edges 20
```

All five tables (`airports.tsv`, `cities.tsv`, `city_representatives.tsv`,
`flight.txt`, `route_provenance.tsv`) and both notices (`ATTRIBUTION.txt`,
`LICENSE-ODbL.txt`) passed the committed SHA-256/byte-length locks. Provenance,
policy, metadata, counts and row accounting passed: **819 cities, 19,283 unique
directed routes, 882 airports, 85 countries/territories**. Both configurations
also execute this verification through CTest's required global fixture.
No raw source was downloaded/regenerated, and this phase does not claim a
fresh full raw-input hash run. The data remain incomplete historical observed
connectivity; synthetic sample edges are never asserted as actual service.

## Reproduction on this existing checkout

```powershell
$env:PATH="C:\msys64\ucrt64\bin;"+$env:PATH
.\.venv\Scripts\cmake.exe -S . -B build -DCMAKE_BUILD_TYPE=Debug -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build --parallel 2
New-Item -ItemType Directory -Force build/tmp
$env:TEMP=(Resolve-Path build/tmp).Path
$env:TMP=$env:TEMP
.\.venv\Scripts\ctest.exe --test-dir build -V --output-on-failure --no-tests=error
.\.venv\Scripts\python.exe scripts/run_tests.py
.\.venv\Scripts\cmake.exe -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build-release --parallel 2
New-Item -ItemType Directory -Force build-release/tmp
$env:TEMP=(Resolve-Path build-release/tmp).Path
$env:TMP=$env:TEMP
.\.venv\Scripts\ctest.exe --test-dir build-release -V --output-on-failure --no-tests=error
```

The first attempt used a restricted system temporary directory and failed on
temporary-file access. Setting TEMP/TMP to the writable build folders resolved
it; all final runs above passed without changing or disabling tests. Detailed
local logs remain ignored in `build/phase7-final.log`,
`build-release/phase7-final.log` and `build/phase7-python.log`.
See [clean-clone MSVC/Linux instructions](team_backend_handoff.md) for a
different machine; these existing build directories already use MinGW.

## Compatibility, CI and remaining work

Q1/Q2 result fields, schema version 1, integer/limit policies, statuses,
algorithm implementations, deterministic parent/order policies, generic
Phase 4 CLI, and ordinary human help are preserved. The deliberate compatibility
fix is combined `--help --json`: it now returns a parseable
`{schema_version:1,status:"help",usage:...}` object with exit 0 rather than raw
usage text. UTF-8 argument validation and UTF-8 path diagnostics protect failure
responses. Invalid platform diagnostic bytes use U+FFFD inside JSON.

The six-job CI workflow remains unchanged. CMake automatically discovers the
new contract target, so Linux/GCC and Windows/MSVC Debug/Release run **eight**
offline CTest targets; two Python jobs retain all 46 original tests. CI never
downloads the worldwide source. The Phase 7 draft PR's current checks and PR
description report the final revision's actual CI status; local Windows/GCC
results above do not stand in for Linux/GCC or Windows/MSVC results.

Diff review against the main baseline confirms no changes to data source pins,
locks, schema, fixture bytes, import/checksum scripts, requirements, license or
attribution files, existing unit/regression test files, public C++ headers or
Person 1 graph/BFS/Q1/Q2 algorithms. The Word dataset guide and team roles
document are preserved byte-for-byte. No raw/generated data are committed.
TEAM_DATASET_SETUP.md gains current integration links and corrects obsolete
branch-status notes; its setup instructions remain intact.

Person 2 must still implement Q3/Q4, with their own algorithm tests and agreed
future CLI/schema. Person 3 must still implement GUI/maps and packaging, worker
execution and UI errors. No Q3/Q4 or GUI/map implementation is supplied by
Phase 7. The PR remains draft/unmerged until the user's separate approval.
