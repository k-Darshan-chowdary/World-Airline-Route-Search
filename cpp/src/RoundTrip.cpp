#include "RoundTrip.h"
#include "BFS.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <queue>
#include <stdexcept>
#include <vector>

namespace airline {
namespace {
constexpr std::size_t EXACT_LIMIT = 14;
// Disallow returning to the start while selecting the next required city.
// A final return is performed separately when every city has been visited.
BFSResult bfsAvoidStart(const Graph& graph, CityId origin, CityId start) {
    BFSResult result{origin, std::vector<int>(graph.cityCount(), -1),
                     std::vector<CityId>(graph.cityCount(), -1)};
    std::queue<CityId> pending;
    pending.push(origin);
    result.distance[origin] = 0;
    while (!pending.empty()) {
        const CityId city = pending.front(); pending.pop();
        for (const CityId next : graph.neighbors(city)) {
            if (next == start || result.distance[next] != -1) continue;
            result.parent[next] = city;
            result.distance[next] = result.distance[city] + 1;
            pending.push(next);
        }
    }
    return result;
}
}

RoundTripResult findRoundTrip(const Graph& graph, CityId start) {
    (void)graph.neighbors(start);
    const auto initial = bfs(graph, start);
    std::vector<CityId> reachable;
    std::vector<int> index(graph.cityCount(), -1);
    for (std::size_t i = 0; i < graph.cityCount(); ++i) {
        if (initial.distance[i] < 0) continue;
        index[i] = static_cast<int>(reachable.size());
        reachable.push_back(static_cast<CityId>(i));
    }
    RoundTripResult answer;
    answer.reachableCities = reachable.size();
    answer.method = reachable.size() <= EXACT_LIMIT
        ? RoundTripMethod::Exact : RoundTripMethod::Heuristic;
    if (reachable.size() == 1) {
        answer.status = RoundTripStatus::Found;
        answer.path = {start};
        return answer;
    }

    // Prove feasibility: every vertex reachable from start must also reach
    // start. A single reverse-graph traversal avoids one BFS per city.
    std::vector<std::vector<CityId>> incoming(graph.cityCount());
    for (CityId u : reachable) {
        for (CityId v : graph.neighbors(u)) incoming[v].push_back(u);
    }
    std::vector<bool> returns(graph.cityCount(), false);
    std::queue<CityId> rq;
    rq.push(start); returns[start] = true;
    while (!rq.empty()) {
        const CityId u = rq.front(); rq.pop();
        for (CityId v : incoming[u]) if (!returns[v]) {
            returns[v] = true; rq.push(v);
        }
    }
    for (CityId id : reachable) if (!returns[id]) return answer;

    if (reachable.size() <= EXACT_LIMIT) {
        const std::size_t r = reachable.size();
        const std::size_t stateCount = (std::size_t(1) << r) * r;
        const std::size_t full = (std::size_t(1) << r) - 1;
        const auto key = [r](int at, std::size_t mask) {
            return mask * r + static_cast<std::size_t>(at);
        };
        const std::size_t root = key(index[start], std::size_t(1) << index[start]);
        std::vector<std::int64_t> parent(stateCount, -1);
        std::vector<unsigned char> seen(stateCount, 0);
        std::queue<std::size_t> q;
        q.push(root); seen[root] = 1;
        std::size_t goal = stateCount;
        while (!q.empty()) {
            const std::size_t current = q.front(); q.pop();
            const int at = static_cast<int>(current % r);
            const std::size_t mask = current / r;
            if (mask == full && reachable[at] == start) { goal = current; break; }
            for (CityId neighbor : graph.neighbors(reachable[at])) {
                const int next = index[neighbor];
                if (next < 0) continue;
                const std::size_t nextMask = mask | (std::size_t(1) << next);
                if (neighbor == start && nextMask != full) continue;
                const auto nk = key(next, nextMask);
                if (seen[nk]) continue;
                seen[nk] = 1;
                parent[nk] = static_cast<std::int64_t>(current);
                q.push(nk);
            }
        }
        if (goal == stateCount) return answer;
        for (std::int64_t k = static_cast<std::int64_t>(goal);
             k != -1; k = parent[static_cast<std::size_t>(k)]) {
            answer.path.push_back(reachable[static_cast<std::size_t>(k) % r]);
        }
        std::reverse(answer.path.begin(), answer.path.end());
    } else {
        // Greedily choose the closest unvisited vertex by directed BFS
        // distance, and mark intermediate vertices encountered en route.
        // Since the reachable component is strongly connected this always
        // produces a feasible closed walk, but it is NOT an optimality proof.
        std::vector<bool> visited(graph.cityCount(), false);
        visited[start] = true;
        std::size_t count = 1;
        CityId here = start;
        answer.path.push_back(start);
        while (count < reachable.size()) {
            const auto paths = bfsAvoidStart(graph, here, start);
            CityId next = -1;
            int shortest = std::numeric_limits<int>::max();
            for (CityId candidate : reachable) {
                if (visited[candidate]) continue;
                const int distance = paths.distance[candidate];
                if (distance >= 0 && distance < shortest) {
                    shortest = distance; next = candidate;
                }
            }
            if (next == -1) {
                answer.status = RoundTripStatus::HeuristicFailed;
                answer.path.clear();
                return answer;
            }
            const auto segment = paths.pathTo(next);
            for (std::size_t i = 1; i < segment.size(); ++i) {
                answer.path.push_back(segment[i]);
                if (!visited[segment[i]]) { visited[segment[i]] = true; ++count; }
            }
            here = next;
        }
        const auto back = bfs(graph, here).pathTo(start);
        if (back.empty()) {
            answer.status = RoundTripStatus::HeuristicFailed;
            answer.path.clear();
            return answer;
        }
        answer.path.insert(answer.path.end(), back.begin() + 1, back.end());
    }
    answer.status = RoundTripStatus::Found;
    answer.flights = answer.path.size() - 1;
    return answer;
}

RoundTripResult findRoundTrip(const Graph& graph, const std::string& start) {
    const auto id = graph.cityId(start);
    if (!id) throw std::invalid_argument("city not found in dataset (exact label required)");
    return findRoundTrip(graph, *id);
}
} // namespace airline
