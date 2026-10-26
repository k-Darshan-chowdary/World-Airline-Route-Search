#include "RouteSearch.h"
#include "BFS.h"
#include "GraphLoader.h"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using namespace airline;
namespace {
int checks = 0;
void require(bool condition, const std::string& message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}
template<class Exception, class Action>
void rejects(Action action) {
    try { action(); }
    catch (const Exception&) { ++checks; return; }
    throw std::runtime_error("expected input exception");
}
void checkPath(const Graph& graph, const RouteSearchResult& result, CityId a, CityId b, int flights) {
    require(result.status == RouteSearchStatus::Found, "qualifying route status");
    require(result.flights == flights && result.connections == std::max(flights - 1, 0), "route counts");
    require(result.path.size() == static_cast<std::size_t>(flights) + 1, "route length");
    require(result.path.front() == a && result.path.back() == b, "route endpoints");
    for (std::size_t i = 1; i < result.path.size(); ++i)
        require(graph.hasEdge(result.path[i-1], result.path[i]), "directed route edge");
}
void boundary(const Graph& graph, CityId a, CityId b, int flights) {
    const int c = std::max(flights - 1, 0);
    const auto failed = searchRoute(graph, a, b, c);
    require(failed.status == RouteSearchStatus::ConnectionLimit && failed.path.empty(), "strict bound rejects equality");
    require(failed.flights == flights && failed.connections == c, "over-limit diagnostic counts");
    checkPath(graph, searchRoute(graph, a, b, static_cast<std::int64_t>(c) + 1), a, b, flights);
    if (c) require(searchRoute(graph, a, b, c-1).status == RouteSearchStatus::ConnectionLimit, "below threshold");
}
void unitTests() {
    Graph g;
    for (const auto* label : {"Alpha, Test", u8"München, Germany", u8"東京, Japan", "Delta, Test", "Tail, Test", "Island, Test"})
        g.addCity(label, {0, 0});
    // Two equal shortest routes and a longer alternative; insert edges out of ID order.
    g.addEdge(0, 2); g.addEdge(0, 1); g.addEdge(2, 3); g.addEdge(1, 3);
    g.addEdge(2, 4); g.addEdge(4, 3); g.addEdge(3, 0);
    g.sortNeighbors();
    boundary(g, 0, 1, 1);
    boundary(g, 0, 3, 2);
    boundary(g, 0, 0, 0);
    boundary(g, 5, 5, 0);
    require(searchRoute(g, 0, 3, 2).path == std::vector<CityId>({0,1,3}), "stable minimum-ID tie");
    require(searchRoute(g, 0, 3, 100).path == searchRoute(g, 0, 3, 2).path, "larger bound keeps shortest path");
    require(searchRoute(g, "Alpha, Test", u8"東京, Japan", 1).path == std::vector<CityId>({0,2}), "Unicode label lookup");
    require(searchRoute(g, "Alpha, Test", u8"München, Germany", 1).connections == 0, "Unicode transfer label");
    checkPath(g, searchRoute(g, 0, 3, std::numeric_limits<std::int64_t>::max()), 0, 3, 2);
    for (const auto limit : {std::int64_t{0}, std::int64_t{1}, std::numeric_limits<std::int64_t>::max()}) {
        const auto result = searchRoute(g, 0, 5, limit);
        require(result.status == RouteSearchStatus::Unreachable && result.path.empty() &&
                !result.flights && !result.connections, "unreachable has no counts");
    }
    Graph directed;
    directed.addCity("A", {0,0}); directed.addCity("B", {0,0}); directed.addEdge(0,1);
    require(searchRoute(directed, 1, 0, 2).status == RouteSearchStatus::Unreachable, "no reverse edge invented");
    rejects<std::invalid_argument>([&] { searchRoute(g, 0, 1, -1); });
    rejects<std::invalid_argument>([&] { searchRoute(g, 0, 1, std::numeric_limits<std::int64_t>::min()); });
    for (const auto* label : {"", "alpha, Test", "Alpha, Test ", "Missing, Test"}) {
        rejects<std::invalid_argument>([&] { searchRoute(g, label, "Alpha, Test", 1); });
        rejects<std::invalid_argument>([&] { searchRoute(g, "Alpha, Test", label, 1); });
    }
    for (const auto id : {-1, 6, std::numeric_limits<int>::max()}) {
        rejects<std::out_of_range>([&] { searchRoute(g, id, 0, 1); });
        rejects<std::out_of_range>([&] { searchRoute(g, 0, id, 0); });
    }
    rejects<std::out_of_range>([] { searchRoute(Graph{}, 0, 0, 1); });
    // Independent all-pairs distance oracle on the small graph.
    const int n = static_cast<int>(g.cityCount()), inf = 1000;
    std::vector<std::vector<int>> d(n, std::vector<int>(n, inf));
    for (int a=0; a<n; ++a) { d[a][a]=0; for (auto b:g.neighbors(a)) d[a][b]=1; }
    for (int k=0;k<n;++k) for(int a=0;a<n;++a) for(int b=0;b<n;++b)
        d[a][b]=std::min(d[a][b],d[a][k]+d[k][b]);
    for(int a=0;a<n;++a) for(int b=0;b<n;++b) {
        if(d[a][b]<inf) boundary(g,a,b,d[a][b]);
        else require(searchRoute(g,a,b,100).status==RouteSearchStatus::Unreachable,"independent no-path oracle");
    }
}
void datasetTests(const std::filesystem::path& path, std::size_t cities, std::size_t routes) {
    const auto g = loadGraph(path);
    require(g.cityCount()==cities && g.routeCount()==routes, "dataset counts");
    // Every source: self, direct neighbor, farthest reachable (strict boundary),
    // and an unreachable destination when present. Phase 4 independently checks
    // the full BFS distance certificates for every source in the same CTest run.
    for(CityId a=0; a<static_cast<CityId>(cities); ++a) {
        const auto traversal=bfs(g,a);
        boundary(g,a,a,0);
        const auto far=static_cast<CityId>(std::max_element(traversal.distance.begin(),traversal.distance.end())-traversal.distance.begin());
        boundary(g,a,far,traversal.distance[far]);
        if(!g.neighbors(a).empty()) boundary(g,a,g.neighbors(a).front(),1);
        const auto absent=std::find(traversal.distance.begin(),traversal.distance.end(),-1);
        if(absent!=traversal.distance.end()) {
            const auto b=static_cast<CityId>(absent-traversal.distance.begin());
            const auto r=searchRoute(g,a,b,std::numeric_limits<std::int64_t>::max());
            require(r.status==RouteSearchStatus::Unreachable && r.path.empty() && !r.flights && !r.connections,"global unreachable");
        }
    }
    std::cout << "Verified Q1 boundaries from all " << cities << " sources; " << routes << " directed routes\n";
}
}
int main(int argc, char** argv) {
    try {
        if(argc==2) datasetTests(argv[1],819,19283);
        else if(argc==1) { unitTests(); datasetTests(std::filesystem::path(AIRLINE_SOURCE_DIR)/"data/sample",12,20); }
        else throw std::runtime_error("usage: airline_q1_tests [GLOBAL_DATA_DIR]");
        std::cout << "PASS: " << checks << " Q1 checks\n";
        return 0;
    } catch(const std::exception& ex) { std::cerr << "FAIL: " << ex.what() << '\n'; return 1; }
}
