# Person 3 GUI setup

The GUI uses PySide6, Qt WebEngine, Folium, and the existing `examples/backend_client.py`.
It uses `data/sample/cities.tsv` by default, which contains synthetic test routes.
This is historical/sample connectivity, not live flights, prices or bookings.

## Windows (VS Code)

From the repository root, using Command Prompt:

```bat
python -m venv .venv-gui
.venv-gui\Scripts\activate.bat
python -m pip install -r python/requirements-gui.txt
python python/main_gui.py
```

The window and map should open without a C++ build. **Searching requires the
backend executable**. Build it using the toolchain instructions in the main
README. Supported paths include `build/Debug/airline_graph.exe`,
`build/Release/airline_graph.exe` and `build-debug/airline_graph.exe`.

If the executable is missing, the GUI displays a warning instead of inventing
routes. Q3/Q4 are not shown because their backend interface is not yet defined.

## Git safety

Keep `.venv-gui/` local and untracked. Use your own feature branch and a pull
request to merge. Do not commit downloaded/generated flight datasets.
