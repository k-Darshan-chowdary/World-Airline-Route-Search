#pragma once

#include "Graph.h"
#include <vector>

namespace airline {

struct BFSResult {
    CityId source;
    std::vector<int> distance;  // -1 indicates unreachable
    std::vector<CityId> parent;  // -1 for source or unreachable

    bool reachable(CityId destination) const;
    std::vector<CityId> pathTo(CityId destination) const;
};

// Single-source shortest paths in O(V + E) for unweighted directed routes.
// Ties follow adjacency order; loadGraph sorts neighbors by stable city ID.
// Throws std::out_of_range for invalid source/destination IDs.
BFSResult bfs(const Graph& graph, CityId source);

}  // namespace airline
