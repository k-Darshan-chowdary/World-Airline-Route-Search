"""Validate the Phase 2 city and directed-edge files; no routing algorithms."""
import argparse
import csv
import math
from pathlib import Path
import re
import sys


def valid_label(value):
    return value == value.strip() and re.fullmatch(r"[^,\t\r\n]+, [^,\t\r\n]+", value) is not None


def check_data(data_dir):
    """Return (city_count, edge_count), raising ValueError for invalid data."""
    cities = set()
    with (Path(data_dir) / "cities.tsv").open(encoding="utf-8", newline="") as stream:
        rows = csv.reader(stream, delimiter="\t")
        if next(rows, None) != ["city", "latitude", "longitude"]:
            raise ValueError("cities.tsv: expected city, latitude, longitude TAB-separated header")
        for line, row in enumerate(rows, 2):
            if len(row) != 3:
                raise ValueError(f"cities.tsv:{line}: expected exactly three TAB-separated fields")
            label, lat_text, lon_text = row
            if not valid_label(label):
                raise ValueError(f"cities.tsv:{line}: invalid City, Country label: {label!r}")
            if label in cities:
                raise ValueError(f"cities.tsv:{line}: duplicate city: {label}")
            try:
                lat, lon = float(lat_text), float(lon_text)
            except ValueError as exc:
                raise ValueError(f"cities.tsv:{line}: coordinates must be numeric") from exc
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError(f"cities.tsv:{line}: coordinates must be finite and within geographic bounds")
            cities.add(label)
    if not cities:
        raise ValueError("cities.tsv: no cities")

    edges, endpoints = set(), set()
    with (Path(data_dir) / "flight.txt").open(encoding="utf-8") as stream:
        for line, raw in enumerate(stream, 1):
            text = raw.rstrip("\r\n")
            if not text.strip() or text.lstrip().startswith("#"):
                continue
            fields = text.split("\t")
            if len(fields) != 2:
                raise ValueError(f"flight.txt:{line}: expected exactly two TAB-separated labels")
            source, destination = fields
            if not all(valid_label(label) for label in fields):
                raise ValueError(f"flight.txt:{line}: invalid City, Country label")
            if source == destination:
                raise ValueError(f"flight.txt:{line}: self-loop is not allowed in this dataset")
            missing = set(fields) - cities
            if missing:
                raise ValueError(f"flight.txt:{line}: missing city metadata: {sorted(missing)}")
            edge = (source, destination)
            if edge in edges:
                raise ValueError(f"flight.txt:{line}: duplicate directed edge: {edge}")
            edges.add(edge)
            endpoints.update(fields)
    if not edges:
        raise ValueError("flight.txt: no directed edges")
    if cities != endpoints:
        raise ValueError(f"cities.tsv: cities without route endpoints: {sorted(cities - endpoints)}")
    return len(cities), len(edges)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "sample")
    parser.add_argument("--expect-cities", type=int)
    parser.add_argument("--expect-edges", type=int)
    args = parser.parse_args(argv)
    try:
        cities, edges = check_data(args.data_dir)
        for label, actual, expected in (("cities", cities, args.expect_cities), ("directed edges", edges, args.expect_edges)):
            if expected is not None and actual != expected:
                raise ValueError(f"expected {expected} {label}, found {actual}")
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {cities} cities; {edges} directed edges; {cities} matching coordinate records")
    print("Integrity checks passed. Sample routes are synthetic; no real-world service is asserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
