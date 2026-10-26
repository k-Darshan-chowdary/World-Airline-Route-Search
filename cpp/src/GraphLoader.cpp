#include "GraphLoader.h"

#include <cmath>
#include <fstream>
#include <locale>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace airline {
namespace {

std::runtime_error error(const std::filesystem::path& file, std::size_t line,
                         const std::string& detail) {
    return std::runtime_error(file.string() + ":" + std::to_string(line) + ": " + detail);
}

bool validUtf8(const std::string& text) {
    for (std::size_t i = 0; i < text.size();) {
        const auto lead = static_cast<unsigned char>(text[i++]);
        if (lead < 0x80) {
            if (lead < 0x20 && lead != '\t') return false;
            if (lead == 0x7f) return false;
            continue;
        }
        unsigned code = 0;
        unsigned minimum = 0;
        int remaining = 0;
        if (lead >= 0xc2 && lead <= 0xdf) { code = lead & 0x1f; minimum = 0x80; remaining = 1; }
        else if (lead >= 0xe0 && lead <= 0xef) { code = lead & 0x0f; minimum = 0x800; remaining = 2; }
        else if (lead >= 0xf0 && lead <= 0xf4) { code = lead & 0x07; minimum = 0x10000; remaining = 3; }
        else return false;
        while (remaining--) {
            if (i == text.size()) return false;
            const auto next = static_cast<unsigned char>(text[i++]);
            if ((next & 0xc0) != 0x80) return false;
            code = (code << 6) | (next & 0x3f);
        }
        if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) return false;
    }
    return true;
}

void normalizeLine(std::string& line, bool first, const std::filesystem::path& file,
                   std::size_t number) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (first && line.compare(0, 3, "\xEF\xBB\xBF") == 0) line.erase(0, 3);
    if (!validUtf8(line)) throw error(file, number, "invalid UTF-8 or control character");
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
           name[comma - 1] != ' ' && name[comma + 2] != ' ' && name[comma + 2] != '#';
}

double parseCoordinate(const std::string& text, bool latitude,
                       const std::filesystem::path& file, std::size_t line) {
    static const std::regex decimal(R"([+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?)");
    if (!std::regex_match(text, decimal)) {
        throw error(file, line, "invalid coordinate");
    }
    std::istringstream input(text);
    input.imbue(std::locale::classic());
    double number = 0;
    input >> number;
    const double bound = latitude ? 90.0 : 180.0;
    if (!input || !std::isfinite(number) || number < -bound || number > bound) {
        throw error(file, line, "coordinate outside valid bounds");
    }
    return number;
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
    normalizeLine(line, true, citiesPath, 1);
    if (line != "city\tlatitude\tlongitude") {
        throw error(citiesPath, 1, "expected city<TAB>latitude<TAB>longitude header");
    }
    std::size_t lineNumber = 1;
    while (std::getline(cities, line)) {
        ++lineNumber;
        normalizeLine(line, false, citiesPath, lineNumber);
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
        normalizeLine(line, lineNumber == 1, routesPath, lineNumber);
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
            throw error(citiesPath, id + 2, "unused city in metadata: " + graph.cityName(static_cast<CityId>(id)));
        }
    }
    graph.sortNeighbors();
    return graph;
}

}  // namespace airline
