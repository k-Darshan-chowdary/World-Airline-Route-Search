"""Standard-library bridge between the C++ CLI and the GUI.

No live flight data: both the sample and official data show only stored routes.
Run from the repository root or provide absolute paths.
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def find_executable(root: Path = ROOT) -> Path:
    candidates = [
        root / "build" / "airline_graph.exe",
        root / "build" / "Debug" / "airline_graph.exe",
        root / "build" / "Release" / "airline_graph.exe",
        root / "build-release" / "airline_graph.exe",
        root / "build-debug" / "airline_graph.exe",
        root / "build-learning" / "airline_graph.exe",
        root / "build" / "airline_graph",
        root / "build-debug" / "airline_graph",
        root / "build-release" / "airline_graph",
    ]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError(
        "C++ executable not found. Build with CMake first; see README.md."
    )


def read_cities(data_dir: Path) -> list[dict]:
    """Read city IDs and coordinates in exactly the GraphLoader row order."""
    path = data_dir / "cities.tsv"
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    if not rows:
        raise ValueError("Dataset has no city rows")
    cities = []
    for index, row in enumerate(rows):
        try:
            name = row["city"]
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid city metadata row {index + 2}") from exc
        cities.append({
            "id": index, "city": name,
            "latitude": latitude, "longitude": longitude,
        })
    return cities


def query(executable: Path, data_dir: Path, question: str,
          values: dict[str, str], *, timeout: int = 90) -> dict:
    options = {
        "q1": ("--from", "--to", "--max-connections"),
        "q2": ("--from", "--to", "--via-b", "--via-c"),
        "q3": ("--round-trip",),
        "q4": ("--meeting-a", "--meeting-b", "--meeting-c"),
    }
    if question not in options:
        raise ValueError(f"Unknown question {question}")
    args = [str(executable), "--data-dir", str(data_dir)]
    for flag in options[question]:
        name = flag[2:].replace("-", "_")
        value = str(values.get(name, "")).strip()
        if not value:
            raise ValueError(f"Missing {name.replace('_', ' ')}")
        args.extend([flag, value])
    args.append("--json")
    finished = subprocess.run(
        args, cwd=str(ROOT), capture_output=True, encoding="utf-8",
        errors="replace", text=True, timeout=timeout, shell=False,
    )
    try:
        response = json.loads(finished.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Backend returned invalid JSON (exit {finished.returncode}): "
            f"{finished.stderr.strip()}"
        ) from exc
    if not isinstance(response, dict) or response.get("schema_version") != 1:
        raise RuntimeError("Unexpected backend response schema")
    if finished.returncode != 0 or response.get("status") == "error":
        raise RuntimeError(response.get("message") or finished.stderr.strip() or
                           f"Backend exited {finished.returncode}")
    if response.get("query") != question:
        raise RuntimeError("Backend returned a result for the wrong question")
    return response


def route_coordinates(result: dict, cities: list[dict]) -> list[tuple[float, float]]:
    """Map returned city IDs to same-dataset representative coordinates."""
    line = []
    for node in result.get("route", []):
        id_ = node["id"]
        if not isinstance(id_, int) or id_ < 0 or id_ >= len(cities):
            raise ValueError("Route references a city ID outside the dataset")
        entry = cities[id_]
        if entry["city"] != node["city"]:
            raise ValueError("Route city label and metadata disagree")
        line.append((entry["latitude"], entry["longitude"]))
    return line
