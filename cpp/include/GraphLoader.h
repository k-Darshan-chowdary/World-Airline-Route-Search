#pragma once

#include "Graph.h"
#include <filesystem>

namespace airline {

// Load Phase 2/3 compatible UTF-8 data files from a directory.
// Throws std::runtime_error with filename and line on malformed data.
Graph loadGraph(const std::filesystem::path& dataDirectory);

}  // namespace airline
