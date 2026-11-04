# Q3 and Q4 algorithms

## Q3: start in A, visit every reachable city, return to A only at the end

- A vertex is a city, a directed edge is one observed city-to-city connection.
- **Feasibility:** Run BFS from A to determine reachable cities. Construct a reverse adjacency list and BFS backward from A. If any reachable city cannot reach A, no closed walk satisfying the requirement exists. This is an actual impossibility proof, not merely a failed search; however, passing this reverse-reachability check does not prove a tour exists **without an early return to A**.
- **Small graph (up to 18 A-reachable cities):** An exact BFS over states
  `(current city, visited-city bitmask)` explores each directed flight.
  Returning to A is forbidden until every reachable city has been visited.
  BFS returns the fewest flight legs or proves that no valid end-only tour
  exists. The worst-case number of states is O(V × 2^V); memory and runtime
  grow exponentially. The 18-city limit bounds the memory used by the
  exact search.
- **Larger graph (19 or more A-reachable cities):** Remove A and calculate
  strongly connected components (SCCs). Collapse the remaining graph into
  a DAG. A walk can cover all SCCs without revisiting A only when the SCC
  DAG admits a directed Hamiltonian path, beginning with an SCC reachable
  from A and ending at an SCC with an edge back to A. In a DAG, a
  Hamiltonian path exists precisely when its topological ordering is
  unique and consecutive components have connecting edges. Therefore
  **feasibility is decided exactly**, even on larger graphs: `no_tour`
  really means no valid route exists.
- If a large-graph tour is feasible, visit the SCCs in that order. Inside
  each SCC, directed BFS paths connect the entry, all its vertices and the
  chosen exit. The constructed walk is always valid but **not guaranteed
  to use the minimum number of flights**. Its JSON result uses
  `method: "heuristic"` and `optimal: false`. The problem is
  computationally difficult in general (NP-hard). This limitation must
  be explained when demonstrating large graphs.
- **Time:** Exact search O(2^V × (V+E)) in the worst case, bounded at
  18 reachable vertices; SCC construction O(V+E), with additional BFS
  calls used to connect vertices inside SCCs for the larger-graph route.
  The latter is polynomial but may produce extra flights.

C++: `#include "RoundTrip.h"`, call `airline::findRoundTrip(graph, cityId)`. Result fields: `status` (`Found`, `NoTour`, or `HeuristicFailed`—reserved for older compatibility; not currently returned), `method` (`Exact` or `Heuristic`), `path`, `reachableCities`, `flights`.

CLI:
```cmd
build\airline_graph.exe --data-dir data/sample --round-trip "Auckland, New Zealand" --json
```
Expected: exact walk Auckland → Sydney → Auckland, 2 flights.

```cmd
build\airline_graph.exe --data-dir data/sample --round-trip "Dallas, United States" --json
```
Expected: `no_tour`, because some reachable cities cannot return to Dallas.

## Q4: a meeting city different from A, B and C

Run three BFS traversals from origins A, B and C. For every other city M reachable from all three, minimize:

```text
cost(M) = dist(A,M) + dist(B,M) + dist(C,M)
```

Distances are **directed flight legs**, not kilometers, air fares, or undirected hops. Break equal-cost ties by smallest stable city ID. Unreachable candidates are excluded. Time is O(V+E) for three BFS traversals and one city scan; additional space O(V).

C++: `#include "MeetingCity.h"`, call `airline::findMeetingCity(graph,a,b,c)`. Result has optional `city`, optional `totalFlights`, per-origin integer distances, and three reconstructed BFS paths (`pathFromA`, `pathFromB`, `pathFromC`).

CLI:
```cmd
build\airline_graph.exe --data-dir data/sample --meeting-a "Dallas, United States" --meeting-b "New York, United States" --meeting-c "London, United Kingdom" --json
```
Expected: Paris, France, total cost 6 legs (3 + 2 + 1).

## Integration and testing

- Existing Q1/Q2 interfaces and JSON responses are preserved.
- Q3 JSON adds `query:"q3"`, `status`, `method`, `optimal`, `reachable_cities`, `flights` and `route`.
- Q4 JSON adds `query:"q4"`, `status`, `meeting_city`, `total_flights`, `distances`, and three `routes` arrays for blue/orange/purple map polylines. No result uses null meeting city and totals.
- Both queries include `schema_version:1` and historical-observed-connectivity caveat.
- `cpp/tests/test_q34.cpp` exercises the 18-city exact cutoff, 19/50-city routes, greedy-trap cases, branched SCC impossibility, deterministic Q4 ties and directed reachability. `cpp/tests/test_q34_cli.py` checks JSON subprocess outputs on synthetic data.
- Build and test with CMake/CTest, then the preserved dataset Python suite; run official-data checks when the local checksum-locked dataset exists. Cross-platform CI and a live GUI demonstration are required for final acceptance.
- The source is incomplete historical observed connectivity, **not live schedules or bookable flights**.

Person 3's GUI should present heuristic outputs as approximate and never label them as guaranteed optimal.
