#include "RoundTrip.h"
#include "BFS.h"

#include <algorithm>
#include <cstdint>
#include <queue>
#include <stdexcept>
#include <utility>
#include <vector>

namespace airline {
namespace {

// 18 vertices need at most 18 * 2^18 states (~43 MB of parent/seen
// arrays, plus the BFS queue). This cap keeps exact searches bounded.
constexpr std::size_t EXACT_LIMIT = 18;

struct Components {
    std::vector<int> of;
    std::vector<std::vector<CityId>> members;
};

// Kosaraju on the part reachable from start, excluding start itself.
// An SCC can be traversed between any two of its vertices while visiting
// every vertex, possibly repeating intermediate vertices.
Components componentsWithoutStart(
    const Graph& graph, const std::vector<CityId>& reachable, CityId start) {
    const auto n = graph.cityCount();
    std::vector<bool> allowed(n, false);
    for (CityId city : reachable) if (city != start) allowed[city] = true;
    std::vector<std::vector<CityId>> reversed(n);
    for (CityId city : reachable) if (city != start)
        for (CityId next : graph.neighbors(city))
            if (allowed[next]) reversed[next].push_back(city);

    // Iterative DFS: avoids recursion limits for larger flight networks.
    std::vector<bool> visited(n, false);
    std::vector<CityId> order;
    for (CityId root : reachable) {
        if (!allowed[root] || visited[root]) continue;
        std::vector<std::pair<CityId, std::size_t>> stack{{root, 0}};
        visited[root] = true;
        while (!stack.empty()) {
            const CityId at = stack.back().first;
            auto& cursor = stack.back().second;
            const auto& next = graph.neighbors(at);
            if (cursor == next.size()) {
                order.push_back(at);
                stack.pop_back();
                continue;
            }
            const CityId dest = next[cursor++];
            if (allowed[dest] && !visited[dest]) {
                visited[dest] = true;
                stack.emplace_back(dest, 0);
            }
        }
    }

    Components result;
    result.of.assign(n, -1);
    for (auto it = order.rbegin(); it != order.rend(); ++it) {
        if (result.of[*it] >= 0) continue;
        const int component = static_cast<int>(result.members.size());
        result.members.emplace_back();
        std::vector<CityId> stack{*it};
        result.of[*it] = component;
        while (!stack.empty()) {
            CityId city = stack.back();
            stack.pop_back();
            result.members.back().push_back(city);
            for (CityId prev : reversed[city]) if (result.of[prev] == -1) {
                result.of[prev] = component;
                stack.push_back(prev);
            }
        }
        std::sort(result.members.back().begin(), result.members.back().end());
    }
    return result;
}

BFSResult bfsInside(
    const Graph& graph, CityId source, const std::vector<int>& componentOf,
    int component) {
    BFSResult result{source, std::vector<int>(graph.cityCount(), -1),
                     std::vector<CityId>(graph.cityCount(), -1)};
    std::queue<CityId> pending;
    pending.push(source);
    result.distance[source] = 0;
    while (!pending.empty()) {
        const CityId at = pending.front();
        pending.pop();
        for (CityId next : graph.neighbors(at)) {
            if (componentOf[next] != component || result.distance[next] != -1) continue;
            result.distance[next] = result.distance[at] + 1;
            result.parent[next] = at;
            pending.push(next);
        }
    }
    return result;
}

// Exact shortest WALK, not just a list of cities: BFS on every flight edge
// in state (city, visited-mask). Start may be revisited only as the final edge.
RoundTripResult exactTour(
    const Graph& graph, CityId start, const std::vector<CityId>& reachable) {
    RoundTripResult answer;
    answer.reachableCities = reachable.size();
    answer.method = RoundTripMethod::Exact;
    const std::size_t r = reachable.size();
    std::vector<int> index(graph.cityCount(), -1);
    for (std::size_t i = 0; i < r; ++i) index[reachable[i]] = static_cast<int>(i);
    const std::size_t masks = std::size_t(1) << r;
    const std::size_t full = masks - 1;
    const auto key = [r](std::size_t at, std::size_t mask) { return mask * r + at; };
    const std::size_t root = key(static_cast<std::size_t>(index[start]),
                                 std::size_t(1) << index[start]);
    std::vector<std::int32_t> parent(masks * r, -1);
    std::vector<unsigned char> seen(masks * r, 0);
    std::queue<std::size_t> queue;
    queue.push(root);
    seen[root] = 1;
    std::size_t goal = masks * r;
    while (!queue.empty()) {
        const auto current = queue.front();
        queue.pop();
        const std::size_t at = current % r;
        const std::size_t mask = current / r;
        if (mask == full && reachable[at] == start) {
            goal = current;
            break;
        }
        for (CityId next : graph.neighbors(reachable[at])) {
            const int id = index[next];
            if (id == -1) continue;
            const std::size_t newMask = mask | (std::size_t(1) << id);
            if (next == start && newMask != full) continue;
            const auto nextKey = key(static_cast<std::size_t>(id), newMask);
            if (seen[nextKey]) continue;
            seen[nextKey] = 1;
            parent[nextKey] = static_cast<std::int32_t>(current);
            queue.push(nextKey);
        }
    }
    if (goal == masks * r) return answer;
    for (std::int32_t cursor = static_cast<std::int32_t>(goal);
         cursor >= 0; cursor = parent[static_cast<std::size_t>(cursor)]) {
        answer.path.push_back(reachable[static_cast<std::size_t>(cursor) % r]);
    }
    std::reverse(answer.path.begin(), answer.path.end());
    answer.status = RoundTripStatus::Found;
    answer.flights = answer.path.size() - 1;
    return answer;
}

// For large components, exact minimization is NP-hard. However, we CAN
// decide whether any end-only tour exists: after removing A, the SCC
// condensation DAG must admit a directed Hamiltonian path from an
// out-neighbor of A to an in-neighbor of A. Such a path exists exactly
// when its topological ordering is unique and consecutive SCCs have edges.
RoundTripResult feasibleTour(
    const Graph& graph, CityId start, const std::vector<CityId>& reachable) {
    RoundTripResult answer;
    answer.reachableCities = reachable.size();
    answer.method = RoundTripMethod::Heuristic;
    const Components scc = componentsWithoutStart(graph, reachable, start);
    const int count = static_cast<int>(scc.members.size());

    std::vector<std::vector<int>> next(count);
    std::vector<int> indegree(count, 0);
    std::vector<std::vector<std::pair<CityId, CityId>>> links(
        count, std::vector<std::pair<CityId, CityId>>(count, {-1, -1}));
    std::vector<std::pair<CityId, CityId>> first(count, {-1, -1});
    std::vector<std::pair<CityId, CityId>> last(count, {-1, -1});
    for (CityId city : reachable) {
        for (CityId dest : graph.neighbors(city)) {
            if (city == start && dest != start) {
                const int c = scc.of[dest];
                if (c >= 0 && (first[c].first == -1 || dest < first[c].second))
                    first[c] = {start, dest};
            } else if (dest == start && city != start) {
                const int c = scc.of[city];
                if (c >= 0 && (last[c].first == -1 || city < last[c].first))
                    last[c] = {city, start};
            } else if (city != start && dest != start) {
                const int from = scc.of[city], to = scc.of[dest];
                if (from != to && from >= 0 && to >= 0) {
                    if (links[from][to].first == -1) {
                        next[from].push_back(to);
                        ++indegree[to];
                        links[from][to] = {city, dest};
                    } else if (std::pair<CityId,CityId>{city,dest} < links[from][to]) {
                        links[from][to] = {city, dest};
                    }
                }
            }
        }
    }

    // Unique topological order is necessary for visiting every SCC in a
    // single walk. Any branching/incomparable SCCs make an end-only tour
    // impossible. No heuristic guesswork is used for this conclusion.
    std::vector<int> order;
    std::vector<int> zero;
    for (int c = 0; c < count; ++c) if (indegree[c] == 0) zero.push_back(c);
    while (!zero.empty()) {
        if (zero.size() != 1) return answer;
        const int current = zero.back();
        zero.pop_back();
        order.push_back(current);
        for (int c : next[current]) if (--indegree[c] == 0) zero.push_back(c);
    }
    if (static_cast<int>(order.size()) != count || count == 0) return answer;
    if (first[order.front()].first == -1 || last[order.back()].first == -1)
        return answer;
    for (int i = 1; i < count; ++i)
        if (links[order[i-1]][order[i]].first == -1) return answer;

    // Construct a valid tour. Each SCC can be walked from its entry to its
    // chosen exit while covering all of its members, using BFS paths within
    // that SCC. This is feasible but NOT necessarily the global minimum.
    answer.path.push_back(start);
    CityId entry = first[order.front()].second;
    answer.path.push_back(entry);
    for (int i = 0; i < count; ++i) {
        const int c = order[i];
        const CityId exit = (i + 1 == count) ? last[c].first :
                                                     links[c][order[i + 1]].first;
        std::vector<bool> visited(graph.cityCount(), false);
        visited[entry] = true;
        CityId here = entry;
        std::size_t covered = 1;
        while (covered < scc.members[c].size()) {
            const auto paths = bfsInside(graph, here, scc.of, c);
            CityId target = -1;
            int distance = -1;
            for (CityId candidate : scc.members[c]) {
                if (visited[candidate]) continue;
                const int d = paths.distance[candidate];
                if (d < 0) continue;
                if (target == -1 || d < distance || (d == distance && candidate < target)) {
                    target = candidate;
                    distance = d;
                }
            }
            if (target == -1) throw std::logic_error("SCC internal traversal failed");
            const auto segment = paths.pathTo(target);
            for (std::size_t j = 1; j < segment.size(); ++j) {
                const CityId city = segment[j];
                answer.path.push_back(city);
                if (!visited[city]) { visited[city] = true; ++covered; }
            }
            here = target;
        }
        const auto finish = bfsInside(graph, here, scc.of, c).pathTo(exit);
        if (finish.empty()) throw std::logic_error("SCC exit not reachable");
        answer.path.insert(answer.path.end(), finish.begin() + 1, finish.end());
        if (i + 1 < count) {
            entry = links[c][order[i+1]].second;
            answer.path.push_back(entry);
        }
    }
    answer.path.push_back(start);
    answer.flights = answer.path.size() - 1;
    answer.status = RoundTripStatus::Found;
    return answer;
}

}  // namespace

RoundTripResult findRoundTrip(const Graph& graph, CityId start) {
    (void)graph.neighbors(start);
    const auto initial = bfs(graph, start);
    std::vector<CityId> reachable;
    for (std::size_t i = 0; i < graph.cityCount(); ++i) {
        if (initial.distance[i] >= 0) reachable.push_back(static_cast<CityId>(i));
    }
    if (reachable.size() == 1) {
        RoundTripResult only;
        only.status = RoundTripStatus::Found;
        only.reachableCities = 1;
        only.method = RoundTripMethod::Exact;
        only.path = {start};
        return only;
    }

    // A reachable city without any path back to start makes a tour impossible.
    std::vector<std::vector<CityId>> incoming(graph.cityCount());
    for (CityId city : reachable)
        for (CityId next : graph.neighbors(city)) incoming[next].push_back(city);
    std::vector<bool> returns(graph.cityCount(), false);
    std::queue<CityId> pending;
    pending.push(start);
    returns[start] = true;
    while (!pending.empty()) {
        CityId city = pending.front(); pending.pop();
        for (CityId prev : incoming[city]) if (!returns[prev]) {
            returns[prev] = true;
            pending.push(prev);
        }
    }
    for (CityId city : reachable) if (!returns[city]) {
        RoundTripResult impossible;
        impossible.reachableCities = reachable.size();
        impossible.method = reachable.size() <= EXACT_LIMIT ?
            RoundTripMethod::Exact : RoundTripMethod::Heuristic;
        return impossible;
    }
    if (reachable.size() <= EXACT_LIMIT) return exactTour(graph, start, reachable);
    return feasibleTour(graph, start, reachable);
}

RoundTripResult findRoundTrip(const Graph& graph, const std::string& start) {
    const auto id = graph.cityId(start);
    if (!id) throw std::invalid_argument("city not found in dataset (exact label required)");
    return findRoundTrip(graph, *id);
}

}  // namespace airline
