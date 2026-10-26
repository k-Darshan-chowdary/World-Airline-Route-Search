# Phase 4 compilation and test evidence

Verified on 2026-10-26 in Windows PowerShell from the existing Phase 4 branch,
continuing commit `7457404`. The checkout is open in VS Code.

Toolchain: MSYS2 UCRT64 GCC 16.2.0, CMake/CTest 4.4.4, CPython 3.13.1,
PyArrow 23.0.1 (installed from `requirements-import.lock`). CMake generated
MinGW Makefiles. Actual compiler flags included `-std=c++17 -Wall -Wextra
-Wpedantic`, with `-g` for Debug and `-O3 -DNDEBUG` for Release.

Both configurations compiled the graph library, CLI and C++ tests successfully.
The CTest commands and reproduced results are documented in
[phase4_cpp.md](phase4_cpp.md).

| Verification | Debug | Release |
| --- | --- | --- |
| All CTest targets, global enabled | 6/6 passed | 6/6 passed |
| Graph/loader/BFS checks plus sample all-source BFS | 1,125 passed | 1,125 passed |
| CLI regression cases (with parameterized failure inputs) | 11/11 passed | 11/11 passed |
| Official global all-source graph/BFS checks | 31,192,104 passed | 31,192,104 passed |

CTest output:

```text
Verified 12 cities; 20 directed routes; all 12 BFS sources
PASS: 1125 checks
Ran 11 tests
OK
PASS: reviewed dataset pins/checksums verified
Verified 819 cities; 19283 directed routes; all 819 BFS sources
PASS: 31192104 checks
100% tests passed out of 6
```

The independent certificate verifies path endpoints, actual directed edges,
path length and the shortest-distance inequality for every reachable edge.
Reachability is closed under outgoing edges; therefore no reachable city can
be incorrectly reported unreachable. All 819 BFS sources are exercised.

The existing Python runner also completed:

```text
Tests: 46; failures: 0; errors: 0; skipped: 0
```

The preserved sample passed `scripts/check_phase2.py --expect-cities 12
--expect-edges 20`. The global dataset passed `scripts/dataset_lock.py
--outputs-only`, independently checking all five table hashes plus notices,
source identity, counts, representative coordinates and route provenance.
The graph input hashes match the existing lock exactly:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `cities.tsv` | 35,366 | `843a70d1166e0df05283ce224b80267cfceb8893cf736a56e54d62584a933de0` |
| `flight.txt` | 860,742 | `398d9f601d7ae9819cc4d567a72171bc33b4de0f7c0af8d52a16be660cfac30c` |

The generated dataset was copied from the previously verified Phase 3 local
output, then reverified; no raw data was redownloaded or imported in this phase.
It remains ignored by Git. Full CTest logs are retained locally in
`build/Testing/Temporary/LastTest.log` and
`build-release/Testing/Temporary/LastTest.log`.

The committed CI matrix independently compiles and tests Linux/GCC and
Windows/MSVC in Debug and Release without raw downloads. This snapshot records
local executed verification; CI results are available on the draft PR.
