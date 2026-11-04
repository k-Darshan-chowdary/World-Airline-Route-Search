#pragma once
#include "Graph.h"
#include <cstddef>
#include <string>
#include <vector>

namespace airline {

enum class RoundTripStatus { Found, NoTour, HeuristicFailed };
enum class RoundTripMethod { Exact, Heuristic };

struct RoundTripResult {
    RoundTripStatus status = RoundTripStatus::NoTour;
    RoundTripMethod method = RoundTripMethod::Exact;
    // The path begins and ends at start and visits every vertex reachable
    // from start. Repeated cities are permitted, but the starting city must
    // not be revisited before the final step. Large graphs have a provably\n    // feasible (or impossible) answer but not necessarily minimum flights.
    std::vector<CityId> path;
    std::size_t reachableCities = 0;
    std::size_t flights = 0;
};

// Q3: shortest closed directed walk visiting all vertices reachable from
// start. For up to 18 reachable cities uses exact BFS over (city, visited mask).\n// Larger graphs are decomposed into strongly connected components after\n// removing the start. The condensation DAG establishes whether any valid\n// end-only tour exists; if so, BFS constructs one, but its length is NOT\n// necessarily minimal. NoTour means proven impossible.\n// HeuristicFailed is retained for JSON API compatibility but is not emitted\n// by the component-based implementation.
RoundTripResult findRoundTrip(const Graph& graph, CityId start);
RoundTripResult findRoundTrip(const Graph& graph, const std::string& start);
} // namespace airline
