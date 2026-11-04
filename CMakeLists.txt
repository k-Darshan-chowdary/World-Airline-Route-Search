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

function(airline_warnings target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /utf-8)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endfunction()
airline_warnings(airline_graph)

add_executable(airline_graph_cli cpp/src/main.cpp)
target_link_libraries(airline_graph_cli PRIVATE airline_graph)
airline_warnings(airline_graph_cli)
if(MINGW)
    target_link_options(airline_graph_cli PRIVATE -municode)
endif()
# The static library's compiler PDB and CLI's linker PDB otherwise share
# airline_graph.pdb on MSVC Debug builds, causing LNK1201 during parallel builds.
set_target_properties(airline_graph_cli PROPERTIES
    OUTPUT_NAME airline_graph
    PDB_NAME airline_graph_cli
)

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
    add_executable(airline_graph_tests cpp/tests/test_graph.cpp)
    target_link_libraries(airline_graph_tests PRIVATE airline_graph)
    airline_warnings(airline_graph_tests)
    target_compile_definitions(airline_graph_tests PRIVATE AIRLINE_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME cpp_graph_tests COMMAND airline_graph_tests)
    add_test(NAME cpp_sample_graph_cli COMMAND airline_graph_cli --data-dir "${CMAKE_CURRENT_SOURCE_DIR}/data/sample" --expect-cities 12 --expect-routes 20)
    add_test(NAME cpp_cli_regressions COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_cli.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")

    add_executable(airline_q1_tests cpp/tests/test_route_search.cpp)
    target_link_libraries(airline_q1_tests PRIVATE airline_graph)
    airline_warnings(airline_q1_tests)
    target_compile_definitions(airline_q1_tests PRIVATE AIRLINE_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME cpp_q1_tests COMMAND airline_q1_tests)
    add_test(NAME cpp_q1_cli COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_q1_cli.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")

    add_executable(airline_q2_tests cpp/tests/test_required_stops.cpp)
    target_link_libraries(airline_q2_tests PRIVATE airline_graph)
    airline_warnings(airline_q2_tests)
    target_compile_definitions(airline_q2_tests PRIVATE AIRLINE_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    add_test(NAME cpp_q2_tests COMMAND airline_q2_tests)
    add_test(NAME cpp_q2_cli COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_q2_cli.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")
    add_test(NAME cpp_backend_contract COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_backend_contract.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")

    add_executable(airline_q34_tests cpp/tests/test_q34.cpp)
    target_link_libraries(airline_q34_tests PRIVATE airline_graph)
    airline_warnings(airline_q34_tests)
    add_test(NAME cpp_q34_tests COMMAND airline_q34_tests)
    add_test(NAME cpp_q34_cli COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_q34_cli.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")

    add_test(NAME cpp_gui_backend_bridge COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_gui_bridge.py"
        "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample")
    add_test(NAME cpp_gui_syntax COMMAND "${Python3_EXECUTABLE}"
        -m py_compile
        "${CMAKE_CURRENT_SOURCE_DIR}/python/gui/app.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/python/gui/route_bridge.py")

    # Explicit opt-in: normal offline CI needs no worldwide download. A supplied
    # directory is mandatory and must match the existing Phase 3 checksum lock.
    set(AIRLINE_GLOBAL_DATA_DIR "" CACHE PATH "Official generated Phase 3 dataset to verify")
    if(AIRLINE_GLOBAL_DATA_DIR)
        get_filename_component(AIRLINE_GLOBAL_DATA_DIR "${AIRLINE_GLOBAL_DATA_DIR}"
            ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
        add_test(NAME cpp_global_dataset_lock COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/dataset_lock.py"
            --outputs-only --data-dir "${AIRLINE_GLOBAL_DATA_DIR}")
        set_tests_properties(cpp_global_dataset_lock PROPERTIES FIXTURES_SETUP official_global)
        add_test(NAME cpp_global_graph COMMAND airline_graph_tests "${AIRLINE_GLOBAL_DATA_DIR}")
        add_test(NAME cpp_global_graph_cli COMMAND airline_graph_cli
            --data-dir "${AIRLINE_GLOBAL_DATA_DIR}" --expect-cities 819 --expect-routes 19283)
        add_test(NAME cpp_global_q1 COMMAND airline_q1_tests "${AIRLINE_GLOBAL_DATA_DIR}")
        add_test(NAME cpp_global_q1_cli COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_q1_cli.py"
            "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample" "${AIRLINE_GLOBAL_DATA_DIR}")
        add_test(NAME cpp_global_q2 COMMAND airline_q2_tests "${AIRLINE_GLOBAL_DATA_DIR}")
        add_test(NAME cpp_global_q2_cli COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_q2_cli.py"
            "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample" "${AIRLINE_GLOBAL_DATA_DIR}")
        add_test(NAME cpp_global_backend_contract COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/cpp/tests/test_backend_contract.py"
            "$<TARGET_FILE:airline_graph_cli>" "${CMAKE_CURRENT_SOURCE_DIR}/data/sample" "${AIRLINE_GLOBAL_DATA_DIR}")
        set_tests_properties(cpp_global_graph cpp_global_graph_cli cpp_global_q1 cpp_global_q1_cli cpp_global_q2 cpp_global_q2_cli cpp_global_backend_contract
            PROPERTIES FIXTURES_REQUIRED official_global)
    endif()
    get_property(airline_tests DIRECTORY PROPERTY TESTS)
    set_tests_properties(${airline_tests} PROPERTIES TIMEOUT 180)
endif()
