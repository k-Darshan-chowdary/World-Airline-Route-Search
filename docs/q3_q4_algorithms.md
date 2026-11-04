# Q3 and Q4 algorithms — urgent team integration

Work in progress for the November 7 CSCE 2110 submission. The implementation is on a review branch, not yet merged. Person 2 should review, run, and be prepared to explain these algorithms rather than claiming work they did not do.

## Q3: start in A, visit every reachable city, return to A only at the end

- A vertex is a city, a directed edge is one observed city-to-city connection.
- **Feasibility:** Run BFS from A to determine reachable cities. Construct a reverse adjacency list and BFS backward from A. If any reachable city cannot reach A, no closed walk satisfying the requirement exists. This is an actual impossibility proof, not merely a failed search; however, passing this reverse-reachability check does not prove a tour exists **without an early return to A**.
- **Small graph (up to 14 A-reachable cities):** Exact BFS on states `(current city, visited-city bitmask)`; stop when every reachable city was visited and the walk returns to A. Every transition is one flight, so state BFS returns the minimum-flight **closed walk**, allowing revisits of other cities but forbidding A until the final step. Worst case roughly O((V+E) 2^V) time/space on the bounded component.
- **Larger graph:** Greedy BFS-guided heuristic: repeatedly visit the closest not-yet-visited city, append the true directed BFS shortest segment, mark all cities encountered, then return to A. It attempts a walk without revisiting A early, but may get stuck even if another valid ordering exists. Successful output is a valid walk; it **does not promise the global minimum**. The CLI and JSON explicitly label it `heuristic` with `optimal: false`. A full exact minimum on a large directed graph is computationally difficult; the decision to use a heuristic must be disclosed to the instructor if the assignment demands a globally shortest result.

C++: `#include "RoundTrip.h"`, call `airline::findRoundTrip(graph, cityId)`. Result fields: `status` (`Found`, `NoTour`, or `HeuristicFailed`), `method` (`Exact` or `Heuristic`), `path`, `reachableCities`, `flights`.

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
- `cpp/tests/test_q34.cpp` exercises exact/heuristic limits, no-return cases, deterministic Q4 ties and directed reachability. `cpp/tests/test_q34_cli.py` checks JSON subprocess outputs on synthetic data.
- Build and test with CMake/CTest, then the preserved dataset Python suite; run official-data checks when the local checksum-locked dataset exists. Cross-platform CI needs to pass before merge.
- The source is incomplete historical observed connectivity, **not live schedules or bookable flights**.

Person 3's GUI should present heuristic outputs as approximate and never label them as guaranteed optimal.
