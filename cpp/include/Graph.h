#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace airline {

using CityId = int;

struct Coordinates {
    double latitude;
    double longitude;
};

// A directed, unweighted, city-level flight graph. IDs are stable after insertion.
class Graph {
public:
    CityId addCity(const std::string& name, Coordinates coordinates);
    bool addEdge(CityId source, CityId destination);
    void sortNeighbors();

    std::optional<CityId> cityId(const std::string& name) const;
    const std::string& cityName(CityId id) const;
    Coordinates coordinates(CityId id) const;
    const std::vector<CityId>& neighbors(CityId id) const;
    bool hasEdge(CityId source, CityId destination) const;
    std::size_t cityCount() const noexcept { return names_.size(); }
    std::size_t routeCount() const noexcept { return routes_; }

private:
    void checkId(CityId id) const;
    std::unordered_map<std::string, CityId> ids_;
    std::vector<std::string> names_;
    std::vector<Coordinates> coordinates_;
    std::vector<std::vector<CityId>> adjacency_;
    std::vector<std::unordered_set<CityId>> edgeSets_;
    std::size_t routes_ = 0;
};

}  // namespace airline
