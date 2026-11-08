cmake_minimum_required(VERSION 3.16)
project(WorldAirlineRouteSearch LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(airline_graph
    cpp/src/Graph.cpp
    cpp/src/GraphLoader.cpp
    cpp/src/BFS.cpp
    cpp/src/RouteSearch.cpp
    cpp/src/RequiredStops.cpp
    cpp/src/MeetingCity.cpp
    cpp/src/RoundTrip.cpp
)
target_include_directories(airline_graph PUBLIC cpp/include)
target_compile_features(airline_graph PUBLIC cxx_std_17)
add_executable(airline_graph_cli cpp/src/main.cpp)
target_link_libraries(airline_graph_cli PRIVATE airline_graph)
if(MSVC)
    target_compile_options(airline_graph PRIVATE /W4 /utf-8)
    target_compile_options(airline_graph_cli PRIVATE /W4 /utf-8)
else()
    target_compile_options(airline_graph PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(airline_graph_cli PRIVATE -Wall -Wextra -Wpedantic)
endif()
if(MINGW)
    target_link_options(airline_graph_cli PRIVATE -municode)
endif()
set_target_properties(airline_graph_cli PROPERTIES
    OUTPUT_NAME airline_graph
    PDB_NAME airline_graph_cli
)
