#include "MeetingCity.h"
#include "BFS.h"
#include <stdexcept>

namespace airline {

MeetingCityResult findMeetingCity(const Graph& graph, CityId a, CityId b, CityId c) {
    (void)graph.neighbors(a); (void)graph.neighbors(b); (void)graph.neighbors(c);
    const auto aa = bfs(graph, a), bb = bfs(graph, b), cc = bfs(graph, c);
    MeetingCityResult best;
    for (std::size_t i = 0; i < graph.cityCount(); ++i) {
        const CityId id = static_cast<CityId>(i);
        if (id == a || id == b || id == c) continue;
        const int da = aa.distance[i], db = bb.distance[i], dc = cc.distance[i];
        if (da == -1 || db == -1 || dc == -1) continue;
        const std::int64_t total =
            static_cast<std::int64_t>(da) + db + dc;
        if (!best.city || total < *best.totalFlights) {
            best.city = id;
            best.totalFlights = total;
            best.fromA = da; best.fromB = db; best.fromC = dc;
        }
    }
    return best;
}

MeetingCityResult findMeetingCity(const Graph& graph, const std::string& a,
                                  const std::string& b, const std::string& c) {
    const auto aa = graph.cityId(a), bb = graph.cityId(b), cc = graph.cityId(c);
    if (!aa || !bb || !cc)
        throw std::invalid_argument("city not found in dataset (exact label required)");
    return findMeetingCity(graph, *aa, *bb, *cc);
}
} // namespace airline
