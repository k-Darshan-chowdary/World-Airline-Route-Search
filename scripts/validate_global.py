"""Validate generated Phase 3 formats, hashes, provenance and count accounting."""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

from check_phase2 import check_data
from download_phase3 import verify
from import_global import read_csv, REASONS, utc_time

ROOT = Path(__file__).resolve().parents[1]


def validate(folder):
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    for name, spec in report["outputs"].items():
        if Path(name).name != name:
            raise ValueError("invalid output filename in report")
        verify(folder / name, spec)
    city_count, edge_count = check_data(folder)
    counts = report["row_counts"]
    if (city_count, edge_count) != (counts["cities"], counts["unique_city_edges"]):
        raise ValueError("city/edge counts differ from report")
    if counts["input_rows"] != counts["accepted_rows"] + sum(counts[r] for r in REASONS):
        raise ValueError("row rejection accounting does not reconcile")
    edges = set()
    with (folder / "flight.txt").open(encoding="utf-8") as stream:
        for line in stream:
            edges.add(tuple(line.rstrip("\n").split("\t")))
    airports = {}
    for row in read_csv(folder / "airports.tsv", {"ident", "id", "icao", "city", "iso_country", "latitude", "longitude"}, delimiter="\t"):
        if row["ident"] in airports:
            raise ValueError("duplicate airport provenance")
        airports[row["ident"]] = row
    countries = {a["iso_country"] for a in airports.values()}
    if len(airports) != counts["airports_used"] or len(countries) != counts["countries"]:
        raise ValueError("airport/country counts differ from report")
    seen, evidence_edges, used, total = set(), set(), set(), 0
    manifest = report["source_manifest"]
    start, end = utc_time(manifest["period_start_utc"]), utc_time(manifest["period_end_exclusive_utc"])
    fields = {"source_city", "destination_city", "source_airport_ident", "destination_airport_ident", "inferred_airline_icao", "accepted_input_rows", "first_departure_utc", "last_departure_utc"}
    for row in read_csv(folder / "route_provenance.tsv", fields, delimiter="\t"):
        s, d, airline = (row[k] for k in ("source_airport_ident", "destination_airport_ident", "inferred_airline_icao"))
        key = (s, d, airline)
        if key in seen or s not in airports or d not in airports or not re.fullmatch("[A-Z]{3}", airline):
            raise ValueError("invalid/duplicate airport-airline evidence")
        seen.add(key)
        pair = (row["source_city"], row["destination_city"])
        if pair != (airports[s]["city"], airports[d]["city"]):
            raise ValueError("evidence city/airport mismatch")
        n = int(row["accepted_input_rows"])
        if n <= 0 or not start <= utc_time(row["first_departure_utc"]) <= utc_time(row["last_departure_utc"]) < end:
            raise ValueError("invalid evidence count or timestamps")
        evidence_edges.add(pair)
        used.update((s, d))
        total += n
    if edges != evidence_edges or used != set(airports) or total != counts["accepted_rows"]:
        raise ValueError("evidence endpoints/row counts differ from city dataset")
    if len(seen) != counts["unique_airport_airline_pairs"]:
        raise ValueError("airport-airline pair count differs from report")
    if counts["collapsed_city_pair_rows"] != total - edge_count or counts["collapsed_airport_airline_rows"] != total - len(seen):
        raise ValueError("duplicate collapse accounting differs from report")
    cities = {row["city"]: row for row in read_csv(folder / "cities.tsv", {"city", "latitude", "longitude"}, delimiter="\t")}
    representatives = {}
    for row in read_csv(folder / "city_representatives.tsv", {"city", "representative_airport_ident"}, delimiter="\t"):
        city, ident = row["city"], row["representative_airport_ident"]
        if city in representatives or city not in cities or ident not in airports or airports[ident]["city"] != city:
            raise ValueError("invalid representative airport")
        if ident != min(i for i, a in airports.items() if a["city"] == city):
            raise ValueError("representative airport selection differs from policy")
        if any(abs(float(cities[city][k]) - float(airports[ident][k])) > 0.00000051 for k in ("latitude", "longitude")):
            raise ValueError("city coordinates differ from representative airport")
        representatives[city] = ident
    if set(cities) != set(representatives):
        raise ValueError("missing representative airport")
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/generated/2026-q3")
    args = parser.parse_args(argv)
    try:
        counts = validate(args.data_dir)
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {counts['cities']:,} cities; {counts['unique_city_edges']:,} unique directed edges; {counts['countries']} countries/territories")
    print("Hashes, metadata, provenance and row accounting verified. Observed historical connectivity only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
