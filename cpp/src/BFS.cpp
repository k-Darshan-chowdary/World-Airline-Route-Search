#include "BFS.h"

#include <algorithm>
#include <queue>
#include <stdexcept>

namespace airline {

bool BFSResult::reachable(CityId destination) const {
    if (destination < 0 || static_cast<std::size_t>(destination) >= distance.size()) {
        throw std::out_of_range("invalid destination city ID");
    }
    return distance[destination] >= 0;
}

std::vector<CityId> BFSResult::pathTo(CityId destination) const {
    if (!reachable(destination)) return {};
    std::vector<CityId> result;
    for (CityId cursor = destination; cursor != -1; cursor = parent[cursor]) {
        result.push_back(cursor);
    }
    std::reverse(result.begin(), result.end());
    return result;
}

BFSResult bfs(const Graph& graph, CityId source) {
    // Graph's checked accessor produces a clear error if source is invalid.
    (void)graph.neighbors(source);
    BFSResult result{source, std::vector<int>(graph.cityCount(), -1),
                     std::vector<CityId>(graph.cityCount(), -1)};
    std::queue<CityId> pending;
    result.distance[source] = 0;
    pending.push(source);
    while (!pending.empty()) {
        const CityId here = pending.front();
        pending.pop();
        for (const CityId next : graph.neighbors(here)) {
            if (result.distance[next] != -1) continue;
            result.distance[next] = result.distance[here] + 1;
            result.parent[next] = here;
            pending.push(next);
        }
    }
    return result;
}

}  // namespace airline
