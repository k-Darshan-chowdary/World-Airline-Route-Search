# Backend integration contract v1

Maintained interface for Person 2 (C++ algorithms) and Person 3 (Python GUI).
Contract revision: **1**, introduced in Phase 7; subprocess `schema_version`
remains **1** from Phases 5/6. Headers are the authoritative signatures. This
document records source-level behavior, not a binary ABI or shared-library API.
Recompile consumers with the same C++17 toolchain. Any incompatible field,
type, status or semantic change requires a new JSON schema version and review;
additive fields may be introduced, so consumers should tolerate unknown keys.
Run `cpp_backend_contract` when changing this contract or the CLI.

## C++ surface for Person 2

Link the existing CMake target `airline_graph`; its public include directory
is `cpp/include`. All types/functions below are in namespace `airline`.

| Header / surface | Types and behavior |
| --- | --- |
| `Graph.h`: `CityId` | `int`, zero-based insertion ID; loaded IDs equal data-row indices in `cities.tsv`, excluding its header. Stable for the lifetime of that graph; not a global airport/city identifier. |
| `Coordinates` | `double latitude`, `double longitude`, finite decimal degrees. |
| `Graph::addCity(const std::string&, Coordinates)` | Returns a new `CityId`; rejects empty/whitespace-only names, tab/CR/LF, duplicate exact labels and invalid coordinates with `std::invalid_argument`; ID capacity exhaustion throws `std::length_error`. Programmatic callers must supply UTF-8; strict file validation belongs to `loadGraph`. |
| `Graph::addEdge(CityId source, CityId destination)` | Directed edge only. Returns `true` on insertion, `false` for a duplicate. Self-loop throws `std::invalid_argument`. |
| `Graph::sortNeighbors()` | Sorts each adjacency list by ascending city ID. Call after constructing a graph for reproducible BFS ties; the loader already does this. |
| `Graph::cityId(const std::string&) const` | `std::optional<CityId>`; exact, case-sensitive byte lookup; absent for unknown label. No spelling, accent, whitespace or Unicode normalization. |
| `Graph::cityName(CityId) const` | `const std::string&`, exact stored label. |
| `Graph::coordinates(CityId) const` | `Coordinates` by value. |
| `Graph::neighbors(CityId) const` | `const std::vector<CityId>&`, outgoing neighbors. |
| `Graph::hasEdge(CityId, CityId) const` | `bool`; checks the requested direction only. |
| `Graph::cityCount() const noexcept`, `routeCount() const noexcept` | `std::size_t`; unique vertices / directed edges. |
| `GraphLoader.h`: `loadGraph(const std::filesystem::path&)` | Returns `Graph` by value from `cities.tsv` and `flight.txt`; throws `std::runtime_error` for file/data errors, usually including UTF-8 filename and line number. |
| `BFS.h`: `bfs(const Graph&, CityId source)` | Returns `BFSResult {CityId source; std::vector<int> distance; std::vector<CityId> parent;}`. Exact unweighted shortest directed distances; `-1` for unreachable distances, and for source/unreachable parents. |
| `BFSResult::reachable(CityId) const` | `bool`. |
| `BFSResult::pathTo(CityId) const` | `std::vector<CityId>`; inclusive endpoints, empty if unreachable, `[source]` for source to itself. |

Graph ID accessors, `addEdge`, BFS source and BFSResult destination reject
negative/out-of-range IDs with `std::out_of_range`. Keep graphs and BFS results
consistent: do not mutate public result arrays or mutate the graph during a
query. References from accessors depend on graph lifetime and can be invalidated
by mutation. Treat the shared graph as `const Graph&` inside teammate algorithms.
Do not infer incoming edges from `neighbors`; build a separate reversed graph
if an algorithm needs one. A→M and M→A are different distances.

Storage is adjacency vectors plus hash label/edge indexes: O(V+E) space,
expected O(1) label/edge lookup, O(outdegree) neighbor enumeration. BFS uses a
queue, distance and parent arrays: O(V+E) time, O(V) additional space. On sorted
neighbors, the first BFS parent wins in city-ID order, not alphabetic label order
unless metadata itself happens to be alphabetically ordered.

### Q1 and Q2 APIs owned by Person 1

```cpp
#include "GraphLoader.h"
#include "BFS.h"
#include "RouteSearch.h"
#include "RequiredStops.h"

const auto graph = airline::loadGraph("data/sample");
const auto q1 = airline::searchRoute(graph, "Dallas, United States",
                                    "New York, United States", 1);
const auto q2 = airline::searchRequiredStops(graph, "Dallas, United States",
    "New York, United States", "London, United Kingdom", "Paris, France");
// Person 2 can reuse graph.neighbors(id) and airline::bfs(graph, id).
```

`RouteSearch.h` declares `searchRoute(const Graph&, CityId source, CityId
destination, std::int64_t exclusiveLimit)` and an overload replacing both IDs
with `const std::string&`. `RouteSearchResult` fields:

- `RouteSearchStatus status`: `Found`, `Unreachable`, `ConnectionLimit`.
- `std::vector<CityId> path`: populated only for `Found`.
- `std::optional<int> flights`, `connections`: shortest-route counts even for
  `ConnectionLimit`, absent for `Unreachable`.

Q1 minimizes edges, then accepts only `connections < exclusiveLimit`.
Connections = `max(flights - 1, 0)`; a direct edge has zero connections. A→A
has zero flights and zero connections, and qualifies only for positive limits.
Zero is valid and yields no qualifying routes; it does not make an unreachable
pair reachable. Negative API limits throw `std::invalid_argument`.

`RequiredStops.h` declares `searchRequiredStops(const Graph&, CityId from,
CityId viaB, CityId viaC, CityId to)` and an overload replacing all four IDs
with `const std::string&`. `RequiredStopsResult` fields:

- `RequiredStopsStatus status`: `Found`, `Unreachable`.
- `std::vector<CityId> path`: minimum directed **walk** through both required
  vertices; repeated vertices are allowed.
- `std::vector<CityId> waypointOrder`: distinct required vertices in actual
  first-encounter order, including source/destination when required. If B=C,
  one entry. An incidental early encounter can reverse the segment order.
- `std::optional<std::int64_t> flights`, `connections`: absent when unreachable;
  both vectors are then empty. Connections use the same formula as Q1.

Q2 compares shortest A→B→C→D and A→C→B→D segment concatenations using BFS from
A/B/C. Equal lengths prefer the B→C segment candidate, then BFS parent ties.
The reported waypoint order follows the returned walk, not this decomposition.
A/B/C/D may be the same vertex; all equal yields a singleton walk. It requires
all three directed segments for at least one order to exist. Q1 and Q2 are each
O(V+E) time, O(V) auxiliary space. Unknown exact labels throw
`std::invalid_argument`; invalid IDs throw `std::out_of_range`.

## Files and metadata for both teammates

The loader requires UTF-8 (optional BOM at file start), accepts LF/CRLF, and
validates Unicode scalars, labels and finite in-range decimal coordinates.
`cities.tsv` has exactly `city<TAB>latitude<TAB>longitude` as its header. Each
subsequent row has three fields; blank metadata rows are errors. Labels follow
`City, Country` with exactly one comma-space separator, no leading/trailing
space or embedded tab/newline. Duplicate labels, unused metadata, unknown
route endpoints, self-loops and duplicate directed edges are errors.
`flight.txt` has two TAB-separated exact labels per edge, no header. Blank
lines and lines with first non-space/tab character `#` are ignored. At least
one city and one edge are required. One-way edges are valid.

Map join: enumerate metadata data rows from zero and verify
`cities[node.id].city == node.city` for every response node. Never combine
sample IDs with global metadata or persist IDs across different datasets.
JSON v1 does **not** return coordinates, airports, weights or a city catalog;
read the same `cities.tsv` locally with Python `csv.DictReader(delimiter='\t')`,
encoding `utf-8-sig`. Use latitude then longitude (Folium's order), decimal
degrees, without swapping them. Sample IDs include Dallas=0, New York=1,
London=2, Paris=3; Dallas sample coordinates are `(32.7767, -96.7970)`.

For the locked official data, `cities.tsv` coordinates are approximate
representative-airport marker positions, rounded to six decimals. Join
`city_representatives.tsv` (`city`, `representative_airport_ident`) to
`airports.tsv` by `ident` for provenance. They do not locate every city route's
actual airport or represent live aircraft positions. Example: official ID 0
is Aalborg, Denmark, `(57.094763, 9.849930)`, representative EKYT. Sample
coordinates instead approximate city centers. The contract tests check every
official representative-coordinate join within 0.00000051 degrees rounding.

## CLI and subprocess JSON v1 for Person 3

The executable is `airline_graph` (`.exe` on Windows). Pass an argument **list**
to `subprocess.run`, `shell=False`, `capture_output=True`, `encoding='utf-8'`,
`errors='strict'`, and a finite timeout. Use absolute executable/data paths to
avoid dependence on the GUI working directory. Windows uses native UTF-16
arguments converted to UTF-8; Unix callers must send UTF-8 arguments.

| CLI options | Behavior |
| --- | --- |
| `--data-dir DIR` | Directory with both input tables. Default `data/generated/2026-q3`, relative to process working directory. |
| `--expect-cities N`, `--expect-routes N` | Optional exact count checks, nonnegative decimal digits fitting platform `size_t`. These alone do not verify dataset hashes. |
| `--from LABEL --to LABEL` | Both required together. Alone selects Phase 4 human-readable BFS. |
| `--max-connections X` | Select Q1; decimal digits only, inclusive input range 0..9223372036854775807; leading zeros accepted. No sign, spaces, float or exponent. |
| `--via-b LABEL --via-c LABEL` | Select Q2; both required with from/to; mutually exclusive with max-connections. |
| `--json` | Q1/Q2 structured output; without either query selector returns an error. |
| `--help` | Exit 0 without opening a dataset. Plain usage normally; with `--json`, a v1 help object. |

Unknown flags/missing values are errors. For compatibility, repeated value
options retain the last value, and repeated `--json` is harmless. Emit each
option once in integrations. The parser processes arguments left to right;
`--help` returns when encountered, after any preceding argument validation.

In JSON mode stdout contains **exactly one UTF-8 JSON object and a trailing
newline**, including help and handled failures. No banner/debug text appears
there. Quotes, backslashes and control characters are escaped. Invalid UTF-8
arguments are rejected; malformed diagnostic bytes are replaced with U+FFFD
inside JSON. Human diagnostics go to stderr; successful queries have empty
stderr. Object member ordering is not an API promise. Paths/ties are
deterministic for identical metadata/edges, even if edge rows are reordered.

| Exit code | Meaning |
| --- | --- |
| `0` | Valid query result (including no route/over limit) or help. |
| `1` | Handled invalid input, failed count check, loading/format error or other caught standard exception. JSON error object plus `ERROR: ...` on stderr. |

OS launch failure, process crash, pipe failure, forced termination and timeout
are transport failures outside the response guarantee; handle them separately.
There are no numeric application error codes. Error `message` is a nonempty
human string, not a stable machine classifier; do not match full text/paths.

### Field names and types

| Field | Type / presence |
| --- | --- |
| `schema_version` | Integer `1`, all objects. |
| `status` | String, all objects; conditions below. |
| `query` | String `"q1"` or `"q2"`, query results only. |
| `from`, `to` | Exact input strings, query results only. |
| `exclusive_connection_limit` | Integer X, Q1 results only. |
| `via_b`, `via_c` | Exact input strings, Q2 results only. |
| `flights`, `connections` | Nonnegative integers or JSON `null`, query results only. Q2 counts can exceed a 32-bit integer; preserve integer precision. |
| `historical_observed_connectivity` | Boolean `true`, all query results, including the synthetic sample. This is a caution flag, not proof that synthetic routes were observed. |
| `route` | Array of `{ "id": nonnegative integer, "city": string }`, query results only; includes both endpoints and any repeated visits. |
| `waypoint_order` | Array of the same city-node objects, Q2 only. |
| `message` | Nonempty string, `status="error"` only. |
| `usage` | Nonempty string, `status="help"` only. |

| Status | Conditions / result invariants |
| --- | --- |
| `found` | A qualifying walk exists. `route.length = flights+1`; endpoints match from/to; counts non-null. Q2 includes both required labels, with actual first-encounter waypoint order. |
| `unreachable` | No directed A→D path for Q1, or no A→D walk through both required cities for Q2. Counts null, route empty, Q2 waypoint_order empty. |
| `connection_limit` | Q1 only: a directed path exists, but its minimum connections >= X. Counts describe that shortest path; route empty. |
| `error` | Invalid query/dataset; only schema_version, status, message. No query-specific fields. Exit 1. |
| `help` | Only schema_version, status, usage. Exit 0. Phase 7 makes combined --help/--json parseable; ordinary --help and all Q1/Q2 result shapes remain unchanged. |

### Exact runnable examples and results

From repo root, PowerShell, MSVC Debug (MinGW uses `build\airline_graph.exe`):

```powershell
.\build\Debug\airline_graph.exe --data-dir "data/sample" --from "Dallas, United States" --to "New York, United States" --max-connections 1 --json
.\build\Debug\airline_graph.exe --data-dir "data/sample" --from "Dallas, United States" --to "Paris, France" --via-b "New York, United States" --via-c "London, United Kingdom" --json
# Unicode is exact: this official label is São Paulo, not Sao Paulo.
.\build\Debug\airline_graph.exe --data-dir "data/generated/2026-q3" --from "São Paulo, Brazil" --to "São Paulo, Brazil" --max-connections 1 --json
```

The first two sample results are:

```json
{"schema_version":1,"query":"q1","status":"found","from":"Dallas, United States","to":"New York, United States","exclusive_connection_limit":1,"flights":1,"connections":0,"historical_observed_connectivity":true,"route":[{"id":0,"city":"Dallas, United States"},{"id":1,"city":"New York, United States"}]}
```

```json
{"schema_version":1,"query":"q2","status":"found","from":"Dallas, United States","to":"Paris, France","via_b":"New York, United States","via_c":"London, United Kingdom","flights":3,"connections":2,"historical_observed_connectivity":true,"route":[{"id":0,"city":"Dallas, United States"},{"id":1,"city":"New York, United States"},{"id":2,"city":"London, United Kingdom"},{"id":3,"city":"Paris, France"}],"waypoint_order":[{"id":1,"city":"New York, United States"},{"id":2,"city":"London, United Kingdom"}]}
```

Changing the first command's limit to `0` yields:

```json
{"schema_version":1,"query":"q1","status":"connection_limit","from":"Dallas, United States","to":"New York, United States","exclusive_connection_limit":0,"flights":1,"connections":0,"historical_observed_connectivity":true,"route":[]}
```

Q1 Auckland→Dallas on the sample with limit 100 yields:

```json
{"schema_version":1,"query":"q1","status":"unreachable","from":"Auckland, New Zealand","to":"Dallas, United States","exclusive_connection_limit":100,"flights":null,"connections":null,"historical_observed_connectivity":true,"route":[]}
```

Q2 Auckland→Dallas via London/Tokyo yields:

```json
{"schema_version":1,"query":"q2","status":"unreachable","from":"Auckland, New Zealand","to":"Dallas, United States","via_b":"London, United Kingdom","via_c":"Tokyo, Japan","flights":null,"connections":null,"historical_observed_connectivity":true,"route":[],"waypoint_order":[]}
```

Unknown exact city labels return exit 1, for either query:

```json
{"schema_version":1,"status":"error","message":"city not found in dataset (exact label required)"}
```

For names containing quotes/backslashes, prefer the argument-list adapter;
shell quoting rules differ across PowerShell, cmd and POSIX shells. Linux
equivalents use `./build/airline_graph` with the same quoted arguments.

## Reusable Python consumer

From repo root, the tested stdlib-only `examples/backend_client.py` supplies:

```python
from examples.backend_client import query_backend, BackendError, BackendProtocolError

q1 = query_backend("build/Debug/airline_graph.exe", "data/sample",
    from_city="Dallas, United States", to_city="New York, United States",
    exclusive_connection_limit=1)
q2 = query_backend("build/Debug/airline_graph.exe", "data/sample",
    from_city="Dallas, United States", to_city="Paris, France",
    via_b="New York, United States", via_c="London, United Kingdom")
```

It checks required types/version, counts, statuses, route endpoints, waypoint
order, return code and echoed query. Valid no-result statuses return normally.
`BackendError` exposes `.payload` and `.stderr`; `BackendProtocolError` means
the response violated the contract. `FileNotFoundError`, `UnicodeError` and
`subprocess.TimeoutExpired` propagate for caller handling. It does not verify
dataset membership/edges or lock hashes; use the same local metadata and setup
verifier. This synchronous helper belongs in a GUI worker; Person 3 chooses
Qt threading/cancellation and user-facing error presentation.

## Team extension boundary

Person 2 implements Q3/Q4 in separate headers/source/tests against `const
Graph&`. Q3 must return to A after visiting every reachable city; directed
return paths may not exist, and any large-graph approximation must be clearly
labeled. Q4 uses directed distances from A/B/C to a different meeting city;
unreachable candidates and tie policy must be explicitly defined/tested.
Neither algorithm, CLI flag nor JSON schema for Q3/Q4 exists yet. Agree on
those contracts with Person 3 before adding them. Preserve the Q1/Q2 schemas
and algorithms; do not repurpose their fields.

Person 3 owns PySide6, Folium and Qt WebEngine, rendering, interaction and
packaging. Consume Q1/Q2 via this subprocess contract and join local metadata;
do not edit Person 1 algorithms to accommodate GUI state. All screens must
identify synthetic sample or **incomplete historical observed connectivity**;
there are no fares, available seats, booking links or live-flight guarantees.
