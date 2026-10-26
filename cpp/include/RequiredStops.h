#pragma once
#include "Graph.h"
#include <string>
#include <vector>

namespace airline {

enum class RequiredStopsStatus { Found, Unreachable };

struct RequiredStopsResult {
    RequiredStopsStatus status = RequiredStopsStatus::Unreachable;
    std::vector<CityId> path;
    std::vector<CityId> waypointOrder;
    int flights = -1;
    int connections = -1;
};

// Q2: shortest directed walk from A to D that includes B and C in either
// order. Ties prefer the B-then-C candidate. Flight legs count as edges;
// intermediate connections = max(legs - 1, 0).
// Repeated cities are allowed, since a directed walk need not be a simple path.
// Input IDs must exist; duplicated A/B/C/D labels are supported.
// Uses BFS from A, B, and C: O(V+E) time and O(V) auxiliary space.
RequiredStopsResult searchRequiredStops(const Graph& graph, CityId from,
                                         CityId viaB, CityId viaC, CityId to);
RequiredStopsResult searchRequiredStops(const Graph& graph, const std::string& from,
                                         const std::string& viaB, const std::string& viaC,
                                         const std::string& to);
} // namespace airline
