#include "RouteSearch.h"
#include "BFS.h"

#include <algorithm>
#include <stdexcept>

namespace airline {

RouteSearchResult searchRoute(const Graph& graph, CityId source,
                              CityId destination, std::int64_t exclusiveLimit) {
    if (exclusiveLimit < 0) throw std::invalid_argument("connection limit must be nonnegative");
    (void)graph.neighbors(source);
    (void)graph.neighbors(destination);
    const auto traversal = bfs(graph, source);
    if (!traversal.reachable(destination)) {
        return {RouteSearchStatus::Unreachable, {}, std::nullopt, std::nullopt};
    }
    const int flights = traversal.distance[destination];
    const int connections = std::max(flights - 1, 0);
    if (connections >= exclusiveLimit) {
        return {RouteSearchStatus::ConnectionLimit, {}, flights, connections};
    }
    return {RouteSearchStatus::Found, traversal.pathTo(destination), flights, connections};
}

RouteSearchResult searchRoute(const Graph& graph, const std::string& source,
                              const std::string& destination, std::int64_t exclusiveLimit) {
    const auto from = graph.cityId(source);
    const auto to = graph.cityId(destination);
    if (!from || !to) throw std::invalid_argument("city not found in dataset (exact label required)");
    return searchRoute(graph, *from, *to, exclusiveLimit);
}

}  // namespace airline
