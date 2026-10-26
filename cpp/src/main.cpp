#include "BFS.h"
#include "GraphLoader.h"

#include <filesystem>
#include <charconv>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    std::filesystem::path directory = "data/generated/2026-q3";
    std::optional<std::string> from;
    std::optional<std::string> to;
    std::optional<std::size_t> expectedCities;
    std::optional<std::size_t> expectedRoutes;
    try {
        for (int i = 1; i < argc; ++i) {
            const std::string argument = argv[i];
            if (argument == "--help") {
                std::cout << "Usage: airline_graph [--data-dir DIR] [--expect-cities N] "
                             "[--expect-routes N] [--from 'City, Country' --to 'City, Country']\n";
                return 0;
            }
            if (i + 1 >= argc) throw std::invalid_argument("missing value for " + argument);
            const std::string value = argv[++i];
            if (argument == "--data-dir") directory = value;
            else if (argument == "--from") from = value;
            else if (argument == "--to") to = value;
            else if (argument == "--expect-cities" || argument == "--expect-routes") {
                std::size_t parsed = 0;
                const auto result = std::from_chars(value.data(), value.data() + value.size(), parsed);
                if (result.ec != std::errc{} || result.ptr != value.data() + value.size()) {
                    throw std::invalid_argument("invalid nonnegative count for " + argument);
                }
                if (argument == "--expect-cities") expectedCities = parsed;
                else expectedRoutes = parsed;
            } else throw std::invalid_argument("unknown argument " + argument);
        }
        if (from.has_value() != to.has_value()) {
            throw std::invalid_argument("--from and --to must be supplied together");
        }
        const auto graph = airline::loadGraph(directory);
        if ((expectedCities && graph.cityCount() != *expectedCities) ||
            (expectedRoutes && graph.routeCount() != *expectedRoutes)) {
            throw std::runtime_error("loaded dataset size differs from expected counts");
        }
        std::cout << "PASS: " << graph.cityCount() << " cities; "
                  << graph.routeCount() << " directed routes\n";
        std::cout << "Historical observed connectivity; not current/bookable flights.\n";
        if (from) {
            const auto source = graph.cityId(*from);
            const auto destination = graph.cityId(*to);
            if (!source || !destination) throw std::invalid_argument("city not found in dataset");
            const auto result = airline::bfs(graph, *source);
            if (!result.reachable(*destination)) {
                std::cout << "No directed route exists between those cities.\n";
                return 0;
            }
            const auto path = result.pathTo(*destination);
            std::cout << "Shortest unweighted path (" << result.distance[*destination] << " flights): ";
            for (std::size_t i = 0; i < path.size(); ++i) {
                if (i) std::cout << " -> ";
                std::cout << graph.cityName(path[i]);
            }
            std::cout << '\n';
        }
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "ERROR: " << ex.what() << '\n';
        return 1;
    }
}
