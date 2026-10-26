"""Build directed city connectivity from conservative MrAirspace observations."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unicodedata

from download_phase3 import fingerprint, verify

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT_FIELDS = ("Lat", "Lon", "FL_Ft", "DateTime_UTC", "ApplicableAirports")
COLUMNS = ["Airline", "Callsign"] + [
    f"Track_{end}_{field}" for end in ("Origin", "Destination") for field in ENDPOINT_FIELDS
]
AIRPORT_FIELDS = {"id", "ident", "icao_code", "iata_code", "type", "municipality",
                  "iso_country", "iso_region", "latitude_deg", "longitude_deg"}
REASONS = ("invalid_time", "outside_period", "missing_airline", "callsign_mismatch",
           "not_ground", "ambiguous_or_missing_airport", "unmatched_airport",
           "invalid_track_coordinates", "endpoint_too_far", "city_self_loop")


def clean_text(value):
    return unicodedata.normalize("NFC", str(value or "")).strip()


def label_part(value):
    value = clean_text(value)
    # Preserve the Phase 2 label grammar; never silently rewrite a place name.
    if not value or any(c in value for c in ",\t\r\n") or value.startswith("#"):
        raise ValueError("city/country cannot be empty or contain commas/control delimiters")
    return value


def coordinates(lat, lon):
    lat, lon = float(lat), float(lon)
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("invalid coordinates")
    return lat, lon


def distance_km(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, h))))


def read_csv(path, required, delimiter=","):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True, delimiter=delimiter)
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError(f"{path}: missing required CSV columns {sorted(required)}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path}: duplicate header names")
        for row in reader:
            if None in row or any(row[k] is None for k in required):
                raise ValueError(f"{path}:{reader.line_num}: malformed CSV row")
            yield row


def load_airports(airports_path, countries_path):
    countries = {}
    for row in read_csv(countries_path, {"code", "name"}):
        code = clean_text(row["code"])
        if code in countries:
            raise ValueError(f"duplicate country code: {code}")
        countries[code] = clean_text(row["name"])
    airports, seen_ids, seen_idents, seen_codes = {}, set(), set(), set()
    ambiguous = set()
    stats = Counter()
    for row in read_csv(airports_path, AIRPORT_FIELDS):
        stats["input_rows"] += 1
        ident, airport_id = clean_text(row["ident"]), clean_text(row["id"])
        if not ident or not airport_id or ident in seen_idents or airport_id in seen_ids:
            raise ValueError("missing or duplicate OurAirports id/ident")
        seen_ids.add(airport_id)
        seen_idents.add(ident)
        code = clean_text(row["icao_code"])
        if not re.fullmatch(r"[A-Z]{4}", code):
            stats["missing_icao"] += 1
            continue
        if code in seen_codes:
            airports.pop(code, None)
            ambiguous.add(code)
            stats["duplicate_icao_rows"] += 1
            continue
        seen_codes.add(code)
        if row["type"] not in {"large_airport", "medium_airport", "small_airport", "seaplane_base"}:
            stats["excluded_type"] += 1
            continue
        try:
            city = label_part(row["municipality"])
            country = label_part(countries.get(row["iso_country"], ""))
            lat, lon = coordinates(row["latitude_deg"], row["longitude_deg"])
        except (TypeError, ValueError):
            stats["invalid_metadata"] += 1
            continue
        airports[code] = dict(id=airport_id, ident=ident, icao=code, iata=row["iata_code"],
                              city=f"{city}, {country}", iso_country=row["iso_country"],
                              region=row["iso_region"], latitude=lat, longitude=lon)
    # Do not merge same-named municipalities in different administrative regions.
    regions = {}
    for airport in airports.values():
        regions.setdefault(airport["city"], set()).add(airport["region"])
    collisions = {city for city, values in regions.items() if len(values) > 1}
    stats["city_region_collision_labels"] = len(collisions)
    filtered = {code: a for code, a in airports.items() if a["city"] not in collisions}
    stats["city_region_collision_airports"] = len(airports) - len(filtered)
    stats["usable_airports"] = len(filtered)
    stats["ambiguous_icao_codes"] = len(ambiguous)
    return filtered, dict(sorted(stats.items()))


@lru_cache(maxsize=32768)
def singleton_airport(value):
    # The verified Q3 schema uses Python-list-shaped strings, not actual lists.
    # An anchored parser accepts exactly one four-letter ICAO code. No eval.
    match = re.fullmatch(r"\[\s*(['\"])([A-Z]{4})\1\s*\]", value)
    return match.group(2) if match else None


def utc_time(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def classify(row, airports, start, end, max_km):
    try:
        departure = utc_time(row["Track_Origin_DateTime_UTC"])
        arrival = utc_time(row["Track_Destination_DateTime_UTC"])
        if not 0 < (arrival - departure).total_seconds() <= 36 * 3600:
            return "invalid_time", None
    except (TypeError, ValueError, OverflowError):
        return "invalid_time", None
    if not start <= departure < end:
        return "outside_period", None
    airline = clean_text(row["Airline"])
    if not re.fullmatch(r"[A-Z]{3}", airline):
        return "missing_airline", None
    callsign = clean_text(row["Callsign"])
    if not re.fullmatch(re.escape(airline) + r"[A-Z0-9]{1,5}", callsign) or not any(c.isdigit() for c in callsign[3:]):
        return "callsign_mismatch", None
    if any(clean_text(row[f"Track_{end}_FL_Ft"]).lower() != "ground" for end in ("Origin", "Destination")):
        return "not_ground", None
    codes = [singleton_airport(clean_text(row[f"Track_{end}_ApplicableAirports"])) for end in ("Origin", "Destination")]
    if not all(codes):
        return "ambiguous_or_missing_airport", None
    if any(code not in airports for code in codes):
        return "unmatched_airport", None
    source, destination = (airports[code] for code in codes)
    for end_name, airport in zip(("Origin", "Destination"), (source, destination)):
        try:
            point = coordinates(row[f"Track_{end_name}_Lat"], row[f"Track_{end_name}_Lon"])
        except (TypeError, ValueError):
            return "invalid_track_coordinates", None
        if distance_km(point, (airport["latitude"], airport["longitude"])) > max_km:
            return "endpoint_too_far", None
    if source["city"] == destination["city"]:
        return "city_self_loop", None
    return None, (source["ident"], destination["ident"], airline, departure.isoformat())


def parquet_rows(path, batch_size):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ValueError("Install requirements-import.txt in a virtual environment first") from exc
    source = pq.ParquetFile(path)
    missing = set(COLUMNS) - set(source.schema_arrow.names)
    if missing:
        raise ValueError(f"Parquet missing columns: {sorted(missing)}")
    for field in source.schema_arrow:
        if field.name in COLUMNS and str(field.type) not in {"string", "large_string"}:
            raise ValueError(f"Parquet schema changed: expected string for {field.name}, got {field.type}")
    for batch in source.iter_batches(batch_size=batch_size, columns=COLUMNS, use_threads=False):
        yield batch.to_pylist()


def write_tsv(path, header, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        if header:
            writer.writerow(header)
        writer.writerows(rows)


def aggregate(batches, airports, folder, start, end, max_km=5.0, progress=False):
    """Disk-backed distinct airport/airline evidence; batches bound Python memory."""
    stats = Counter({"input_rows": 0, "accepted_rows": 0, **{k: 0 for k in REASONS}})
    by_ident = {a["ident"]: a for a in airports.values()}
    database = folder / "aggregation.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA cache_size=-16384")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("CREATE TABLE evidence (src TEXT, dst TEXT, airline TEXT, records INTEGER, first_seen TEXT, last_seen TEXT, PRIMARY KEY(src,dst,airline)) WITHOUT ROWID")
        for batch in batches:
            accepted = {}
            for row in batch:
                stats["input_rows"] += 1
                reason, result = classify(row, airports, start, end, max_km)
                if reason:
                    stats[reason] += 1
                    continue
                stats["accepted_rows"] += 1
                src, dst, airline, timestamp = result
                key = (src, dst, airline)
                if key in accepted:
                    n, first, last = accepted[key]
                    accepted[key] = (n + 1, min(first, timestamp), max(last, timestamp))
                else:
                    accepted[key] = (1, timestamp, timestamp)
            with connection:
                connection.executemany("INSERT INTO evidence VALUES (?,?,?,?,?,?) ON CONFLICT(src,dst,airline) DO UPDATE SET records=records+excluded.records, first_seen=min(first_seen,excluded.first_seen), last_seen=max(last_seen,excluded.last_seen)",
                                       ((*key, *value) for key, value in accepted.items()))
            if progress and stats["input_rows"] % (20 * 32768) < len(batch):
                print(f"Processed {stats['input_rows']:,}; accepted {stats['accepted_rows']:,} rows", flush=True)
        if not stats["accepted_rows"]:
            raise ValueError("no reliable observations retained; no dataset published")
        connection.execute("CREATE TABLE airports (ident TEXT PRIMARY KEY, city TEXT)")
        connection.executemany("INSERT INTO airports VALUES (?,?)", ((ident, a["city"]) for ident, a in by_ident.items()))
        connection.execute("CREATE TABLE edges AS SELECT DISTINCT a.city AS src, b.city AS dst FROM evidence e JOIN airports a ON e.src=a.ident JOIN airports b ON e.dst=b.ident")
        stats["unique_city_edges"] = connection.execute("SELECT count(*) FROM edges").fetchone()[0]
        stats["unique_airport_airline_pairs"] = connection.execute("SELECT count(*) FROM evidence").fetchone()[0]
        stats["collapsed_city_pair_rows"] = stats["accepted_rows"] - stats["unique_city_edges"]
        stats["collapsed_airport_airline_rows"] = stats["accepted_rows"] - stats["unique_airport_airline_pairs"]
        write_tsv(folder / "flight.txt", None, connection.execute("SELECT src,dst FROM edges ORDER BY src,dst"))
        used = {r[0] for r in connection.execute("SELECT src FROM evidence UNION SELECT dst FROM evidence")}
        representatives = {}
        for ident in sorted(used):
            a = by_ident[ident]
            representatives.setdefault(a["city"], a)
        stats["cities"] = len(representatives)
        stats["airports_used"] = len(used)
        stats["countries"] = len({by_ident[i]["iso_country"] for i in used})
        write_tsv(folder / "cities.tsv", ["city", "latitude", "longitude"],
                  ((city, f"{a['latitude']:.6f}", f"{a['longitude']:.6f}") for city, a in sorted(representatives.items())))
        write_tsv(folder / "city_representatives.tsv", ["city", "representative_airport_ident"],
                  ((city, a["ident"]) for city, a in sorted(representatives.items())))
        fields = ["ident", "id", "icao", "iata", "city", "iso_country", "region", "latitude", "longitude"]
        write_tsv(folder / "airports.tsv", fields, ([by_ident[i][k] for k in fields] for i in sorted(used)))
        write_tsv(folder / "route_provenance.tsv", ["source_city", "destination_city", "source_airport_ident", "destination_airport_ident", "inferred_airline_icao", "accepted_input_rows", "first_departure_utc", "last_departure_utc"],
                  ((by_ident[s]["city"], by_ident[d]["city"], s, d, airline, n, first, last)
                   for s, d, airline, n, first, last in connection.execute("SELECT * FROM evidence ORDER BY src,dst,airline")))
    finally:
        connection.close()
        database.unlink(missing_ok=True)
    assert stats["input_rows"] == stats["accepted_rows"] + sum(stats[k] for k in REASONS)
    return dict(sorted(stats.items()))


def run(raw_dir, output, manifest_path, batch_size=32768, max_km=5.0):
    if not 1 <= batch_size <= 131072 or not math.isfinite(max_km) or not 0 < max_km <= 9:
        raise ValueError("batch-size must be 1..131072 and max-endpoint-km must be >0 and <=9")
    if output.exists():
        raise ValueError(f"output already exists: {output}; select a new directory")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, spec in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("manifest filenames must be basenames")
        verify(raw_dir / name, spec)
    airports, airport_stats = load_airports(raw_dir / "airports.csv", raw_dir / "countries.csv")
    start, end = utc_time(manifest["period_start_utc"]), utc_time(manifest["period_end_exclusive_utc"])
    if start >= end:
        raise ValueError("invalid manifest period")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish the complete output folder only after successful parsing/aggregation.
    with tempfile.TemporaryDirectory(prefix="phase3-", dir=output.parent) as temporary:
        stage = Path(temporary) / "dataset"
        stage.mkdir()
        stats = aggregate(parquet_rows(raw_dir / "flights.parquet", batch_size), airports, stage, start, end, max_km, progress=True)
        report = {"format_version": 1, "source_manifest": manifest, "airport_metadata_counts": airport_stats,
                  "row_counts": stats, "policy": {"ground_both_ends": True, "max_endpoint_km": max_km,
                  "single_icao_candidate": True, "airline": "callsign-inferred; not verified operating carrier",
                  "coordinate": "lexicographically first retained airport ident per city; not city center",
                  "duplicates": "unique directed city pairs; accepted_input_rows are NOT unique flights or frequencies"},
                  "outputs": {p.name: fingerprint(p) for p in sorted(stage.iterdir())}}
        (stage / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (stage / "ATTRIBUTION.txt").write_text(
            "Derived from MrAirspace aircraft-flight-schedules (ADSB.lol observations), 2026 Q3.\n"
            + manifest["release_url"] + "\nDatabase licensed ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/\n"
            "Airport metadata: OurAirports, Public Domain: https://ourairports.com/data/\n"
            "Observed historical connectivity only; incomplete coverage; no live schedules.\n"
            "See report.json and docs/phase3_import.md for sources, hashes, filtering and limitations.\n", encoding="utf-8")
        (stage / "LICENSE-ODbL.txt").write_bytes((raw_dir / "LICENSE-ODbL.txt").read_bytes())
        stage.rename(output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/phase3")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/generated/2026-q3")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/sources.json")
    parser.add_argument("--batch-size", type=int, default=32768)
    parser.add_argument("--max-endpoint-km", type=float, default=5.0)
    args = parser.parse_args(argv)
    try:
        report = run(args.raw_dir, args.output_dir, args.manifest, args.batch_size, args.max_endpoint_km)
    except (OSError, ValueError, csv.Error, sqlite3.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["row_counts"], indent=2))
    print(f"Published {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
