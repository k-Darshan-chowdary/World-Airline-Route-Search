# Phase 6 — Person 1, Question 2

Professor's question:

> Give me the route with the smallest number of connections from city A to D
> which passes cities B and C, in either order.

Merged into `main` through [PR #7](https://github.com/k-Darshan-chowdary/World-Airline-Route-Search/pull/7)
at `aaa014a5abce132e8ba6414566cf54e983f512bc`. The implementation was developed
on `feature/phase6-q2-required-cities` from the merged Phase 5 baseline.
The validation below records that revision; Phase 7 adds the maintained
[backend contract](backend_api_contract.md) and two more CTest targets.

## Semantics and API

```cpp
airline::searchRequiredStops(graph, sourceId, viaBId, viaCId, destinationId);
airline::searchRequiredStops(graph, sourceLabel, viaBLabel, viaCLabel, destinationLabel);
```

`cpp/include/RequiredStops.h` exposes `RequiredStopsResult`:

- `status`: `RequiredStopsStatus::Found` or `Unreachable`.
- `path`: city IDs of the complete directed walk, including endpoints.
- `waypointOrder`: distinct required cities in actual first-encounter order.
- `flights`, `connections`: optional signed 64-bit counts, absent if unreachable.

A flight is one directed edge. Connections are `max(flights - 1, 0)`. The
algorithm minimizes flights; this also minimizes connections. A zero-flight
walk is preferred over a returning cycle when all four cities are equal.
Unreachable results have empty path/order vectors. Invalid IDs in any of the
four positions throw `std::out_of_range`; unknown exact labels throw
`std::invalid_argument`, even if some other segment is unreachable. Labels are
case-sensitive UTF-8 with no trimming or Unicode normalization.

Visits at the source and destination satisfy requirements. A=B, B=C, C=D and
all other aliases are supported. If B=C, the required city appears once in
`waypointOrder`. Repeated visits elsewhere are allowed and retained in `path`:
Q2 searches for the best **walk**, not necessarily a simple path. D may occur
before the final visit to D. No reverse route is invented.

## DSA, correctness and ties

The graph stores directed adjacency lists with a hash table for exact label to
ID lookup. Existing BFS uses a FIFO queue, distance array and parent array.
Three BFS traversals rooted at A, B and C supply all six needed distances:

```text
L_BC = dist(A,B) + dist(B,C) + dist(C,D)
L_CB = dist(A,C) + dist(C,B) + dist(B,D)
```

A candidate is unavailable if any of its segments is unreachable. Reconstruct
each available candidate using BFS parents and concatenate its three segments,
skipping the first node of the second/third segment. This removes duplicate
segment boundaries without removing real repeated visits. Select the shorter
candidate. Equal flight counts prefer the BC **segment candidate**; equal BFS
paths follow adjacency order. Loaded graphs sort neighbors by stable metadata
city ID, so route row reordering cannot change the result. Direct API callers
can call `sortNeighbors()` for the same policy. This does not promise a globally
lexicographically smallest walk among every optimal walk.

Why this is globally optimal even with incidental visits: take any feasible
walk and split it at visits to B and C in their encounter order (aliases allow
zero-length pieces). Each piece is at least its directed shortest distance,
so the relevant candidate sum is at most that walk's length. Conversely, each
available concatenation is itself a feasible walk. The minimum of the two
candidate sums therefore equals the best feasible walk length. A shortest
segment may pass the other required city early; it remains feasible and does
not invalidate the lower-bound argument.

The selected segment order need not equal the order of first encounters. For
edges A→C, C→B, B→C, C→D, both candidates yield A→C→B→C→D. The tie selects BC's
decomposition, but `waypointOrder` correctly reports C then B. This fixes the
WIP implementation's reporting of the selected decomposition as encounter order.

Time is `3 * O(V+E) + O(V) = O(V+E)` and auxiliary storage is `O(V)`.
Each segment has at most V−1 edges; three-segment counts use 64-bit integers
to avoid narrowing their total to a single BFS distance's `int`. Graph storage
is neither copied nor modified. The oracle described below is test-only.

## CLI and JSON

Use both `--via-b` and `--via-c` with `--from` and `--to` to select Q2.
`--max-connections` selects Q1 and cannot be combined with Q2. Q2 has no limit
parameter. Existing Phase 4 commands and Q1 strict-limit behavior are preserved.
`--json` is accepted for either Q1 or Q2.

```powershell
# Synthetic sample, available without downloading worldwide data.
.\build\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --via-b "London, United Kingdom" --via-c "Tokyo, Japan" --to "Auckland, New Zealand" --json

# Official locally verified observed dataset; 3 flights, 2 connections.
.\build\airline_graph.exe --expect-cities 819 --expect-routes 19283 --from "London, United Kingdom" --via-b "Paris, France" --via-c "Dubai, United Arab Emirates" --to "Tokyo, Japan" --json
```

The successful global query emits one UTF-8 object and no banner:

```json
{"schema_version":1,"query":"q2","status":"found","from":"London, United Kingdom","to":"Tokyo, Japan","via_b":"Paris, France","via_c":"Dubai, United Arab Emirates","flights":3,"connections":2,"historical_observed_connectivity":true,"route":[{"id":409,"city":"London, United Kingdom"},{"id":552,"city":"Paris, France"},{"id":211,"city":"Dubai, United Arab Emirates"},{"id":731,"city":"Tokyo, Japan"}],"waypoint_order":[{"id":552,"city":"Paris, France"},{"id":211,"city":"Dubai, United Arab Emirates"}]}
```

`route` is the JSON path, matching Q1's existing field name and city-object
shape. `waypoint_order` uses that same object shape and first-encounter semantics.
Unreachable queries return `status: "unreachable"`, empty `route` and
`waypoint_order`, and `null` counts. All valid outcomes exit 0. Invalid arguments,
unknown cities, malformed data, missing directories or count mismatches exit 1,
print `ERROR:` to stderr and, with `--json`, emit the existing error contract
`{"schema_version":1,"status":"error","message":"..."}` to stdout. `--help`
exits 0 without opening data files. Q1's existing fields and status names remain
unchanged; Q2 omits `exclusive_connection_limit`.

Windows retains the native UTF-16 argument entry point and explicit conversion
to UTF-8, including non-ASCII dataset directories and city names. JSON escapes
quotes, backslashes and ASCII control characters. Python subprocess callers
should use `encoding="utf-8"` and parse stdout with `json.loads`.

Routes represent historical observed connectivity, not current/bookable flights.
The `historical_observed_connectivity` field remains true. Phase 3 source pins,
checksums, licenses, attribution and generated files are unchanged. Raw and
generated data remain ignored. No GUI, maps, Q3/Q4 or Phase 7 work is included.

## Build and reproduce verification

Use [Phase 4's compiler setup](phase4_cpp.md). On this Windows checkout,
`.venv` already supplies CMake, CTest and the hash-locked Python dependencies;
MSYS2 UCRT64 supplies GCC. Keep `C:\msys64\ucrt64\bin` on PATH.

```powershell
# Existing MinGW build directories; each has its compiler/generator configured.
.\.venv\Scripts\cmake.exe -S . -B build -DCMAKE_BUILD_TYPE=Debug -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build --parallel 2
.\.venv\Scripts\ctest.exe --test-dir build --output-on-failure --no-tests=error -V
.\.venv\Scripts\cmake.exe -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build-release --parallel 2
.\.venv\Scripts\ctest.exe --test-dir build-release --output-on-failure --no-tests=error -V
.\.venv\Scripts\python.exe scripts/run_tests.py
.\.venv\Scripts\python.exe scripts/dataset_lock.py --pins-only
.\.venv\Scripts\python.exe scripts/check_phase2.py --expect-cities 12 --expect-edges 20
```

For a fresh Linux/GCC or Windows/MSVC build use `cmake -S . -B build
-DCMAKE_BUILD_TYPE=Debug`, `cmake --build build --config Debug --parallel 2`,
and `ctest --test-dir build -C Debug --output-on-failure --no-tests=error`.
Repeat Release with a separate build directory or MSVC configuration. Add
`-DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3` only when the official
local data exists. Omitting it gives seven offline CTest targets; enabling it
gives fourteen. Q2 adds `cpp_q2_tests`, `cpp_q2_cli`, `cpp_global_q2` and
`cpp_global_q2_cli`. All global consumers require the checksum fixture first;
a missing or changed dataset fails rather than silently skipping.

On a runner that restricts temporary directories, create `build/tmp` and set
`$env:TEMP=(Resolve-Path build/tmp).Path; $env:TMP=$env:TEMP` before tests.
Keep separate temporary directories when testing both configurations concurrently.

## Executed local evidence — 2026-10-26

Windows PowerShell, GCC 16.2.0, CMake/CTest 4.4.4, CPython 3.13.1:

| Check | Debug | Release |
| --- | --- | --- |
| Complete CTest suite, including global fixture | 14/14 passed | 14/14 passed |
| Q2 small/sample oracle queries | 25,214 passed | 25,214 passed |
| Q2 small/sample assertions | 142,010 passed | 142,010 passed |
| Q2 global oracle queries, two from each of 819 sources | 1,638 passed | 1,638 passed |
| Q2 global assertions | 12,407 passed | 12,407 passed |
| Q2 subprocess tests offline / with global checks | 9 / 10 passed | 9 / 10 passed |
| Preserved global graph/BFS assertions | 31,192,104 passed | 31,192,104 passed |
| Preserved Q1 assertions sample / global | 579 / 20,679 passed | 579 / 20,679 passed |
| Preserved Phase 4 / Q1 CLI tests offline / Q1 with global | 11 / 8 / 9 passed | 11 / 8 / 9 passed |

The original Python suite passed **46 tests, zero failures/errors/skips** with
network access blocked by its runner. Source-pin consistency, synthetic sample
counts and whitespace checks passed. Both configurations executed independent
`dataset_lock.py --outputs-only` verification against the committed lock:
SHA-256 and byte lengths for all five generated tables and both attribution/
license notices, followed by provenance/count validation of the 819-city,
19,283-directed-route dataset. This did not re-download or regenerate the raw
1 GB source and does not claim a new raw-input hash verification.

The independent C++ oracle searches `(city, visited-B/C mask)` states, covering
every A/B/C/D tuple of all 64 three-city directed graphs and 32 seeded five-city
graphs. Additional explicit checks cover both permutations, tempting longer
routes, equal-order and equal-parent ties, directed asymmetry, incidental visits,
necessary revisits, all alias patterns, invalid IDs/names in every position,
isolated vertices, and Unicode labels. The Python subprocess tests independently
check returned edges/counts/order and cover malformed arguments, missing/unknown
flags/cities, Unicode directories, JSON escaping, human/error output, sample data
and fixed real global labels plus spread-out global queries.

Detailed local logs are in ignored `build/phase6-debug.log`,
`build-release/phase6-release.log` and `build/phase6-python.log`. GitHub Actions
runs all seven offline CTest targets on Linux/GCC and Windows/MSVC in Debug and
Release, plus the two original Python jobs. Full global tests were executed
locally; CI intentionally performs no worldwide download. See PR #7 checks for
the final pushed revision's CI results. Local compilation uses Windows GCC;
Windows MSVC and Linux GCC validation are supplied by CI.
