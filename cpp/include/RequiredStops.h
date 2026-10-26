#pragma once
#include "Graph.h"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace airline {

enum class RequiredStopsStatus { Found, Unreachable };

struct RequiredStopsResult {
    RequiredStopsStatus status = RequiredStopsStatus::Unreachable;
    std::vector<CityId> path;
    // Distinct required cities in first-encounter order on the returned walk.
    // Includes the source/destination when required; B=C appears only once.
    std::vector<CityId> waypointOrder;
    std::optional<std::int64_t> flights;
    std::optional<std::int64_t> connections;
};

// Q2: shortest directed walk from A to D that includes B and C in either
// order. Ties prefer the B-then-C segment candidate, then BFS adjacency order.
// A segment may encounter the other required city early; waypointOrder reports
// actual first encounters, not the chosen segment decomposition.
// Flight legs count as edges;
// intermediate connections = max(legs - 1, 0).
// Repeated cities are allowed, since a directed walk need not be a simple path.
// Invalid IDs throw out_of_range; unknown exact labels throw invalid_argument.
// Aliased A/B/C/D labels are supported. Unreachable results have empty vectors
// and absent counts. Sort graph neighbors for stable metadata-ID BFS ties.
// Uses BFS from A, B, and C: O(V+E) time and O(V) auxiliary space.
RequiredStopsResult searchRequiredStops(const Graph& graph, CityId from,
                                         CityId viaB, CityId viaC, CityId to);
RequiredStopsResult searchRequiredStops(const Graph& graph, const std::string& from,
                                         const std::string& viaB, const std::string& viaC,
                                         const std::string& to);
} // namespace airline
