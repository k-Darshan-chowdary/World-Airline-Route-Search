#include "Graph.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace airline {

void Graph::checkId(CityId id) const {
    if (id < 0 || static_cast<std::size_t>(id) >= names_.size()) {
        throw std::out_of_range("unknown city ID");
    }
}

CityId Graph::addCity(const std::string& name, Coordinates coordinates) {
    if (name.empty() || !std::isfinite(coordinates.latitude) ||
        !std::isfinite(coordinates.longitude) ||
        coordinates.latitude < -90 || coordinates.latitude > 90 ||
        coordinates.longitude < -180 || coordinates.longitude > 180) {
        throw std::invalid_argument("invalid city name or coordinates");
    }
    if (ids_.count(name)) {
        throw std::invalid_argument("duplicate city: " + name);
    }
    if (names_.size() >= static_cast<std::size_t>(std::numeric_limits<CityId>::max())) {
        throw std::length_error("too many cities for integer IDs");
    }
    const CityId id = static_cast<CityId>(names_.size());
    names_.push_back(name);
    coordinates_.push_back(coordinates);
    adjacency_.emplace_back();
    edgeSets_.emplace_back();
    ids_.emplace(name, id);
    return id;
}

bool Graph::addEdge(CityId source, CityId destination) {
    checkId(source);
    checkId(destination);
    if (source == destination) {
        throw std::invalid_argument("city self-loop is not permitted");
    }
    if (!edgeSets_[source].insert(destination).second) {
        return false;
    }
    adjacency_[source].push_back(destination);
    ++routes_;
    return true;
}

void Graph::sortNeighbors() {
    for (auto& neighbors : adjacency_) {
        std::sort(neighbors.begin(), neighbors.end());
    }
}

std::optional<CityId> Graph::cityId(const std::string& name) const {
    auto it = ids_.find(name);
    return it == ids_.end() ? std::nullopt : std::optional<CityId>{it->second};
}

const std::string& Graph::cityName(CityId id) const {
    checkId(id);
    return names_[id];
}

Coordinates Graph::coordinates(CityId id) const {
    checkId(id);
    return coordinates_[id];
}

const std::vector<CityId>& Graph::neighbors(CityId id) const {
    checkId(id);
    return adjacency_[id];
}

bool Graph::hasEdge(CityId source, CityId destination) const {
    checkId(source);
    checkId(destination);
    return edgeSets_[source].count(destination) != 0;
}

}  // namespace airline
