#pragma once
#include "Graph.h"
#include <cstdint>
#include <optional>
#include <string>

namespace airline {

// Q4: city M is different from A, B, C, minimizes the sum of the
// three *directed* shortest flight-leg distances A->M, B->M, C->M.
// A candidate must be reachable from all three sources. Equal sums
// choose the smallest stable city ID.
struct MeetingCityResult {
    std::optional<CityId> city;
    std::optional<std::int64_t> totalFlights;
    int fromA = -1, fromB = -1, fromC = -1;
};

MeetingCityResult findMeetingCity(const Graph& graph, CityId a, CityId b, CityId c);
MeetingCityResult findMeetingCity(const Graph& graph, const std::string& a,
                                  const std::string& b, const std::string& c);
} // namespace airline
