#include "RequiredStops.h"
#include "GraphLoader.h"

#include <algorithm>
#include <array>
#include <filesystem>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using namespace airline;
namespace {
std::size_t checks = 0, queries = 0;
void require(bool value, const char* what) {
    ++checks;
    if (!value) throw std::runtime_error(what);
}
template<class Exception, class Action> void rejects(Action action) {
    try { action(); } catch (const Exception&) { ++checks; return; }
    throw std::runtime_error("expected invalid input exception");
}
Graph cities(int n) {
    Graph g;
    for (int i = 0; i < n; ++i) g.addCity("City" + std::to_string(i) + ", Test", {0,0});
    return g;
}

// Independent oracle: BFS in (city, visited-required-mask) space. It never
// splits the walk into waypoint permutations, and marks aliases at the source.
int oracle(const Graph& g, CityId a, CityId b, CityId c, CityId d) {
    const auto maskAt = [=](CityId u) { return (u == b ? 1 : 0) | (u == c ? 2 : 0); };
    std::vector<std::array<int,4>> distance(g.cityCount(), std::array<int,4>{-1,-1,-1,-1});
    std::queue<std::pair<CityId,int>> pending;
    const int initial = maskAt(a);
    distance[a][initial] = 0;
    pending.push({a,initial});
    while (!pending.empty()) {
        const auto state = pending.front(); pending.pop();
        const auto u = state.first;
        const auto mask = state.second;
        if (u == d && mask == 3) return distance[u][mask];
        for (const auto v : g.neighbors(u)) {
            const int next = mask | maskAt(v);
            if (distance[v][next] >= 0) continue;
            distance[v][next] = distance[u][mask] + 1;
            pending.push({v,next});
        }
    }
    return -1;
}
void verify(const Graph& g, CityId a, CityId b, CityId c, CityId d) {
    ++queries;
    const int expected = oracle(g,a,b,c,d);
    const auto r = searchRequiredStops(g,a,b,c,d);
    if (expected < 0) {
        require(r.status == RequiredStopsStatus::Unreachable, "oracle unreachable status");
        require(r.path.empty() && r.waypointOrder.empty() && !r.flights && !r.connections,
                "unreachable has no path, order or counts");
        return;
    }
    require(r.status == RequiredStopsStatus::Found, "oracle found status");
    require(r.flights == expected && r.connections == std::max(expected-1,0), "optimal walk counts");
    require(r.path.size() == static_cast<std::size_t>(expected)+1, "path length");
    require(r.path.front() == a && r.path.back() == d, "endpoints");
    std::vector<CityId> order;
    for (std::size_t i = 0; i < r.path.size(); ++i) {
        const auto u = r.path[i];
        if (i) require(g.hasEdge(r.path[i-1],u), "directed edge without duplicated boundary");
        if ((u == b || u == c) && std::find(order.begin(),order.end(),u) == order.end()) order.push_back(u);
    }
    require(order.size() == (b == c ? 1u : 2u), "both required cities visited");
    require(order == r.waypointOrder, "actual first-encounter order");
}
void examples() {
    auto g = cities(6);
    for (const auto edge : {std::pair<int,int>{0,1},{1,4},{4,2},{2,3},{0,2},{2,1},{1,3}})
        g.addEdge(edge.first,edge.second);
    g.sortNeighbors();
    require(searchRequiredStops(g,0,1,2,3).path == std::vector<CityId>({0,2,1,3}), "CB beats tempting longer BC");
    require(searchRequiredStops(g,0,2,1,3).path == std::vector<CityId>({0,2,1,3}), "BC shortest");
    g.addEdge(1,2);
    require(searchRequiredStops(g,0,1,2,3).path == std::vector<CityId>({0,1,2,3}), "equal permutations prefer BC");

    auto repeated = cities(4);
    repeated.addEdge(0,2); repeated.addEdge(2,1); repeated.addEdge(1,2); repeated.addEdge(2,3);
    const auto r = searchRequiredStops(repeated,0,1,2,3);
    require(r.path == std::vector<CityId>({0,2,1,2,3}), "must revisit C; both candidates coincide");
    require(r.waypointOrder == std::vector<CityId>({2,1}), "early incidental C reported before B");
    verify(repeated,0,1,2,3); verify(repeated,3,1,2,0);
    verify(repeated,0,0,2,3); verify(repeated,0,2,2,3); verify(repeated,0,1,3,3);
    verify(repeated,2,1,3,2);
    require(searchRequiredStops(repeated,2,2,2,2).path == std::vector<CityId>{2}, "all aliases yield zero-flight route");

    auto tie = cities(6);
    for (const auto edge : {std::pair<int,int>{0,5},{0,4},{5,1},{4,1},{1,2},{2,3}})
        tie.addEdge(edge.first,edge.second);
    tie.sortNeighbors();
    require(searchRequiredStops(tie,0,1,2,3).path == std::vector<CityId>({0,4,1,2,3}), "sorted BFS parent tie");

    Graph unicode;
    for (const auto* label : {u8"München, Germany",u8"東京, Japan",u8"Zürich, Switzerland","D, Test"})
        unicode.addCity(label,{0,0});
    unicode.addEdge(0,1); unicode.addEdge(1,2); unicode.addEdge(2,3);
    require(searchRequiredStops(unicode,u8"München, Germany",u8"東京, Japan",u8"Zürich, Switzerland","D, Test").flights == 3,
            "exact Unicode lookup");
    for (int position = 0; position < 4; ++position) {
        for (const int id : {-1,6,std::numeric_limits<int>::max()}) {
            std::array<CityId,4> ids{0,1,2,3}; ids[position] = id;
            rejects<std::out_of_range>([&] { searchRequiredStops(g,ids[0],ids[1],ids[2],ids[3]); });
        }
        for (const auto* name : {"","city0, Test","City0, Test ","Missing, Test"}) {
            std::array<std::string,4> names{"City0, Test","City1, Test","City2, Test","City3, Test"};
            names[position] = name;
            rejects<std::invalid_argument>([&] { searchRequiredStops(g,names[0],names[1],names[2],names[3]); });
        }
    }
    rejects<std::out_of_range>([] { searchRequiredStops(Graph{},0,0,0,0); });
}
void allQueries(const Graph& g) {
    const auto n = static_cast<CityId>(g.cityCount());
    for (CityId a=0;a<n;++a) for (CityId b=0;b<n;++b)
        for (CityId c=0;c<n;++c) for (CityId d=0;d<n;++d) verify(g,a,b,c,d);
}
void exhaustive() {
    // Every three-city digraph and every tuple, including all aliases.
    for (unsigned edges=0;edges<64;++edges) {
        auto g = cities(3);
        unsigned bit=0;
        for (CityId u=0;u<3;++u) for (CityId v=0;v<3;++v) {
            if (u==v) continue;
            if (edges & (1u << bit)) g.addEdge(u,v);
            ++bit;
        }
        allQueries(g);
    }
    // Reproducible sparse/dense/cyclic/disconnected five-city graphs.
    std::mt19937 rng(6017);
    for (unsigned trial=0;trial<32;++trial) {
        auto g = cities(5);
        for (CityId u=0;u<5;++u) for (CityId v=0;v<5;++v)
            if (u!=v && rng()%100 < 10+trial*2) g.addEdge(u,v);
        allQueries(g);
    }
}
void dataset(const std::filesystem::path& path, int n, std::size_t edges) {
    const auto g = loadGraph(path);
    require(g.cityCount()==static_cast<std::size_t>(n) && g.routeCount()==edges, "dataset counts");
    for (CityId a=0;a<n;++a) {
        verify(g,a,(a+1)%n,(a+17)%n,(a+89)%n);
        verify(g,a,a,a,a);
    }
    std::cout << "Q2 state-space oracle verified from all " << n << " dataset sources\n";
}
}
int main(int argc, char** argv) {
    try {
        if (argc==2) dataset(argv[1],819,19283);
        else if (argc==1) {
            examples(); exhaustive();
            dataset(std::filesystem::path(AIRLINE_SOURCE_DIR)/"data/sample",12,20);
        } else throw std::runtime_error("usage: airline_q2_tests [GLOBAL_DATA_DIR]");
        std::cout << "PASS: " << checks << " Q2 checks; " << queries << " independent oracle queries\n";
        return 0;
    } catch (const std::exception& ex) { std::cerr << "FAIL: " << ex.what() << '\n'; return 1; }
}
