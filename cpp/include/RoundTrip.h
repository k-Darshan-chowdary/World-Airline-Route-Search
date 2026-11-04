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
    // from start. Repeated cities are permitted, but the starting city must\n    // not be revisited before the final step.
    std::vector<CityId> path;
    std::size_t reachableCities = 0;
    std::size_t flights = 0;
};

// Q3: shortest closed directed walk visiting all vertices reachable from
// start. For <=14 reachable cities uses exact BFS over (city, visited mask).
// For larger reachable subgraphs uses a deterministic greedy *heuristic*;
// the heuristic does NOT promise a minimum number of flights.
// NoTour is exact for small graphs (or proven if return is impossible).\n// HeuristicFailed means the greedy construction got stuck, NOT proof that\n// no qualifying closed walk exists.
RoundTripResult findRoundTrip(const Graph& graph, CityId start);
RoundTripResult findRoundTrip(const Graph& graph, const std::string& start);
} // namespace airline
