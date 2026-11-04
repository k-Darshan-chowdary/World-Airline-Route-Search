# Desktop GUI demonstration and validation

## What the application does

The C++17 program runs the graph algorithms. PySide6 collects inputs and
displays the resulting JSON as readable route information. Folium draws
city-to-city graph connections using approximate representative coordinates,
not actual flight tracks or live bookable schedules.

Launch from the repository root after compiling the C++ program:

~~~cmd
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m python.gui.app
~~~

The synthetic dataset with 12 cities and 20 directed edges is bundled with
the repository. The filtered historical dataset, if prepared locally, has
819 cities and 19,283 directed edges.

## Suggested sample demonstrations

| Question | Inputs | Expected answer |
| --- | --- | --- |
| Q1 success | Dallas → New York, x = 1 | One flight, zero connections |
| Q1 boundary | Dallas → New York, x = 0 | No qualifying route: 0 is not less than 0 |
| Q2 | Dallas → Paris, required New York and London | Three flight legs, two connections |
| Q3 | Auckland | Auckland → Sydney → Auckland, exact two-flight tour |
| Q4 | Origins Dallas, New York, London | Meeting city Paris; six total flight legs and three intermediate connections |

The four question buttons stay visible. Each result has a readable summary,
the visited city sequence, and optionally expandable technical JSON.

The result pop-up contains an enlarged map. **Only one Qt WebEngine view is
created**: opening the pop-up moves the existing map into that window.
Closing it returns the map to the main window.

Q4's three routes use blue (traveler A), orange (B), and purple (C). The
meeting city has a green marker. To calculate intermediate connections,
subtract one from each traveler's number of flight legs; all three origins
are distinct from the selected meeting city.

## DSA concepts to explain

- A city is a vertex; a direct directional flight connection is an edge.
  A → B does not imply B → A.
- The directed graph uses adjacency lists (C++ vectors of neighbor IDs),
  a hash map for city-name lookup, and a FIFO queue for BFS.
- BFS finds the fewest edges in an unweighted directed graph; parent arrays
  reconstruct the full city sequence.
- Q1 applies a strict intermediate-connection limit after BFS.
- Q2 compares the two orders of the required cities, checking directed
  reachability on every segment.
- Q3 may not return to its start early. Its state-space BFS is exact
  for at most 14 reachable cities. Its larger-graph heuristic is explicitly
  **not guaranteed minimum** and can fail to find an existing tour.
- Q4 runs BFS from three origins and selects the meeting city that minimizes
  the sum of their directed shortest-flight distances, then prints all
  three reconstructed paths.

## Dataset sizes and running time

The instructor recommends small hand-verifiable examples and larger feasible
graphs. Our tests cover the 12-city sample, generated 6/20/50-city directed
cycles, and the checksum-locked historical dataset when available.

To print **measured** end-to-end times (including process startup and file
loading) for 6, 20 and 50 vertices, run after building:

~~~cmd
.\.venv\Scripts\ctest.exe --test-dir build -V -R cpp_graph_size_checks
~~~

Use real measurements from your computer in the presentation. These are not
isolated algorithm timings, and Q3 changes from exact to heuristic above
14 reachable cities.

To inspect the small directed input file, run:

~~~cmd
type data\sample\flight.txt
~~~

Each tab-separated pair means one outgoing connection from the first city
to the second. Cities that appear only as destinations still have vertices.

## Windows visual acceptance checklist

- [ ] Four question controls are visible without horizontal tab scrolling.
- [ ] Q1 success and strict-limit failure have distinct messages.
- [ ] Q2 displays its required-city order and whole route.
- [ ] Q3 exact and approximate results are visibly different.
- [ ] Q4 shows three color-coded paths and their legend.
- [ ] An unreachable route, a no-tour case, and invalid input are legible.
- [ ] The results pop-up opens with the map, closes, and returns the map.
- [ ] Running another search after closing the pop-up is responsive.
- [ ] The historical dataset, if present, loads without corrupting the sample.
- [ ] CTest passes Debug/Release, and the 46 offline Python dataset tests pass.

The C++ and subprocess tests do not replace a real graphical smoke test.

## Qt startup and interaction regression

The Q3 form is a one-element tuple of `(key, caption)` pairs; the trailing
comma is required. Without it, MainWindow iterates the two strings and raises
`ValueError: too many values to unpack` before startup finishes.

With GUI dependencies installed, run the actual window regression offline:

~~~cmd
set QT_QPA_PLATFORM=offscreen
set QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu
.\.venv\Scripts\python.exe cpp\tests\test_gui_window.py build\airline_graph.exe --require-qt
set QT_QPA_PLATFORM=
set QTWEBENGINE_CHROMIUM_FLAGS=
~~~

Use `build\Release\airline_graph.exe` for MSVC Release builds. The test
constructs MainWindow, checks all four forms and navigation, recovers from a
dataset read failure, runs Q1-Q4 through the real worker/CLI, expands JSON,
and moves the same WebEngine widget into and out of the result dialog.
It captures generated map HTML before web navigation, so it does not verify
remote map tiles or CDN availability.

CTest registers `cpp_gui_window` with `QT_QPA_PLATFORM=offscreen`. If PySide6
is absent, exit 77 is explicitly reported as **skipped**, not passed. Broken
Qt imports or construction fail. The separate Windows GUI CI job installs
the optional dependencies and uses `--require-qt`, so missing Qt fails there.
Normal C++/dataset jobs do not need GUI dependencies.

## Reading resources recommended by the instructor

These are references for learning the algorithms, not a claim that their
example implementations were copied into this project.

- [Runestone — Breadth-first search](https://runestone.academy/ns/books/published/cppds/Graphs/ImplementingBreadthFirstSearch.html)
- [Open Data Structures — Graph traversal](https://www.opendatastructures.org/ods-cpp/12_3_Graph_Traversal.html)
- [Microsoft — basic_ifstream](https://learn.microsoft.com/en-us/cpp/standard-library/basic-ifstream-class?view=msvc-170)
- [Microsoft — basic_istringstream](https://learn.microsoft.com/en-us/cpp/standard-library/basic-istringstream-class?view=msvc-170)
