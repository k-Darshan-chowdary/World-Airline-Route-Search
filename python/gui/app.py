"""Minimal four-question GUI for the CSCE 2110 airline graph project.

Run from repo root: python -m python.gui.app
Requires: pip install -r requirements-gui.txt
The displayed lines join observed city-level edges, NOT actual flight tracks.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QSplitter, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from .route_bridge import ROOT, find_executable, query, read_cities, route_coordinates

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

try:
    import folium
except ImportError:
    folium = None


class SearchWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, executable: Path, data_dir: Path, question: str, values: dict):
        super().__init__()
        self.executable = executable
        self.data_dir = data_dir
        self.question = question
        self.values = values

    def run(self):
        try:
            self.succeeded.emit(query(
                self.executable, self.data_dir, self.question, self.values
            ))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    FIELDS = {
        "q1": [("from", "From"), ("to", "To")],
        "q2": [("from", "From"), ("via_b", "Required city B"),
               ("via_c", "Required city C"), ("to", "Destination")],
        "q3": [("round_trip", "Start and finish")],
        "q4": [("meeting_a", "Traveller A"), ("meeting_b", "Traveller B"),
               ("meeting_c", "Traveller C")],
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Airline Route Search — CSCE 2110")
        self.resize(1250, 740)
        self.worker = None
        self.city_rows = []
        self.combo_fields = {}
        self.inputs = {}

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        left = QWidget()
        left.setMinimumWidth(420)
        layout = QVBoxLayout(left)
        heading = QLabel("World Airline Route Search")
        heading.setStyleSheet("font-size: 23px; font-weight: 700;")
        layout.addWidget(heading)
        subtitle = QLabel(
            "C++17 graph algorithms · historical observed connectivity, "
            "not current/bookable flights."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        self.dataset = QComboBox()
        self.dataset.addItem("Synthetic sample (12 cities)", str(ROOT / "data" / "sample"))
        global_dir = ROOT / "data" / "generated" / "2026-q3"
        if (global_dir.joinpath("cities.tsv").is_file():
            self.dataset.addItem("Historical dataset (819 cities)", str(global_dir))
        layout.addWidget(QLabel("Dataset"))
        layout.addWidget(self.dataset)
        self.dataset.currentIndexChanged.connect(self.load_dataset)

        self.tabs = QTabWidget()
        titles = {
            "q1": "Q1 · Shortest route",
            "q2": "Q2 · Required cities",
            "q3": "Q3 · Round trip",
            "q4": "Q4 · Meeting city",
        }
        for question, fields in self.FIELDS.items():
            tab = QWidget()
            form = QFormLayout(tab)
            controls = {}
            for key, label in fields:
                combo = QComboBox()
                combo.setEditable(True)
                combo.setMinimumWidth(270)
                controls[key] = combo
                form.addRow(label, combo)
            if question == "q1":
                limit = QSpinBox()
                limit.setRange(0, 1000000)
                limit.setValue(3)
                controls["max_connections"] = limit
                form.addRow("Connections strictly less than", limit)
            if question == "q3":
                note = QLabel(
                    "Exact minimum for up to 14 reachable cities. "
                    "Larger graphs use a labeled approximation."
                )
                note.setWordWrap(True)
                form.addRow(note)
            self.inputs[question] = controls
            self.tabs.addTab(tab, titles[question])
        layout.addWidget(self.tabs)

        self.search_button = QPushButton("Search route")
        self.search_button.setStyleSheet(
            "QPushButton { padding: 11px; font-size: 15px; font-weight: bold; }"
        )
        self.search_button.clicked.connect(self.start_search)
        layout.addWidget(self.search_button)

        self.summary = QLabel("Select a question and run a search.")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-weight: 600; padding: 5px;")
        layout.addWidget(self.summary)
        layout.addWidget(QLabel("Backend JSON result"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(190)
        layout.addWidget(self.output)
        layout.addWidget(QLabel(
            "Map positions are representative city markers. Drawn lines are "
            "graph edges, not precise aircraft tracks."
        ))
        splitter.addWidget(left)

        if QWebEngineView is None:
            self.map_view = QTextEdit()
            self.map_view.setReadOnly(True)
            self.map_view.setPlainText(
                "Qt WebEngine is unavailable. Route results are still shown "
                "at left; install the full PySide6 distribution for maps."
            )
        else:
            self.map_view = QWebEngineView()
            self.map_view.setHtml(
                "<html><body style='font-family:sans-serif;padding:35px'>"
                "<h2>Map preview</h2><p>Run a query to view routes.</p></body></html>"
            )
        splitter.addWidget(self.map_view)
        splitter.setSizes([470, 780])
        self.load_dataset()

    def load_dataset(self, *_):
        try:
            self.city_rows = read_cities(Path(self.dataset.currentData()))
            labels = [row["city"] for row in self.city_rows]
            for controls in self.inputs.values():
                for widget in controls.values():
                    if not isinstance(widget, QComboBox):
                        continue
                    current = widget.currentText()
                    widget.clear()
                    widget.addItems(labels)
                    if current in labels:
                        widget.setCurrentText(current)
            self.summary.setText(f"Loaded {len(labels)} city names.")
        except Exception as exc:
            self.city_rows = []
            self.summary.setText(f"Could not load metadata: {exc}")

    def start_search(self):
        if self.worker is not None:
            return
        question = list(self.FIELDS)[self.tabs.currentIndex()]
        values = {}
        for key, widget in self.inputs[question].items():
            values[key] = str(widget.value()) if isinstance(widget, QSpinBox) else widget.currentText()
        try:
            binary = find_executable()
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Build required", str(exc))
            return
        self.search_button.setEnabled(False)
        self.summary.setText("Searching the directed flight graph…")
        self.worker = SearchWorker(binary, Path(self.dataset.currentData()), question, values)
        self.worker.succeeded.connect(self.display_result)
        self.worker.failed.connect(self.display_error)
        self.worker.finished.connect(self.finished_search)
        self.worker.start()

    def finished_search(self):
        self.search_button.setEnabled(True)
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

    def display_error(self, message: str):
        self.summary.setText("Search failed.")
        self.output.setPlainText(message)

    def display_result(self, result: dict):
        self.output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        question = result["query"]
        status = result["status"]
        if status != "found":
            self.summary.setText(f"{question.upper()}: {status.replace('_', ' ')}")
        elif question == "q4":
            meeting = result["meeting_city"]["city"]
            self.summary.setText(
                f"Q4: {meeting} · total directed flights = {result['total_flights']}"
            )
        else:
            route = result.get("route", [])
            mode = (
                " · HEURISTIC (not guaranteed shortest)"
                if question == "q3" and not result.get("optimal") else ""
            )
            self.summary.setText(
                f"{question.upper()}: {len(route)} route points · "
                f"{result.get('flights')} flights{mode}"
            )
        self.update_map(result)

    def update_map(self, result: dict):
        if QWebEngineView is None or folium is None:
            if QWebEngineView is not None:
                self.map_view.setHtml(
                    "<html><body><h3>Install folium to display maps.</h3>"
                    "<p>pip install -r requirements-gui.txt</p></body></html>"
                )
            return
        try:
            locations = route_coordinates(result, self.city_rows)
            markers = list(result.get("route", []))
            if result.get("query") == "q4" and result.get("meeting_city"):
                names = [result["from_a"], result["from_b"], result["from_c"],
                         result["meeting_city"]["city"]]
                by_name = {x["city"]: x for x in self.city_rows}
                markers = [{"id": by_name[name]["id"], "city": name}
                           for name in names]
                locations = route_coordinates({"route": markers}, self.city_rows)
            fmap = folium.Map(location=[20, 0], zoom_start=2)
            for item, (lat, lon) in zip(markers, locations):
                folium.Marker([lat, lon], tooltip=item["city"]).add_to(fmap)
            if len(locations) >= 2 and result.get("query") != "q4":
                folium.PolyLine(locations, color="#1479b8", weight=4).add_to(fmap)
            self.map_view.setHtml(fmap.get_root().render(), QUrl("https://localhost/"))
        except Exception as exc:
            self.map_view.setHtml(
                "<html><body><h3>Map unavailable</h3>"
                "<p>Check that city metadata matches the selected dataset.</p>"
                "</body></html>"
            )
            self.output.append(f"Map diagnostic: {exc}")


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
