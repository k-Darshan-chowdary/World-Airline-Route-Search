cmake_minimum_required(VERSION 3.16)
project(WorldAirlineRouteSearch LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(airline_graph
    cpp/src/Graph.cpp
    cpp/src/GraphLoader.cpp
    cpp/src/BFS.cpp
)
target_include_directories(airline_graph PUBLIC cpp/include)
if(MSVC)
    target_compile_options(airline_graph PRIVATE /W4)
else()
    target_compile_options(airline_graph PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(airline_graph_cli cpp/src/main.cpp)
target_link_libraries(airline_graph_cli PRIVATE airline_graph)
set_target_properties(airline_graph_cli PROPERTIES OUTPUT_NAME airline_graph)

include(CTest)
if(BUILD_TESTING)
    add_executable(airline_graph_tests cpp/tests/test_graph.cpp)
    target_link_libraries(airline_graph_tests PRIVATE airline_graph)
    target_compile_definitions(airline_graph_tests PRIVATE AIRLINE_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME cpp_graph_tests COMMAND airline_graph_tests)
    add_test(NAME cpp_sample_graph_cli COMMAND airline_graph_cli --data-dir "${CMAKE_CURRENT_SOURCE_DIR}/data/sample" --expect-cities 12 --expect-routes 20)
endif()
