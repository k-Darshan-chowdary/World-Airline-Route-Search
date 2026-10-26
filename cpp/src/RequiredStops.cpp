#include "RequiredStops.h"
#include "BFS.h"

#include <algorithm>
#include <optional>
#include <stdexcept>
#include <utility>

namespace airline {
namespace {
using Path = std::vector<CityId>;
std::optional<Path> concatenate(const BFSResult& first, CityId middle1,
                                const BFSResult& second, CityId middle2,
                                const BFSResult& third, CityId destination) {
    if (!first.reachable(middle1) || !second.reachable(middle2) ||
        !third.reachable(destination)) return std::nullopt;
    Path route = first.pathTo(middle1);
    for (const auto& segment : {second.pathTo(middle2), third.pathTo(destination)}) {
        route.insert(route.end(), segment.begin() + 1, segment.end());
    }
    return route;
}
}

RequiredStopsResult searchRequiredStops(const Graph& graph, CityId from,
                                         CityId viaB, CityId viaC, CityId to) {
    // Checked graph access gives an out_of_range exception for invalid IDs.
    (void)graph.neighbors(from);
    (void)graph.neighbors(viaB);
    (void)graph.neighbors(viaC);
    (void)graph.neighbors(to);
    // Only three BFS traversals are needed for both waypoint permutations.
    const auto fromPaths = bfs(graph, from);
    const auto bPaths = bfs(graph, viaB);
    const auto cPaths = bfs(graph, viaC);
    const auto orderBC = concatenate(fromPaths, viaB, bPaths, viaC, cPaths, to);
    const auto orderCB = concatenate(fromPaths, viaC, cPaths, viaB, bPaths, to);
    if (!orderBC && !orderCB) return {};
    // Stable policy for equal flight counts: prefer B -> C.
    const bool chooseBC = orderBC && (!orderCB || orderBC->size() <= orderCB->size());
    const Path& path = chooseBC ? *orderBC : *orderCB;
    const int flights = static_cast<int>(path.size() - 1);
    return {RequiredStopsStatus::Found, path,
            chooseBC ? std::vector<CityId>{viaB,viaC} : std::vector<CityId>{viaC,viaB},
            flights, std::max(flights - 1, 0)};
}

RequiredStopsResult searchRequiredStops(const Graph& graph, const std::string& from,
                                         const std::string& viaB, const std::string& viaC,
                                         const std::string& to) {
    const auto a = graph.cityId(from), b = graph.cityId(viaB);
    const auto c = graph.cityId(viaC), d = graph.cityId(to);
    if (!a || !b || !c || !d)
        throw std::invalid_argument("city not found in dataset (exact label required)");
    return searchRequiredStops(graph, *a, *b, *c, *d);
}
} // namespace airline
