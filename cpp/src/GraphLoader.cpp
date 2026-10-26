#include "GraphLoader.h"

#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace airline {
namespace {

std::runtime_error error(const std::filesystem::path& file, std::size_t line,
                         const std::string& detail) {
    return std::runtime_error(file.string() + ":" + std::to_string(line) + ": " + detail);
}

void normalizeLine(std::string& line, bool first) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (first && line.compare(0, 3, "\xEF\xBB\xBF") == 0) line.erase(0, 3);
}

std::vector<std::string> fields(const std::string& line) {
    std::vector<std::string> parts;
    std::size_t offset = 0;
    do {
        const auto tab = line.find('\t', offset);
        parts.push_back(line.substr(offset, tab == std::string::npos ? tab : tab - offset));
        if (tab == std::string::npos) break;
        offset = tab + 1;
    } while (true);
    return parts;
}

bool validCity(const std::string& name) {
    const auto comma = name.find(", ");
    return !name.empty() && name[0] != '#' && comma != std::string::npos &&
           comma > 0 && comma + 2 < name.size() &&
           name.find(',') == comma && name.find(',', comma + 1) == std::string::npos &&
           name.find_first_of("\t\r\n") == std::string::npos &&
           name.front() != ' ' && name.back() != ' ' &&
           name[comma - 1] != ' ';
}

double parseCoordinate(const std::string& text, bool latitude,
                       const std::filesystem::path& file, std::size_t line) {
    if (text.empty() || text.front() == ' ' || text.back() == ' ') {
        throw error(file, line, "invalid coordinate");
    }
    try {
        std::size_t consumed = 0;
        const double number = std::stod(text, &consumed);
        const double bound = latitude ? 90.0 : 180.0;
        if (consumed != text.size() || !std::isfinite(number) ||
            number < -bound || number > bound) {
            throw error(file, line, "coordinate outside valid bounds");
        }
        return number;
    } catch (const std::invalid_argument&) {
        throw error(file, line, "coordinate is not numeric");
    } catch (const std::out_of_range&) {
        throw error(file, line, "coordinate outside valid bounds");
    }
}

std::ifstream inputFile(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open " + path.string());
    return input;
}

}  // namespace

Graph loadGraph(const std::filesystem::path& directory) {
    const auto citiesPath = directory / "cities.tsv";
    const auto routesPath = directory / "flight.txt";
    auto cities = inputFile(citiesPath);
    Graph graph;
    std::string line;
    if (!std::getline(cities, line)) throw error(citiesPath, 1, "missing TSV header");
    normalizeLine(line, true);
    if (line != "city\tlatitude\tlongitude") {
        throw error(citiesPath, 1, "expected city<TAB>latitude<TAB>longitude header");
    }
    std::size_t lineNumber = 1;
    while (std::getline(cities, line)) {
        ++lineNumber;
        normalizeLine(line, false);
        const auto cols = fields(line);
        if (cols.size() != 3 || !validCity(cols[0])) {
            throw error(citiesPath, lineNumber, "invalid city record or label");
        }
        const Coordinates coords{
            parseCoordinate(cols[1], true, citiesPath, lineNumber),
            parseCoordinate(cols[2], false, citiesPath, lineNumber)};
        try {
            graph.addCity(cols[0], coords);
        } catch (const std::invalid_argument& ex) {
            throw error(citiesPath, lineNumber, ex.what());
        }
    }
    if (!cities.eof()) throw std::runtime_error("read failure: " + citiesPath.string());
    if (!graph.cityCount()) throw error(citiesPath, lineNumber, "no cities");

    auto routes = inputFile(routesPath);
    std::vector<bool> used(graph.cityCount(), false);
    lineNumber = 0;
    while (std::getline(routes, line)) {
        ++lineNumber;
        normalizeLine(line, lineNumber == 1);
        const auto nonSpace = line.find_first_not_of(" \t");
        if (nonSpace == std::string::npos || line[nonSpace] == '#') continue;
        const auto cols = fields(line);
        if (cols.size() != 2 || !validCity(cols[0]) || !validCity(cols[1])) {
            throw error(routesPath, lineNumber, "expected two City, Country labels separated by one TAB");
        }
        const auto source = graph.cityId(cols[0]);
        const auto destination = graph.cityId(cols[1]);
        if (!source || !destination) {
            throw error(routesPath, lineNumber, "route endpoint missing from cities.tsv");
        }
        try {
            if (!graph.addEdge(*source, *destination)) {
                throw error(routesPath, lineNumber, "duplicate directed route");
            }
        } catch (const std::invalid_argument& ex) {
            throw error(routesPath, lineNumber, ex.what());
        }
        used[*source] = true;
        used[*destination] = true;
    }
    if (!routes.eof()) throw std::runtime_error("read failure: " + routesPath.string());
    if (!graph.routeCount()) throw error(routesPath, lineNumber, "no routes");
    for (std::size_t id = 0; id < used.size(); ++id) {
        if (!used[id]) {
            throw std::runtime_error("unused city in metadata: " + graph.cityName(static_cast<CityId>(id)));
        }
    }
    graph.sortNeighbors();
    return graph;
}

}  // namespace airline
