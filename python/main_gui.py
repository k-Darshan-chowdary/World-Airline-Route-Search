"""Person 3 GUI: historical route search using the team's v1 backend."""
import csv
import html
import sys
from pathlib import Path

import folium
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from examples.backend_client import query_backend  # noqa: E402


def find_executable():
    candidates = (
        ROOT / "build" / "Debug" / "airline_graph.exe",
        ROOT / "build" / "Release" / "airline_graph.exe",
        ROOT / "build-debug" / "airline_graph.exe",
        ROOT / "build-release" / "airline_graph.exe",
        ROOT / "build" / "airline_graph.exe",
        ROOT / "build-debug" / "airline_graph",
        ROOT / "build-release" / "airline_graph",
    )
    return next((path for path in candidates if path.is_file()), None)


def read_cities(data_dir):
    path = data_dir / "cities.tsv"
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise ValueError(f"No cities in {path}")
    for row in rows:
        if not all(key in row for key in ("city", "latitude", "longitude")):
            raise ValueError("Invalid city metadata columns")
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid map coordinates")
    return rows


class SearchWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, executable, data_dir, params):
        super().__init__()
        self.executable, self.data_dir, self.params = executable, data_dir, params

    def run(self):
        try:
            result = query_backend(self.executable, self.data_dir, **self.params, timeout=30)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class AirlineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Airline Route Search")
        self.resize(1150, 800)
        self.data_dir = ROOT / "data" / "sample"
        self.cities = read_cities(self.data_dir)
        self.thread = None
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        title = QLabel("World Airline Route Search")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Historical observed connectivity • Sample routes are synthetic • Not live flight schedules"))

        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Q1: Shortest route (connection limit)", "Q2: Visit two required cities"])
        self.source = QComboBox()
        self.target = QComboBox()
        self.via_b = QComboBox()
        self.via_c = QComboBox()
        names = [row["city"] for row in self.cities]
        for combo in (self.source, self.target, self.via_b, self.via_c):
            combo.addItems(names)
        self.source.setCurrentText("Dallas, United States")
        self.target.setCurrentText("New York, United States")
        self.via_b.setCurrentText("New York, United States")
        self.via_c.setCurrentText("London, United Kingdom")
        self.limit = QSpinBox()
        self.limit.setRange(0, 1000000)
        self.limit.setValue(3)
        form.addRow("Query", self.mode)
        form.addRow("From", self.source)
        form.addRow("To", self.target)
        form.addRow("Exclusive connection limit", self.limit)
        form.addRow("Required city B", self.via_b)
        form.addRow("Required city C", self.via_c)
        layout.addLayout(form)
        self.mode.currentIndexChanged.connect(self.update_mode)
        self.update_mode()

        controls = QHBoxLayout()
        self.search_button = QPushButton("Search Route")
        self.search_button.clicked.connect(self.search)
        controls.addWidget(self.search_button)
        layout.addLayout(controls)
        self.status = QLabel("Ready. Build the C++ backend before searching.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.map = QWebEngineView()
        layout.addWidget(self.map, stretch=1)
        self.draw_map([])

    def update_mode(self):
        q2 = self.mode.currentIndex() == 1
        self.via_b.setEnabled(q2)
        self.via_c.setEnabled(q2)
        self.limit.setEnabled(not q2)

    def draw_map(self, nodes):
        points = []
        for node in nodes:
            index = node.get("id")
            if type(index) is not int or index < 0 or index >= len(self.cities):
                raise ValueError("Backend returned an unknown city ID")
            row = self.cities[index]
            if row["city"] != node.get("city"):
                raise ValueError("Backend city ID/name does not match dataset")
            points.append((float(row["latitude"]), float(row["longitude"]), row["city"]))
        map_view = folium.Map(location=[20, 0], zoom_start=2, control_scale=True)
        for number, (lat, lon, city) in enumerate(points, 1):
            folium.Marker([lat, lon], tooltip=f"{number}. {city}",
                          popup=html.escape(city)).add_to(map_view)
        if len(points) >= 2:
            folium.PolyLine([(lat, lon) for lat, lon, _ in points],
                            color="#2563eb", weight=4, opacity=0.85).add_to(map_view)
            map_view.fit_bounds([(lat, lon) for lat, lon, _ in points])
        self.map.setHtml(map_view.get_root().render())

    def search(self):
        executable = find_executable()
        if executable is None:
            QMessageBox.warning(self, "Backend not built",
                "Cannot find airline_graph executable. Build the C++ backend first (see README.md). "
                "The GUI does not calculate routes by itself.")
            return
        params = dict(from_city=self.source.currentText(), to_city=self.target.currentText())
        if self.mode.currentIndex() == 0:
            params["exclusive_connection_limit"] = self.limit.value()
        else:
            params.update(via_b=self.via_b.currentText(), via_c=self.via_c.currentText())
        self.search_button.setEnabled(False)
        self.status.setText("Searching...")
        self.thread = QThread(self)
        self.worker = SearchWorker(executable, self.data_dir, params)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.search_done)
        self.thread.start()

    def search_done(self):
        self.search_button.setEnabled(True)
        self.worker = None
        self.thread = None

    def show_result(self, result):
        status = result["status"]
        if status == "found":
            nodes = result["route"]
            try:
                self.draw_map(nodes)
                names = " → ".join(node["city"] for node in nodes)
                self.status.setText(
                    f"Found: {result['flights']} flights, {result['connections']} connections. {names}"
                )
            except Exception as exc:
                self.show_error(str(exc))
        elif status == "connection_limit":
            self.draw_map([])
            self.status.setText(
                f"Shortest route has {result['connections']} connections, "
                "but does not satisfy the strict limit."
            )
        else:
            self.draw_map([])
            self.status.setText("No directed route found for these cities.")

    def show_error(self, message):
        self.status.setText(f"Error: {message}")
        QMessageBox.warning(self, "Route search error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = AirlineWindow()
    except Exception as exc:
        QMessageBox.critical(None, "Startup error", str(exc))
        sys.exit(1)
    window.show()
    sys.exit(app.exec())
