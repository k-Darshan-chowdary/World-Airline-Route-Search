# Phase 5 Question 1

Person 1's Question 1 is implemented on `feature/phase5-q1-route-search`,
starting at merged Phase 4 `main` commit
`4cbf979a2306eb63130e00333e09371fca219b0a`. Phases 1–4 are preserved.
Phase 5 is merged through PR #6 at `0bf82691a1365da02a052c7bb19fe0533fdd23a8`.
Question 2 is now covered in [Phase 6](phase6_q2.md); the evidence below records
the original Phase 5 validation. Other teammates' algorithms, GUI and maps
remain future work.

## Assignment and semantics

Q1 wording supplied for this phase:

> I am in city A, can I fly to city B with less than x connections? Give me
> the route with the smallest number of connections or tell me there is no
> such a route.

The repository's `Airline_Team_Roles.docx` assigns shortest A-to-B search with
a connection limit to Person 1 and JSON integration to Person 3. The document
is a team responsibility summary, not a separate full professor assignment.

A connection means an **intermediate city/transfer**, rather than a flight leg.
For distinct endpoints and a route with L flight legs:

```text
connections C = L - 1
qualifies     = C < x        (strictly fewer, not at most)
```

A direct flight has L=1, C=0. A deliberate same-city policy accepts the
singleton route `[A]` with L=0, C=0; it does not search for a returning cycle.
For all routes we therefore use C=max(L-1, 0).

| Query | Shortest flights | Connections | x | Result |
| --- | ---: | ---: | ---: | --- |
| Direct A → B | 1 | 0 | 0 | No qualifying route: connection limit |
| Direct A → B | 1 | 0 | 1 | Found |
| A → M → B | 2 | 1 | 1 | No qualifying route: connection limit |
| A → M → B | 2 | 1 | 2 | Found |
| A = B | 0 | 0 | 0 | No qualifying route: connection limit |
| A = B | 0 | 0 | 1 | Found: `[A]` |
| No directed path | — | — | Any valid x | No qualifying route: unreachable |

Zero is valid but cannot admit a route. Negative limits are invalid. The CLI
accepts decimal digits only, including leading zeros, in the inclusive range
0 through 9223372036854775807 (signed 64-bit). Signs, whitespace, fractions,
exponents, empty values, trailing junk and overflow are errors. City labels
are exact, case-sensitive UTF-8 strings from metadata; neither trimming nor
Unicode normalization is applied. Unknown cities are errors even for x=0.
Reverse routes exist only when an input directed edge provides them.

## Reusable API and correctness

`cpp/include/RouteSearch.h` and `cpp/src/RouteSearch.cpp` expose:

```cpp
airline::searchRoute(graph, sourceId, destinationId, exclusiveLimit);
airline::searchRoute(graph, sourceLabel, destinationLabel, exclusiveLimit);
```

The bound is `std::int64_t`. Invalid IDs throw `std::out_of_range`; unknown
labels or negative bounds throw `std::invalid_argument`. Valid searches return
`RouteSearchResult` with typed `Found`, `Unreachable` or `ConnectionLimit`
status, a vector of city IDs, and optional integer flight/connection counts.
Only `Found` contains a path. Over-limit results include shortest-route counts
for diagnostics; unreachable results have absent counts. IDs remain tied to
metadata insertion order in the loaded graph.

The algorithm uses the existing unweighted BFS and reconstructs its parent
path. BFS minimizes flight legs L. For distinct endpoints C=L-1 is monotonic,
so this also minimizes connections. If the shortest route fails C<x, every
longer route fails as well. The same-city rule is checked by the same formula.
No enumeration of longer paths is necessary.

Time is O(V+E), with O(V) traversal storage and O(path length) reconstruction.
The graph and its metadata are not copied or modified. Ties follow existing
BFS adjacency order. The loader sorts neighbors by stable city ID, giving a
deterministic smallest-ID-first traversal for identical metadata, even if
route input lines are reordered. API callers constructing a graph themselves
should call `sortNeighbors()` for this same ordering.

## CLI and JSON

All previous Phase 4 invocations and plain-text output remain available.
Adding `--max-connections X` selects Q1; `--from` and `--to` are both required.
`--json` requires Q1. Dataset defaults and expected-count options are preserved.

```powershell
# Direct route: zero connections is strictly less than one.
.\build\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --to "New York, United States" --max-connections 1

# The preserved sample's shortest Dallas–Auckland route has 9 flights and
# 8 connections. x=8 fails; x=9 succeeds.
.\build\airline_graph.exe --data-dir data/sample --from "Dallas, United States" --to "Auckland, New Zealand" --max-connections 9 --json

# Official observed dataset, with count checks.
.\build\airline_graph.exe --expect-cities 819 --expect-routes 19283 --from "Aalborg, Denmark" --to "Aalborg, Denmark" --max-connections 1 --json
```

A direct sample query with `--json` emits exactly one UTF-8 JSON object on
stdout (no text banner):

```json
{"schema_version":1,"query":"q1","status":"found","from":"Dallas, United States","to":"New York, United States","exclusive_connection_limit":1,"flights":1,"connections":0,"historical_observed_connectivity":true,"route":[{"id":0,"city":"Dallas, United States"},{"id":1,"city":"New York, United States"}]}
```

`status` is `found`, `unreachable`, or `connection_limit`. Both no-result
statuses have an empty `route`; unreachable counts are `null`, whereas
connection-limit counts describe the shortest nonqualifying route. All valid
search outcomes exit 0, including no-result. Invalid input or loading/count
failure exits 1 with `ERROR:` on stderr. JSON mode also emits a single error
object such as `{"schema_version":1,"status":"error","message":"..."}`.
`--help` exits 0 and prints usage without opening files, including with
`--json`; it is not a JSON request.

JSON escapes quotation marks, backslashes and ASCII controls, preserves UTF-8,
and needs no third-party C++ dependency. On Windows the executable uses the
native wide-character entry point and converts arguments to UTF-8 explicitly,
so non-ASCII city labels and dataset paths work regardless of ANSI code page.
MinGW links with `-municode`; MSVC uses its native `wmain` support. Python callers
should capture output with `encoding="utf-8"`, parse stdout with `json.loads`,
and check the exit code/status before reading a route. The exact 64-bit bound
is representable by Python integers; consumers using floating-point JSON
numbers must take care with bounds above 2^53-1.

Routes represent historical observed connectivity, not current/bookable
flights. The official source is the checksum-locked 2026 Q3 observed MrAirspace
and OurAirports dataset: 819 cities, 19,283 directed routes, 85 countries or
territories. Source pins, hashes, attribution, licenses, provenance and the
12-city/20-route synthetic fixture are unchanged. No generated/raw data is
added to Git.

## Build and verification

Use [the Phase 4 compiler/environment instructions](phase4_cpp.md). The same
CI matrix runs Linux/GCC and Windows/MSVC in Debug and Release, with the two
preserved Python jobs. Q1 targets are part of normal CTest; no worldwide
download or extra C++ dependencies are needed for CI.

```powershell
.\.venv\Scripts\cmake.exe -S . -B build -DAIRLINE_GLOBAL_DATA_DIR:PATH=data/generated/2026-q3
.\.venv\Scripts\cmake.exe --build build --parallel 2
.\.venv\Scripts\ctest.exe --test-dir build --output-on-failure --no-tests=error
.\.venv\Scripts\python.exe scripts/run_tests.py
```

There are five offline CTest targets, or ten with the optional global dataset.
The global fixture verifies the committed checksum lock before any global
algorithm/CLI target runs. Run Release in the separate `build-release`
directory as described in Phase 4. For Visual Studio generators pass
`--config Debug` / `--config Release` and `-C Debug` / `-C Release`.

Tests cover equality and adjacent thresholds, direct/multi-flight routes,
shortest versus longer alternatives, zero-flight same-city queries, invalid
bounds/IDs/labels, Unicode labels and directories, JSON escaping/error output,
directed and disconnected routes, and deterministic ties. A small-graph
Floyd–Warshall oracle checks all endpoint pairs independently of BFS. Global
Q1 tests check every source's self/direct/farthest-reachable boundaries and an
unreachable destination when present. Preserved Phase 4 tests certify BFS
shortest distances from all 819 sources; the global CLI test independently
computes Python BFS expectations for real multi-flight/unreachable cases.

Local executed verification on 2026-10-26, Windows PowerShell, MSYS2 UCRT64
GCC 16.2.0, CMake/CTest 4.4.4 and CPython 3.13.1:

| Check | Debug | Release |
| --- | --- | --- |
| All CTest targets including verified global data | 10/10 passed | 10/10 passed |
| Q1 C++ unit/sample checks | 579 passed | 579 passed |
| Global Q1 checks, all 819 sources | 20,679 passed | 20,679 passed |
| Preserved graph/BFS global checks | 31,192,104 passed | 31,192,104 passed |
| Preserved CLI tests | 11 passed | 11 passed |
| Q1 offline CLI tests / with global CLI test | 8 / 9 passed | 8 / 9 passed |

The original Python suite passed 46 tests with zero failures, errors or skips.
Sample validation, source-pin consistency and full generated-output lock
verification passed. Local logs remain in the ignored build directories.
The restricted runner required a writable workspace TEMP/TMP directory for
new temporary Unicode fixtures; no product change was needed for that setting.
Linux/GCC and Windows/MSVC outcomes are reported by GitHub Actions on the PR;
local compilation here uses Windows GCC, not local MSVC or Linux.
