"""Desktop interface for the World Airline Route Search project.

The C++ program performs all route searches. This module handles input,
clear results and a map of the returned city-level graph paths.
Run from the project root: python -m python.gui.app
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QStackedWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from .presentation import Q4_COLORS, describe_result
from .route_bridge import ROOT, find_executable, query, read_cities, route_coordinates

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

try:
    import folium
except ImportError:
    folium = None


STYLE = """
QMainWindow, QDialog, QWidget#root, QFrame#sidebar { background: #101827; }
QWidget { color: #e8f0fb; font-family: 'Segoe UI'; font-size: 12px; }
QLabel#appTitle { font-size: 23px; font-weight: 700; color: white; }
QLabel#subheading { color: #aebed2; font-size: 12px; }
QLabel#sectionLabel { color: #aebed2; font-size: 11px; font-weight: 600; }
QLabel#resultTitle { color: white; font-size: 19px; font-weight: 700; }
QLabel#resultMetric { color: #8ee1bb; font-size: 17px; font-weight: 700; }
QLabel#resultDescription { color: #c4d3e5; font-size: 12px; }
QLabel#footnote { color: #92a9c2; font-size: 10px; }
QFrame#card { background: #1d2b40; border: 1px solid #30425a; border-radius: 10px; }
QFrame#mapHeader { background: #142338; border: none; }
QComboBox, QSpinBox {
    background: #25364d; border: 1px solid #465c76; border-radius: 6px;
    padding: 7px 10px; min-height: 23px; color: white;
}
QComboBox QAbstractItemView {
    background: #25364d; color: white; selection-background-color: #2563eb;
}
QPushButton { background: #25364d; border: 1px solid #3c5470;
              border-radius: 7px; padding: 10px; color: #d8e8fa; }
QPushButton:hover { background: #324969; }
QPushButton:checked { background: #245cbd; color: white; border: 1px solid #3987ff; }
QPushButton#searchButton {
    background: #2563eb; font-size: 14px; font-weight: 700;
    padding: 12px; border: 0;
}
QPushButton#searchButton:hover { background: #3475f5; }
QPushButton:disabled { color: #8c9aab; background: #26374a; }
QTextEdit { background: #121f31; color: #cce0f6; border: 1px solid #3c506a;
            border-radius: 8px; font-family: Consolas; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #142338; width: 9px; }
QScrollBar::handle:vertical { background: #405b78; border-radius: 4px; }
QSplitter::handle { background: #33465e; }
"""


def label(text: str, *, name: str = "", wrap: bool = True) -> QLabel:
    item = QLabel(text)
    item.setWordWrap(wrap)
    if name:
        item.setObjectName(name)
    return item


class SearchWorker(QThread):
    succeeded = Signal(dict, float)
    failed = Signal(str)

    def __init__(self, executable: Path, data_dir: Path,
                 question: str, values: dict[str, str]) -> None:
        super().__init__()
        self.executable = executable
        self.data_dir = data_dir
        self.question = question
        self.values = values

    def run(self) -> None:
        started = time.perf_counter()
        try:
            result = query(self.executable, self.data_dir, self.question, self.values)
            self.succeeded.emit(result, (time.perf_counter() - started) * 1000)
        except Exception as exc:
            self.failed.emit(str(exc))


class MapDialog(QDialog):
    """The existing map widget is moved here, not rendered twice."""

    def __init__(self, parent: QWidget, title: str, metric: str,
                 detail: str, notes: tuple[str, ...],
                 legend: tuple[tuple[str, str], ...], map_widget: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Route search result — " + title)
        self.resize(1040, 710)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 16, 17, 16)
        layout.setSpacing(9)
        layout.addWidget(label(title, name="resultTitle"))
        layout.addWidget(label(metric, name="resultMetric"))
        layout.addWidget(label(detail, name="resultDescription"))
        if notes:
            notes_label = label("\n".join(notes[:10]), name="resultDescription")
            notes_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(notes_label)
        if legend:
            dots = label(" · ".join(
                '<span style="color:' + color + '">●</span> ' + html.escape(name)
                for name, color in legend
            ))
            dots.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(dots)
        map_widget.setParent(self)
        layout.addWidget(map_widget, 1)
        layout.addWidget(label(
            "Lines connect representative city coordinates. They are not "
            "actual flight tracks or currently bookable flights.", name="footnote"
        ))


class MainWindow(QMainWindow):
    FIELDS = {
        "q1": (("from", "From city"), ("to", "Destination")),
        "q2": (("from", "From city"), ("via_b", "Required city B"),
               ("via_c", "Required city C"), ("to", "Destination")),
        "q3": (("round_trip", "Start and finish")),
        "q4": (("meeting_a", "Traveler A"), ("meeting_b", "Traveler B"),
               ("meeting_c", "Traveler C")),
    }
    NAMES = (
        "Q1 · Shortest", "Q2 · Via cities", "Q3 · Round trip", "Q4 · Meeting"
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("World Airline Route Search — CSCE 2110")
        self.resize(1370, 820)
        self.setMinimumSize(970, 650)
        self.setStyleSheet(STYLE)
        self.worker: SearchWorker | None = None
        self.result_dialog: MapDialog | None = None
        self.selected_question = "q1"
        self.last_summary = None
        self.city_rows: list[dict] = []
        self.inputs: dict[str, dict] = {}

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(400)
        sidebar.setMaximumWidth(580)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(17, 16, 17, 15)
        side_layout.setSpacing(10)

        side_layout.addWidget(label("World Airline Route Search", name="appTitle"))
        side_layout.addWidget(label(
            "Directed graph · C++17 + BFS · CSCE 2110", name="subheading"
        ))
        side_layout.addWidget(label("DATASET", name="sectionLabel"))
        self.dataset = QComboBox()
        self.dataset.addItem("Sample graph · 12 cities", str(ROOT / "data" / "sample"))
        global_dir = ROOT / "data" / "generated" / "2026-q3"
        if (global_dir / "cities.tsv").is_file():
            self.dataset.addItem("Historical observations · 819 cities", str(global_dir))
        self.dataset.currentIndexChanged.connect(self.load_dataset)
        side_layout.addWidget(self.dataset)

        side_layout.addWidget(label("CHOOSE A QUESTION", name="sectionLabel"))
        navigation = QHBoxLayout()
        navigation.setSpacing(5)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for index, (key, title) in enumerate(zip(self.FIELDS, self.NAMES)):
            button = QPushButton(title)
            button.setCheckable(True)
            button.setToolTip({
                "q1": "Fewest flights subject to connections < x",
                "q2": "Fewest flights visiting two required cities",
                "q3": "Visit all reachable cities; return only at the end",
                "q4": "Minimize total directed flights to a meeting city",
            }[key])
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            navigation.addWidget(button)
            button.clicked.connect(lambda checked=False, k=key: self.change_question(k))
        self.nav_buttons[0].setChecked(True)
        side_layout.addLayout(navigation)

        self.form_stack = QStackedWidget()
        self.form_stack.setSizePolicy(
            self.form_stack.sizePolicy().horizontalPolicy(),
            self.form_stack.sizePolicy().verticalPolicy()
        )
        for question, fields in self.FIELDS.items():
            form_widget = QWidget()
            form = QFormLayout(form_widget)
            form.setContentsMargins(0, 4, 0, 3)
            form.setSpacing(8)
            controls: dict = {}
            for key, caption in fields:
                combo = QComboBox()
                combo.setEditable(True)
                combo.setMinimumWidth(200)
                controls[key] = combo
                form.addRow(caption, combo)
            if question == "q1":
                count = QSpinBox()
                count.setRange(0, 1_000_000)
                count.setValue(3)
                count.setToolTip("The number of intermediate stops must be strictly less than x.")
                controls["max_connections"] = count
                form.addRow("Connections < x", count)
            if question == "q3":
                form.addRow(label(
                    "Exact minimum on up to 14 reachable cities. "
                    "Larger graphs use a clearly labeled heuristic.",
                    name="footnote"
                ))
            self.inputs[question] = controls
            self.form_stack.addWidget(form_widget)
        side_layout.addWidget(self.form_stack)

        self.search_button = QPushButton("Find route")
        self.search_button.setObjectName("searchButton")
        self.search_button.clicked.connect(self.start_search)
        side_layout.addWidget(self.search_button)

        self.status = label("Choose cities to search.", name="subheading")
        side_layout.addWidget(self.status)

        result_card = QFrame()
        result_card.setObjectName("card")
        card_layout = QVBoxLayout(result_card)
        card_layout.setContentsMargins(13, 13, 13, 13)
        card_layout.setSpacing(8)
        self.result_title = label("Your result will appear here", name="resultTitle")
        self.result_metric = label("—", name="resultMetric")
        self.result_detail = label(
            "Select a question, choose cities and click Find route.",
            name="resultDescription"
        )
        self.result_lines = label("", name="resultDescription")
        self.result_lines.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.warning = label("", name="footnote")
        self.warning.setStyleSheet("color: #ffc185; font-weight: 600")
        self.legend = label("", name="resultDescription")
        self.legend.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(self.result_title)
        card_layout.addWidget(self.result_metric)
        card_layout.addWidget(self.result_detail)
        card_layout.addWidget(self.result_lines)
        card_layout.addWidget(self.legend)
        card_layout.addWidget(self.warning)
        self.result_lines.hide()
        self.legend.hide()
        self.warning.hide()
        side_layout.addWidget(result_card)

        self.details_button = QPushButton("Show technical JSON")
        self.details_button.setCheckable(True)
        self.details_button.toggled.connect(self.toggle_details)
        self.details_button.setEnabled(False)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(110)
        self.output.setMaximumHeight(230)
        self.output.hide()
        side_layout.addWidget(self.details_button)
        side_layout.addWidget(self.output)
        side_layout.addStretch(1)
        side_layout.addWidget(label(
            "Historical connectivity only · Arrows are directional · "
            "Map locations are representative, not aircraft tracks.",
            name="footnote"
        ))

        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setWidget(sidebar)
        scroller.setMinimumWidth(420)
        splitter.addWidget(scroller)

        map_panel = QWidget()
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("mapHeader")
        head_row = QHBoxLayout(header)
        self.map_heading = label("ROUTE MAP · city-level connections", name="sectionLabel")
        head_row.addWidget(self.map_heading)
        head_row.addStretch()
        self.expand_button = QPushButton("Open larger map")
        self.expand_button.setEnabled(False)
        self.expand_button.clicked.connect(self.open_map_dialog)
        head_row.addWidget(self.expand_button)
        map_layout.addWidget(header)

        self.map_holder = QVBoxLayout()
        self.map_holder.setContentsMargins(0, 0, 0, 0)
        map_layout.addLayout(self.map_holder, 1)
        self.map_blank = label(
            "Run a search to display a route map.\n"
            "The map shows graph connections, not airline schedules."
        )
        self.map_blank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_blank.setStyleSheet("background: #e8eef4; color: #344b61; font-size: 15px")
        if QWebEngineView is not None and folium is not None:
            self.map_view: QWidget = QWebEngineView()
            self.map_view.hide()
            self.map_holder.addWidget(self.map_view)
        else:
            self.map_view = None
        self.map_holder.addWidget(self.map_blank)
        splitter.addWidget(map_panel)
        splitter.setSizes([480, 890])
        self.load_dataset()

    def change_question(self, question: str) -> None:
        if self.worker is not None or self.result_dialog is not None:
            return
        self.selected_question = question
        self.form_stack.setCurrentIndex(list(self.FIELDS).index(question))
        self.reset_result("Select the cities for " + question.upper() + ".")
        self.clear_map()

    def load_dataset(self, *_args) -> None:
        if self.result_dialog is not None:
            self.result_dialog.close()
        try:
            self.city_rows = read_cities(Path(self.dataset.currentData()))
            names = [row["city"] for row in self.city_rows]
            for controls in self.inputs.values():
                for widget in controls.values():
                    if not isinstance(widget, QComboBox):
                        continue
                    before = widget.currentText()
                    widget.clear()
                    widget.addItems(names)
                    if before in names:
                        widget.setCurrentText(before)
            self.reset_result(f"Loaded {len(names)} cities.")
            self.clear_map()
        except Exception as exc:
            self.city_rows = []
            self.reset_result("Could not read dataset: " + str(exc))
            self.search_button.setEnabled(False)

    def reset_result(self, message: str) -> None:
        self.status.setText(message)
        self.result_title.setText("Ready for a new search")
        self.result_metric.setText("—")
        self.result_detail.setText("Select your cities and run a search.")
        self.result_lines.hide()
        self.legend.hide()
        self.warning.hide()
        self.output.clear()
        self.details_button.setChecked(False)
        self.details_button.setEnabled(False)
        self.expand_button.setEnabled(False)

    def toggle_details(self, checked: bool) -> None:
        self.output.setVisible(checked)
        self.details_button.setText(
            "Hide technical JSON" if checked else "Show technical JSON"
        )

    def start_search(self) -> None:
        if self.worker is not None or self.result_dialog is not None:
            return
        question = self.selected_question
        values: dict[str, str] = {}
        for key, widget in self.inputs[question].items():
            values[key] = str(widget.value()) if isinstance(widget, QSpinBox) else widget.currentText().strip()
        try:
            executable = find_executable()
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "C++ build not found", str(exc))
            return
        self.search_button.setEnabled(False)
        for button in self.nav_buttons:
            button.setEnabled(False)
        self.dataset.setEnabled(False)
        self.status.setText("Searching the directed graph…")
        self.worker = SearchWorker(
            executable, Path(self.dataset.currentData()), question, values
        )
        self.worker.succeeded.connect(self.display_result)
        self.worker.failed.connect(self.display_error)
        self.worker.finished.connect(self.finish_search)
        self.worker.start()

    def finish_search(self) -> None:
        self.search_button.setEnabled(bool(self.city_rows))
        for button in self.nav_buttons:
            button.setEnabled(True)
        self.dataset.setEnabled(True)
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()

    def display_error(self, message: str) -> None:
        self.reset_result("Search failed.")
        self.result_title.setText("Could not complete search")
        self.result_detail.setText(message)

    def display_result(self, result: dict, milliseconds: float) -> None:
        summary = describe_result(result)
        self.last_summary = summary
        self.result_title.setText(summary.title)
        self.result_metric.setText(summary.metric)
        self.result_detail.setText(summary.detail)
        if summary.lines:
            self.result_lines.setText("\n\n".join(summary.lines))
            self.result_lines.show()
        else:
            self.result_lines.hide()
        if summary.legend:
            self.legend.setText(
                " · ".join(
                    '<span style="color:' + color + '">●</span> '
                    + html.escape(title)
                    for title, color in summary.legend
                )
            )
            self.legend.show()
        else:
            self.legend.hide()
        if summary.warning:
            self.warning.setText(summary.warning)
            self.warning.show()
        else:
            self.warning.hide()
        self.output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        self.details_button.setEnabled(True)
        self.status.setText(
            f"{result['query'].upper()} search complete · {milliseconds:.0f} ms "
            "(end-to-end subprocess time)"
        )
        self.draw_map(result)
        self.expand_button.setEnabled(self.map_view is not None)
        # Show the result in a separate window as requested by the assignment.
        # The map widget is moved rather than launching a second browser.
        if self.map_view is not None:
            self.open_map_dialog()

    def clear_map(self) -> None:
        if self.result_dialog is not None:
            return
        if self.map_view is not None:
            self.map_view.hide()
        self.map_blank.show()
        self.expand_button.setEnabled(False)

    def draw_map(self, result: dict) -> None:
        if self.map_view is None or folium is None:
            self.map_blank.setText(
                "Map unavailable. Install PySide6 with WebEngine and folium "
                "to enable visualization."
            )
            self.map_blank.show()
            return

        try:
            map_plot = folium.Map(
                location=[20, 0], zoom_start=2, tiles="OpenStreetMap",
                control_scale=True, prefer_canvas=True,
            )
            all_points: list[tuple[float, float]] = []
            if result["query"] == "q4" and result.get("meeting_city"):
                for key, color in Q4_COLORS.items():
                    nodes = result["routes"][key]
                    coordinates = route_coordinates({"route": nodes}, self.city_rows)
                    all_points.extend(coordinates)
                    if len(coordinates) >= 2:
                        folium.PolyLine(
                            coordinates, color=color, weight=4, opacity=0.9,
                            tooltip=key.replace("_", " ").upper()
                        ).add_to(map_plot)
                city_index = {item["city"]: item for item in self.city_rows}
                meeting_name = result["meeting_city"]["city"]
                cities = dict.fromkeys([
                    result["from_a"], result["from_b"], result["from_c"],
                    meeting_name,
                ])
                for name in cities:
                    item = city_index[name]
                    is_meeting = name == meeting_name
                    folium.Marker(
                        [item["latitude"], item["longitude"]],
                        tooltip=("Meeting: " if is_meeting else "Origin: ") + name,
                        icon=folium.Icon(
                            color="green" if is_meeting else "blue"
                        )
                    ).add_to(map_plot)
                    all_points.append((item["latitude"], item["longitude"]))
            else:
                nodes = result.get("route", [])
                coordinates = route_coordinates(result, self.city_rows)
                all_points.extend(coordinates)
                if len(coordinates) >= 2:
                    folium.PolyLine(
                        coordinates, color="#2563eb", weight=4,
                        opacity=0.9
                    ).add_to(map_plot)
                for item, coordinate in zip(nodes, coordinates):
                    folium.Marker(coordinate, tooltip=item["city"]).add_to(map_plot)
            if len(all_points) > 1 and len(set(all_points)) > 1:
                map_plot.fit_bounds(all_points, padding=(36, 36))
            elif all_points:
                map_plot.location = list(all_points[0])
                map_plot.zoom_start = 5
            rendered = map_plot.get_root().render()
            # One WebEngine instance; do not load the same tile page twice.
            self.map_view.setHtml(rendered, QUrl("https://localhost/"))
            self.map_blank.hide()
            self.map_view.show()
        except Exception as exc:
            self.map_blank.setText("Map unavailable: " + str(exc))
            self.map_blank.show()
            self.map_view.hide()

    def open_map_dialog(self) -> None:
        if self.map_view is None or self.result_dialog is not None:
            return
        if not self.expand_button.isEnabled():
            return
        self.map_holder.removeWidget(self.map_view)
        self.map_blank.setText("The map is open in the results window.")
        self.map_blank.show()
        notes = tuple(self.result_lines.text().split("\n\n")) if self.result_lines.isVisible() else ()
        self.result_dialog = MapDialog(
            self, self.result_title.text(), self.result_metric.text(),
            self.result_detail.text(), notes,
            self.last_summary.legend if self.last_summary is not None else (),
            self.map_view
        )
        self.result_dialog.finished.connect(self.restore_map)
        self.result_dialog.show()

    def restore_map(self, *_args) -> None:
        if self.result_dialog is None:
            return
        dialog = self.result_dialog
        if self.map_view is not None:
            dialog.layout().removeWidget(self.map_view)
            self.map_view.setParent(self.centralWidget())
            self.map_holder.insertWidget(0, self.map_view)
            self.map_view.show()
        self.map_blank.hide()
        self.result_dialog = None

def main() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
