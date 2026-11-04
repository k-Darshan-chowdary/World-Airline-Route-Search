#include "BFS.h"
#include "GraphLoader.h"
#include "RouteSearch.h"
#include "RequiredStops.h"
#include "RoundTrip.h"
#include "MeetingCity.h"
#include "Utf8.h"

#include <charconv>
#include <cstdint>
#include <cwchar>
#include <filesystem>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace {
std::string jsonString(const std::string& value) {
    std::string out = "\"";
    const char* hex = "0123456789abcdef";
    for (std::size_t i = 0; i < value.size();) {
        const auto ch = static_cast<unsigned char>(value[i]);
        if (ch >= 0x80) {
            const auto bytes = airline::detail::utf8ScalarBytes(value, i);
            // Exception diagnostics may originate in a platform's legacy encoding.
            // Keep even those error responses valid UTF-8 JSON.
            if (!bytes) { out += "\\ufffd"; ++i; }
            else { out.append(value, i, bytes); i += bytes; }
            continue;
        }
        ++i;
        if (ch == '"' || ch == '\\') { out += '\\'; out += static_cast<char>(ch); }
        else if (ch < 0x20) {
            out += "\\u00";
            out += hex[ch >> 4];
            out += hex[ch & 15];
        } else out += static_cast<char>(ch);
    }
    return out + '"';
}

int reportError(bool json, const std::string& message) {
    if (json) std::cout << "{\"schema_version\":1,\"status\":\"error\",\"message\":" << jsonString(message) << "}\n";
    std::cerr << "ERROR: " << message << '\n';
    return 1;
}

template<class Integer>
Integer nonnegative(const std::string& value, const std::string& option) {
    Integer parsed = 0;
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos) {
        throw std::invalid_argument("invalid nonnegative count for " + option);
    }
    const auto result = std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (result.ec != std::errc{} || result.ptr != value.data() + value.size()) {
        throw std::invalid_argument("invalid nonnegative count for " + option);
    }
    return parsed;
}

const char* statusName(airline::RouteSearchStatus status) {
    switch (status) {
        case airline::RouteSearchStatus::Found: return "found";
        case airline::RouteSearchStatus::Unreachable: return "unreachable";
        case airline::RouteSearchStatus::ConnectionLimit: return "connection_limit";
    }
    throw std::logic_error("unknown route status");
}

void printJsonCities(const airline::Graph& graph, const std::vector<airline::CityId>& path) {
    std::cout << '[';
    for (std::size_t i = 0; i < path.size(); ++i) {
        if (i) std::cout << ',';
        const auto id = path[i];
        std::cout << "{\"id\":" << id << ",\"city\":" << jsonString(graph.cityName(id)) << '}';
    }
    std::cout << ']';
}

int run(const std::vector<std::string>& args) {
    bool json = false;
    for (const auto& arg : args) if (arg == "--json") json = true;
    try {
        for (const auto& arg : args) {
            if (!airline::detail::validUtf8(arg)) throw std::invalid_argument("invalid UTF-8 argument");
        }
        std::filesystem::path directory = "data/generated/2026-q3";
        std::optional<std::string> from, to, viaB, viaC, roundTrip, meetingA, meetingB, meetingC;
        std::optional<std::size_t> expectedCities, expectedRoutes;
        std::optional<std::int64_t> limit;
        for (std::size_t i = 0; i < args.size(); ++i) {
            const auto& argument = args[i];
            if (argument == "--help") {
                const std::string usage = "Usage: airline_graph [--data-dir DIR] [--expect-cities N] "
                             "[--expect-routes N] [--from 'City, Country' --to 'City, Country' "
                             "[--max-connections X | --via-b 'City, Country' --via-c 'City, Country'] [--json]]\n"
                             "Q1 requires connections < X; direct flight = 0 connections.\n"
                             "X must be decimal digits in [0, 9223372036854775807].\n"
                             "Q2 visits both required cities in either order, minimizing flights; repeated visits are allowed.\n"
                             "Q3: --round-trip CITY; return to start only at end (exact <=14; heuristic above).\n"
                             "Q4: --meeting-a CITY --meeting-b CITY --meeting-c CITY.\n";
                if (json) std::cout << "{\"schema_version\":1,\"status\":\"help\",\"usage\":" << jsonString(usage) << "}\n";
                else std::cout << usage;
                return 0;
            }
            if (argument == "--json") continue;
            if (i + 1 >= args.size()) throw std::invalid_argument("missing value for " + argument);
            const auto& value = args[++i];
            if (argument == "--data-dir") directory = std::filesystem::u8path(value);
            else if (argument == "--from") from = value;
            else if (argument == "--to") to = value;
            else if (argument == "--via-b") viaB = value;
            else if (argument == "--via-c") viaC = value;
            else if (argument == "--round-trip") roundTrip = value;
            else if (argument == "--meeting-a") meetingA = value;
            else if (argument == "--meeting-b") meetingB = value;
            else if (argument == "--meeting-c") meetingC = value;
            else if (argument == "--expect-cities") expectedCities = nonnegative<std::size_t>(value, argument);
            else if (argument == "--expect-routes") expectedRoutes = nonnegative<std::size_t>(value, argument);
            else if (argument == "--max-connections") limit = nonnegative<std::int64_t>(value, argument);
            else throw std::invalid_argument("unknown argument " + argument);
        }
        if (from.has_value() != to.has_value()) {
            throw std::invalid_argument("--from and --to must be supplied together");
        }
        if (limit && !from) throw std::invalid_argument("--max-connections requires --from and --to");
        if (viaB.has_value() != viaC.has_value())
            throw std::invalid_argument("--via-b and --via-c must be supplied together");
        if (viaB && !from) throw std::invalid_argument("Q2 requires --from and --to");
        if (viaB && limit) throw std::invalid_argument("Q2 cannot be combined with --max-connections");
        const bool meeting = meetingA.has_value() || meetingB.has_value() || meetingC.has_value();
        if (meeting && (!meetingA || !meetingB || !meetingC))
            throw std::invalid_argument("Q4 requires --meeting-a, --meeting-b and --meeting-c");
        if ((roundTrip && (from || viaB || limit || meeting)) ||
            (meeting && (from || viaB || limit)))
            throw std::invalid_argument("Q3/Q4 cannot be combined with Q1/Q2 or each other");
        if (json && !limit && !viaB && !roundTrip && !meeting)
            throw std::invalid_argument("--json requires a Q1, Q2, Q3 or Q4 query");
        const auto graph = airline::loadGraph(directory);
        if ((expectedCities && graph.cityCount() != *expectedCities) ||
            (expectedRoutes && graph.routeCount() != *expectedRoutes)) {
            throw std::runtime_error("loaded dataset size differs from expected counts");
        }
        if (!json) {
            std::cout << "PASS: " << graph.cityCount() << " cities; "
                      << graph.routeCount() << " directed routes\n";
            std::cout << "Historical observed connectivity; not current/bookable flights.\n";
        }
        if (roundTrip) {
            const auto result = airline::findRoundTrip(graph, *roundTrip);
            const bool found = result.status == airline::RoundTripStatus::Found;
            const bool exact = result.method == airline::RoundTripMethod::Exact;
            if (json) {
                std::cout << "{\"schema_version\":1,\"query\":\"q3\",\"status\":"
                          << jsonString(found ? "found" : result.status == airline::RoundTripStatus::NoTour ? "no_tour" : "heuristic_failed")
                          << ",\"from\":" << jsonString(*roundTrip)
                          << ",\"method\":" << jsonString(exact ? "exact" : "heuristic")
                          << ",\"optimal\":" << (found && exact ? "true" : "false")
                          << ",\"reachable_cities\":" << result.reachableCities
                          << ",\"flights\":" << (found ? std::to_string(result.flights) : "null")
                          << ",\"historical_observed_connectivity\":true,\"route\":";
                printJsonCities(graph, result.path);
                std::cout << "}\n";
            } else if (found) {
                std::cout << (exact ? "Exact shortest" : "Heuristic (not guaranteed shortest)")
                          << " closed walk (" << result.flights << " flights; "
                          << result.reachableCities << " reachable cities): ";
                for (std::size_t i = 0; i < result.path.size(); ++i) {
                    if (i) std::cout << " -> ";
                    std::cout << graph.cityName(result.path[i]);
                }
                std::cout << '\n';
            } else {
                if (result.status == airline::RoundTripStatus::NoTour)
                    std::cout << "No valid tour exists that visits every reachable city and returns only at the end.\\n";
                else
                    std::cout << "Greedy heuristic could not find a valid tour; feasibility is unknown.\\n";
            }
        } else if (meeting) {
            const auto result = airline::findMeetingCity(graph, *meetingA, *meetingB, *meetingC);
            if (json) {
                std::cout << "{\"schema_version\":1,\"query\":\"q4\",\"status\":"
                          << jsonString(result.city ? "found" : "unreachable")
                          << ",\"from_a\":" << jsonString(*meetingA)
                          << ",\"from_b\":" << jsonString(*meetingB)
                          << ",\"from_c\":" << jsonString(*meetingC)
                          << ",\"historical_observed_connectivity\":true,\"meeting_city\":";
                if (result.city) {
                    std::cout << "{\"id\":" << *result.city
                              << ",\"city\":" << jsonString(graph.cityName(*result.city))
                              << "},\"total_flights\":" << *result.totalFlights
                              << ",\"distances\":{\"from_a\":" << result.fromA
                              << ",\"from_b\":" << result.fromB
                              << ",\"from_c\":" << result.fromC << "}";
                } else {
                    std::cout << "null,\"total_flights\":null,\"distances\":null";
                }
                std::cout << "}\n";
            } else if (result.city) {
                std::cout << "Best meeting city: " << graph.cityName(*result.city)
                          << " (sum of directed shortest flights: " << *result.totalFlights
                          << "; distances: " << result.fromA << ", " << result.fromB
                          << ", " << result.fromC << ")\n";
            } else {
                std::cout << "No meeting city reachable from all three origins.\n";
            }
        } else if (viaB) {
            const auto result = airline::searchRequiredStops(graph, *from, *viaB, *viaC, *to);
            const bool found = result.status == airline::RequiredStopsStatus::Found;
            if (json) {
                std::cout << "{\"schema_version\":1,\"query\":\"q2\",\"status\":"
                          << jsonString(found ? "found" : "unreachable")
                          << ",\"from\":" << jsonString(*from) << ",\"to\":" << jsonString(*to)
                          << ",\"via_b\":" << jsonString(*viaB) << ",\"via_c\":" << jsonString(*viaC)
                          << ",\"flights\":" << (result.flights ? std::to_string(*result.flights) : "null")
                          << ",\"connections\":" << (result.connections ? std::to_string(*result.connections) : "null")
                          << ",\"historical_observed_connectivity\":true,\"route\":";
                printJsonCities(graph, result.path);
                std::cout << ",\"waypoint_order\":";
                printJsonCities(graph, result.waypointOrder);
                std::cout << "}\n";
            } else if (found) {
                std::cout << "Shortest route through required cities (" << *result.flights << " flights; "
                          << *result.connections << " connections): ";
                for (std::size_t i = 0; i < result.path.size(); ++i) {
                    if (i) std::cout << " -> ";
                    std::cout << graph.cityName(result.path[i]);
                }
                std::cout << '\n';
            } else {
                std::cout << "No directed route through both required cities exists.\n";
            }
        } else if (limit) {
            const auto result = airline::searchRoute(graph, *from, *to, *limit);
            if (json) {
                std::cout << "{\"schema_version\":1,\"query\":\"q1\",\"status\":" << jsonString(statusName(result.status))
                          << ",\"from\":" << jsonString(*from) << ",\"to\":" << jsonString(*to)
                          << ",\"exclusive_connection_limit\":" << *limit
                          << ",\"flights\":" << (result.flights ? std::to_string(*result.flights) : "null")
                          << ",\"connections\":" << (result.connections ? std::to_string(*result.connections) : "null")
                          << ",\"historical_observed_connectivity\":true,\"route\":";
                printJsonCities(graph, result.path);
                std::cout << "}\n";
            } else if (result.status == airline::RouteSearchStatus::Found) {
                std::cout << "Shortest qualifying route (" << *result.flights << " flights; "
                          << *result.connections << " connections; connections < " << *limit << "): ";
                for (std::size_t i = 0; i < result.path.size(); ++i) {
                    if (i) std::cout << " -> ";
                    std::cout << graph.cityName(result.path[i]);
                }
                std::cout << '\n';
            } else if (result.status == airline::RouteSearchStatus::Unreachable) {
                std::cout << "No qualifying route: no directed route exists between those cities.\n";
            } else {
                std::cout << "No qualifying route: shortest route has " << *result.connections
                          << " connections; requires connections < " << *limit << ".\n";
            }
        } else if (from) {
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
        return reportError(json, ex.what());
    }
}
}  // namespace

#ifdef _WIN32
// Native Windows arguments are UTF-16. Convert explicitly so exact UTF-8 city
// lookup works independently of the user's legacy console/ANSI code page.
int wmain(int argc, wchar_t** argv) {
    SetConsoleOutputCP(CP_UTF8);
    bool json = false;
    for (int i = 1; i < argc; ++i) if (std::wcscmp(argv[i], L"--json") == 0) json = true;
    std::vector<std::string> args;
    for (int i = 1; i < argc; ++i) {
        const int bytes = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, argv[i], -1,
                                             nullptr, 0, nullptr, nullptr);
        if (!bytes) return reportError(json, "invalid Unicode argument");
        std::string value(static_cast<std::size_t>(bytes), '\0');
        WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, argv[i], -1,
                            value.data(), bytes, nullptr, nullptr);
        value.pop_back();
        args.push_back(value);
    }
    return run(args);
}
#else
int main(int argc, char** argv) {
    return run(std::vector<std::string>(argv + 1, argv + argc));
}
#endif
