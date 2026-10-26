#include "BFS.h"
#include "GraphLoader.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using namespace airline;

namespace {
int checks = 0;

// Always active in Release builds (unlike assert).
void require(bool condition, const std::string& message) {
    ++checks;
    if (!condition) throw std::runtime_error(message);
}

template<class Exception, class Function>
void rejects(Function action, const std::string& diagnostic = "") {
    try { action(); }
    catch (const Exception& ex) {
        require(std::string(ex.what()).find(diagnostic) != std::string::npos,
                "unexpected diagnostic: " + std::string(ex.what()));
        return;
    }
    throw std::runtime_error("expected exception containing: " + diagnostic);
}

struct Fixture {
    fs::path path;
    Fixture() {
        const auto seed = std::chrono::steady_clock::now().time_since_epoch().count();
        for (int i = 0; i < 100; ++i) {
            path = fs::temp_directory_path() / ("airline-tests-" + std::to_string(seed) + "-" + std::to_string(i));
            if (fs::create_directory(path)) return;
        }
        throw std::runtime_error("cannot create fixture directory");
    }
    ~Fixture() { std::error_code ignored; fs::remove_all(path, ignored); }
    void write(const std::string& cities, const std::string& routes) const {
        for (const auto& entry : std::vector<std::pair<std::string, std::string>>{
                 {"cities.tsv", cities}, {"flight.txt", routes}}) {
            std::ofstream output(path / entry.first, std::ios::binary);
            output << entry.second;
            if (!output) throw std::runtime_error("fixture write failed");
        }
    }
};

const std::string header = "city\tlatitude\tlongitude\n";
const std::string cities = header + "Alpha, Test\t0\t0\nBeta, Test\t90\t-180\n";
const std::string route = "Alpha, Test\tBeta, Test\n";

void graphTests() {
    Graph g;
    require(g.cityCount() == 0 && g.routeCount() == 0, "empty graph counts");
    rejects<std::out_of_range>([&] { bfs(g, 0); });
    const auto a = g.addCity("Alpha", {0, 0});
    const auto b = g.addCity("Beta", {-90, 180});
    const auto c = g.addCity("Gamma", {90, -180});
    const auto isolated = g.addCity("Isolated", {1, 2});
    require(a == 0 && b == 1 && c == 2 && isolated == 3, "stable sequential IDs");
    require(g.cityId("Alpha") == a && !g.cityId("alpha"), "exact name lookup");
    require(g.cityName(b) == "Beta" && g.coordinates(b).longitude == 180, "metadata lookup");
    require(g.addEdge(a, c) && g.addEdge(a, b), "new edges");
    require(!g.addEdge(a, b) && g.routeCount() == 2, "deduplication");
    require(!g.hasEdge(b, a), "no invented reverse route");
    require(g.addEdge(b, a) && g.addEdge(b, c), "explicit reverse and cycle");
    g.sortNeighbors();
    require(g.neighbors(a) == std::vector<CityId>({b, c}), "sorted neighbors");
    const auto result = bfs(g, a);
    require(result.source == a && result.distance == std::vector<int>({0, 1, 1, -1}), "BFS distances");
    require(result.pathTo(a) == std::vector<CityId>({a}), "zero-flight path");
    require(result.pathTo(c) == std::vector<CityId>({a, c}), "shortest direct path");
    require(!result.reachable(isolated) && result.pathTo(isolated).empty(), "unreachable city");
    require(result.parent[a] == -1 && result.parent[isolated] == -1, "parent sentinels");
    for (const CityId id : {-1, 4}) {
        rejects<std::out_of_range>([&] { g.cityName(id); });
        rejects<std::out_of_range>([&] { g.coordinates(id); });
        rejects<std::out_of_range>([&] { g.neighbors(id); });
        rejects<std::out_of_range>([&] { g.hasEdge(a, id); });
        rejects<std::out_of_range>([&] { g.hasEdge(id, a); });
        rejects<std::out_of_range>([&] { g.addEdge(a, id); });
        rejects<std::out_of_range>([&] { g.addEdge(id, a); });
        rejects<std::out_of_range>([&] { bfs(g, id); });
        rejects<std::out_of_range>([&] { result.reachable(id); });
        rejects<std::out_of_range>([&] { result.pathTo(id); });
    }
    rejects<std::invalid_argument>([&] { g.addEdge(a, a); });
    rejects<std::invalid_argument>([&] { g.addCity("Alpha", {0, 0}); });
    for (const auto& name : {"", " \t", "A\nB"}) {
        rejects<std::invalid_argument>([&] { g.addCity(name, {0, 0}); });
    }
    for (const auto coords : std::vector<Coordinates>{{91, 0}, {-91, 0}, {0, 181}, {0, -181},
             {std::numeric_limits<double>::quiet_NaN(), 0}, {0, std::numeric_limits<double>::infinity()}}) {
        rejects<std::invalid_argument>([&] { g.addCity("Invalid", coords); });
    }
    require(g.cityCount() == 4 && g.routeCount() == 4, "rejections preserve graph");

    Graph diamond;
    for (int i = 0; i < 5; ++i) diamond.addCity(std::to_string(i), {0, 0});
    for (const auto edge : std::vector<std::pair<int, int>>{{0, 2}, {0, 1}, {2, 3}, {1, 3}, {3, 4}, {4, 0}})
        diamond.addEdge(edge.first, edge.second);
    diamond.sortNeighbors();
    require(bfs(diamond, 0).pathTo(4) == std::vector<CityId>({0, 1, 3, 4}), "deterministic multi-hop tie");
}

void loaderTests() {
    Fixture f;
    f.write(cities, route);
    auto g = loadGraph(f.path);
    require(g.cityCount() == 2 && g.routeCount() == 1 && !g.hasEdge(1, 0), "loader direction");
    f.write("\xEF\xBB\xBF" "city\tlatitude\tlongitude\r\nAlpha, Test\t+0.0e0\t.5\r\nBeta, Test\t-90\t180\r\n",
            "\xEF\xBB\xBF" "  # comment\r\n\t \r\nAlpha, Test\tBeta, Test");
    require(loadGraph(f.path).coordinates(0).longitude == .5, "BOM CRLF comments exponent and no final newline");
    f.write(header + "M\xC3\xBCnchen, Germany\t0\t0\nBeta, Test\t1\t1\n",
            "M\xC3\xBCnchen, Germany\tBeta, Test\n");
    require(loadGraph(f.path).cityId("M\xC3\xBCnchen, Germany").has_value(), "UTF-8 labels");

    const auto bad = [&](const std::string& metadata, const std::string& edges, const std::string& message) {
        f.write(metadata, edges);
        rejects<std::runtime_error>([&] { loadGraph(f.path); }, message);
    };
    bad("", route, "cities.tsv:1:");
    bad("wrong\n", route, "cities.tsv:1:");
    bad(header, route, "no cities");
    bad(cities + "\n", route, "cities.tsv:4:");
    bad(cities + "Alpha, Test\t1\t1\n", route, "duplicate city");
    for (const auto& label : {"Alpha", " Alpha, Test", "Alpha, Test ", "Alpha, ", "Alpha,  Test",
                              "Alpha , Test", "Alpha, Test, Other", "#Alpha, Test", "Alpha, #Test"}) {
        bad(header + label + "\t0\t0\nBeta, Test\t1\t1\n", route, "cities.tsv:2:");
    }
    for (const auto& number : {"", "nan", "inf", "1e999", "91", "-91", "1x", "0x1p0", " 0", "0 "}) {
        bad(header + "Alpha, Test\t" + number + "\t0\nBeta, Test\t0\t0\n", route, "cities.tsv:2:");
    }
    bad(header + "Alpha, Test\t0\t181\nBeta, Test\t0\t0\n", route, "cities.tsv:2:");
    bad(header + "Alpha, Test\t0\t-181\nBeta, Test\t0\t0\n", route, "cities.tsv:2:");
    bad(header + "Alpha, Test\t0\t0\textra\n", route, "cities.tsv:2:");
    bad(cities, "# comment\n\n", "no routes");
    bad(cities, route + route, "flight.txt:2: duplicate");
    bad(cities, "Alpha, Test\tAlpha, Test\n", "self-loop");
    bad(cities, "Alpha, Test\tMissing, Test\n", "missing from cities.tsv");
    bad(cities, "Alpha, Test,Beta, Test\n", "flight.txt:1:");
    bad(cities, route + "Alpha, Test\tBeta, Test\textra\n", "flight.txt:2:");
    bad(cities + "Unused, Test\t0\t0\n", route, "cities.tsv:4: unused");
    for (const auto& bytes : std::vector<std::string>{"\xff", "\xc0\xaf", "\xed\xa0\x80", "\xf4\x90\x80\x80", "\xe2\x82", std::string(1, '\0')}) {
        bad(header + "A" + bytes + ", Test\t0\t0\n", route, "cities.tsv:2: invalid UTF-8");
        bad(cities, "Alpha, Test\tB" + bytes + ", Test\n", "flight.txt:1: invalid UTF-8");
    }
    f.write(cities, route);
    fs::remove(f.path / "flight.txt");
    rejects<std::runtime_error>([&] { loadGraph(f.path); }, "cannot open");
    fs::remove(f.path / "cities.tsv");
    rejects<std::runtime_error>([&] { loadGraph(f.path); }, "cannot open");
}

// A certificate independent of BFS's queue: parent paths witness achievable
// distances, and every edge satisfies d[v] <= d[u]+1. Together these prove
// shortest distances and that no reachable vertex was marked unreachable.
void verifyAllSources(const Graph& g) {
    for (CityId source = 0; source < static_cast<CityId>(g.cityCount()); ++source) {
        const auto result = bfs(g, source);
        require(result.distance[source] == 0, "source distance");
        for (CityId v = 0; v < static_cast<CityId>(g.cityCount()); ++v) {
            const auto path = result.pathTo(v);
            if (!result.reachable(v)) { require(path.empty(), "unreachable path"); continue; }
            require(path.front() == source && path.back() == v, "path endpoints");
            require(static_cast<int>(path.size()) == result.distance[v] + 1, "path length");
            for (std::size_t i = 1; i < path.size(); ++i) require(g.hasEdge(path[i - 1], path[i]), "path edge");
            for (const auto next : g.neighbors(v)) {
                require(result.reachable(next), "reachable closure");
                require(result.distance[next] <= result.distance[v] + 1, "shortest-distance inequality");
            }
        }
    }
}

void datasetTests(const fs::path& path, std::size_t cityCount, std::size_t routes) {
    const auto g = loadGraph(path);
    require(g.cityCount() == cityCount && g.routeCount() == routes, "dataset counts");
    std::size_t counted = 0;
    for (CityId id = 0; id < static_cast<CityId>(g.cityCount()); ++id) {
        require(g.cityId(g.cityName(id)) == id, "name/ID round trip");
        const auto& neighbors = g.neighbors(id);
        require(std::is_sorted(neighbors.begin(), neighbors.end()), "deterministic adjacency");
        counted += neighbors.size();
    }
    require(counted == routes, "adjacency edge count");
    verifyAllSources(g);
    std::cout << "Verified " << cityCount << " cities; " << routes << " directed routes; all "
              << cityCount << " BFS sources\n";
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2) datasetTests(argv[1], 819, 19283);
        else if (argc == 1) {
            graphTests();
            loaderTests();
            datasetTests(fs::path(AIRLINE_SOURCE_DIR) / "data/sample", 12, 20);
            const auto sample = loadGraph(fs::path(AIRLINE_SOURCE_DIR) / "data/sample");
            const auto dallas = *sample.cityId("Dallas, United States");
            const auto auckland = *sample.cityId("Auckland, New Zealand");
            require(bfs(sample, dallas).distance[auckland] == 9, "sample Dallas/Auckland distance");
            require(!bfs(sample, auckland).reachable(dallas), "sample directed unreachability");
        } else throw std::runtime_error("usage: airline_graph_tests [GLOBAL_DATA_DIR]");
        std::cout << "PASS: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "FAIL after " << checks << " checks: " << ex.what() << '\n';
        return 1;
    }
}
