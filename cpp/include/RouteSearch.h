#pragma once

#include "Graph.h"
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace airline {

enum class RouteSearchStatus { Found, Unreachable, ConnectionLimit };

struct RouteSearchResult {
    RouteSearchStatus status;
    // Only qualifying routes contain city IDs. Counts describe the shortest
    // route even when it exceeds the limit; unreachable counts are absent.
    std::vector<CityId> path;
    std::optional<int> flights;
    std::optional<int> connections;
};

// Q1: minimize flight legs, then require max(legs - 1, 0) < exclusiveLimit.
// A source-to-itself route has zero flights and zero connections.
// Throws invalid_argument for negative limits or unknown labels, out_of_range
// for invalid IDs. Zero is a valid limit with no qualifying routes.
// O(V + E) time, O(V) extra space; ties follow BFS adjacency order. Graphs
// loaded by loadGraph have neighbors sorted by stable metadata city ID.
RouteSearchResult searchRoute(const Graph& graph, CityId source,
                              CityId destination, std::int64_t exclusiveLimit);
RouteSearchResult searchRoute(const Graph& graph, const std::string& source,
                              const std::string& destination, std::int64_t exclusiveLimit);

}  // namespace airline
