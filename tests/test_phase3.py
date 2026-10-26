"""Small deterministic importer fixtures; never download data during tests."""
import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_global as imp
import download_phase3 as dl
import validate_global as validator
from check_phase2 import check_data


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.airports = {
            "KAAA": dict(id="101", ident="KAAA", icao="KAAA", iata="AAA", city="Alpha, Country A", iso_country="AA", region="AA-X", latitude=1.0, longitude=2.0),
            "KBBB": dict(id="202", ident="KBBB", icao="KBBB", iata="BBB", city="Beta, Country B", iso_country="BB", region="BB-X", latitude=3.0, longitude=4.0),
            "KAAC": dict(id="303", ident="KAAC", icao="KAAC", iata="AAC", city="Alpha, Country A", iso_country="AA", region="AA-X", latitude=1.0, longitude=2.0),
        }
        self.start = imp.utc_time("2026-07-01T00:00:00Z")
        self.end = imp.utc_time("2026-10-01T00:00:00Z")
        self.row = {"Airline": "TST", "Callsign": "TST123"}
        for end, code in (("Origin", "KAAA"), ("Destination", "KBBB")):
            a = self.airports[code]
            self.row.update({f"Track_{end}_Lat": str(a["latitude"]), f"Track_{end}_Lon": str(a["longitude"]),
                             f"Track_{end}_FL_Ft": "ground", f"Track_{end}_ApplicableAirports": repr([code]),
                             f"Track_{end}_DateTime_UTC": "2026-07-01 01:00:00" if end == "Origin" else "2026-07-01 02:00:00"})

    def classify(self, **updates):
        return imp.classify(dict(self.row, **updates), self.airports, self.start, self.end, 5)[0]

    def aggregate(self, batches, name="result"):
        folder = self.folder / name
        folder.mkdir()
        counts = imp.aggregate(batches, self.airports, folder, self.start, self.end)
        return folder, counts

    def test_valid_actual_list_string_and_utc_boundary(self):
        self.assertIsNone(self.classify(Track_Origin_DateTime_UTC="2026-07-01 00:00:00"))

    def test_period_end_and_previous_year_rejected(self):
        for start, end in (("2026-10-01 00:00:00", "2026-10-01 01:00:00"), ("2025-07-01 00:00:00", "2025-07-01 01:00:00")):
            with self.subTest(start=start):
                self.assertEqual(self.classify(Track_Origin_DateTime_UTC=start, Track_Destination_DateTime_UTC=end), "outside_period")

    def test_invalid_missing_and_reversed_times(self):
        for value in ("-", None, "2026-07-02 01:00:00"):
            with self.subTest(value=value):
                self.assertEqual(self.classify(Track_Origin_DateTime_UTC=value), "invalid_time")

    def test_airline_is_required_and_consistent_with_callsign(self):
        self.assertEqual(self.classify(Airline="-"), "missing_airline")
        self.assertEqual(self.classify(Callsign="BAD123"), "callsign_mismatch")
        self.assertEqual(self.classify(Callsign="TSTABC"), "callsign_mismatch")

    def test_numeric_altitude_not_assumed_ground(self):
        self.assertEqual(self.classify(Track_Origin_FL_Ft="0"), "not_ground")

    def test_ambiguous_and_malformed_candidates_rejected(self):
        for value in ("['KAAA','KAAC']", "KAAA", "['AAA']", "[]", "-", "__import__('os')"):
            with self.subTest(value=value):
                self.assertEqual(self.classify(Track_Origin_ApplicableAirports=value), "ambiguous_or_missing_airport")

    def test_no_numeric_id_or_iata_guessing(self):
        self.assertEqual(self.classify(Track_Origin_ApplicableAirports="['ZZZZ']"), "unmatched_airport")

    def test_invalid_coordinates_and_distance(self):
        for value in ("nan", "inf", "91", "-"):
            with self.subTest(value=value):
                self.assertEqual(self.classify(Track_Origin_Lat=value), "invalid_track_coordinates")
        self.assertEqual(self.classify(Track_Origin_Lat="20"), "endpoint_too_far")

    def test_city_self_loop_after_airport_aggregation(self):
        self.assertEqual(self.classify(Track_Destination_ApplicableAirports="['KAAC']", Track_Destination_Lat="1", Track_Destination_Lon="2"), "city_self_loop")

    def test_direction_dedup_provenance_counts_and_reconciliation(self):
        second = dict(self.row, Airline="OTH", Callsign="OTH9")
        bad = dict(self.row, Airline="-")
        folder, counts = self.aggregate([[self.row], [self.row, second, bad]])
        self.assertEqual(check_data(folder), (2, 1))
        self.assertEqual(counts["accepted_rows"], 3)
        self.assertEqual(counts["collapsed_city_pair_rows"], 2)
        self.assertEqual(counts["collapsed_airport_airline_rows"], 1)
        self.assertEqual(counts["input_rows"], counts["accepted_rows"] + sum(counts[k] for k in imp.REASONS))
        with (folder / "route_provenance.tsv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        self.assertEqual({r["inferred_airline_icao"]: int(r["accepted_input_rows"]) for r in rows}, {"TST": 2, "OTH": 1})
        self.assertEqual((folder / "flight.txt").read_text(), "Alpha, Country A\tBeta, Country B\n")

    def test_batch_size_and_input_order_do_not_change_outputs(self):
        second = dict(self.row, Airline="OTH", Callsign="OTH9")
        a, ac = self.aggregate([[self.row, second, self.row]], "a")
        b, bc = self.aggregate([[second], [self.row], [self.row]], "b")
        self.assertEqual(ac, bc)
        self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()}, {p.name: p.read_bytes() for p in b.iterdir()})

    def metadata_files(self, rows=None):
        rows = rows or list(self.airports.values())
        ap = self.folder / "airports.csv"
        fields = sorted(imp.AIRPORT_FIELDS)
        with ap.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for a in rows:
                city, _ = a["city"].split(", ")
                writer.writerow(dict(id=a["id"], ident=a["ident"], icao_code=a["icao"], iata_code=a["iata"], type="large_airport", municipality=city, iso_country=a["iso_country"], iso_region=a["region"], latitude_deg=a["latitude"], longitude_deg=a["longitude"]))
        cp = self.folder / "countries.csv"
        cp.write_text('code,name\nAA,Country A\nBB,Country B\n', encoding="utf-8")
        return ap, cp

    def test_ourairports_numeric_ids_are_separate_and_codes_are_exact(self):
        airports, stats = imp.load_airports(*self.metadata_files())
        self.assertEqual(airports["KAAA"]["id"], "101")
        self.assertNotIn("101", airports)
        self.assertEqual(stats["usable_airports"], 3)

    def test_duplicate_icao_excluded_and_duplicate_internal_id_fails(self):
        rows = copy.deepcopy(list(self.airports.values()))
        rows[-1]["icao"] = "KAAA"
        airports, stats = imp.load_airports(*self.metadata_files(rows))
        self.assertNotIn("KAAA", airports)
        self.assertEqual(stats["ambiguous_icao_codes"], 1)
        rows[-1]["id"] = "101"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            imp.load_airports(*self.metadata_files(rows))

    def test_same_named_cities_in_different_regions_excluded(self):
        rows = copy.deepcopy(list(self.airports.values()))
        rows[-1]["region"] = "AA-Y"
        airports, stats = imp.load_airports(*self.metadata_files(rows))
        self.assertEqual(set(airports), {"KBBB"})
        self.assertEqual(stats["city_region_collision_labels"], 1)

    def test_distance_handles_antimeridian(self):
        self.assertLess(imp.distance_km((0, 179.99), (0, -179.99)), 3)

    def test_reverse_direction_requires_its_own_observation(self):
        reverse = dict(self.row)
        for field in ("Lat", "Lon", "ApplicableAirports"):
            reverse[f"Track_Origin_{field}"] = self.row[f"Track_Destination_{field}"]
            reverse[f"Track_Destination_{field}"] = self.row[f"Track_Origin_{field}"]
        folder, counts = self.aggregate([[self.row, reverse]])
        self.assertEqual(check_data(folder), (2, 2))
        self.assertEqual(counts["unique_city_edges"], 2)

    def test_label_grammar_preserves_unicode_and_rejects_delimiters(self):
        self.assertEqual(imp.label_part("  Montre\u0301al  "), "Montréal")
        for value in ("A,B", "A\tB", "A\nB", "#comment", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                imp.label_part(value)

    def test_empty_retained_set_fails(self):
        with self.assertRaisesRegex(ValueError, "no reliable observations"):
            self.aggregate([[dict(self.row, Airline="-")]])

    def test_duplicate_csv_header_fails(self):
        file = self.folder / "bad.csv"
        file.write_text("code,name,name\nAA,A,B\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate header"):
            list(imp.read_csv(file, {"code", "name"}))

    def test_checksum_and_existing_output_fail_closed(self):
        ap, _ = self.metadata_files()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            dl.verify(ap, {"bytes": ap.stat().st_size, "sha256": "0" * 64})
        with self.assertRaisesRegex(ValueError, "already exists"):
            imp.run(self.folder, self.folder, self.folder / "missing.json")

    def test_download_stream_verifies_and_preserves_existing_files(self):
        body = b"synthetic test input"
        expected = self.folder / "expected"
        expected.write_bytes(body)
        spec = dict(url="https://example.invalid/input", **dl.fingerprint(expected))
        folder = self.folder / "downloads"
        with patch.object(dl.urllib.request, "urlopen", return_value=io.BytesIO(body)):
            dl.download(folder, {"files": {"input": spec}})
        with patch.object(dl.urllib.request, "urlopen", side_effect=AssertionError("no download needed")):
            dl.download(folder, {"files": {"input": spec}})
        (folder / "input").write_bytes(b"existing changed file")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            dl.download(folder, {"files": {"input": spec}})
        self.assertEqual((folder / "input").read_bytes(), b"existing changed file")

    def test_bad_download_never_publishes_partial_file(self):
        with patch.object(dl.urllib.request, "urlopen", return_value=io.BytesIO(b"bad")):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                dl.download(self.folder, {"files": {"input": {"url": "https://example.invalid", "bytes": 3, "sha256": "0" * 64}}})
        self.assertFalse((self.folder / "input").exists())
        self.assertFalse((self.folder / "input.part").exists())

    def test_real_parquet_adapter_and_transactional_publish(self):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("install requirements-import.txt to exercise actual Parquet IO")
        self.metadata_files()
        pq.write_table(pa.Table.from_pylist([self.row, self.row]), self.folder / "flights.parquet")
        (self.folder / "LICENSE-ODbL.txt").write_text("synthetic license fixture", encoding="utf-8")
        manifest = {"files": {name: dl.fingerprint(self.folder / name) for name in ("airports.csv", "countries.csv", "flights.parquet", "LICENSE-ODbL.txt")},
                    "period_start_utc": self.start.isoformat(), "period_end_exclusive_utc": self.end.isoformat(), "release_url": "https://example.invalid/synthetic"}
        path = self.folder / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        output = self.folder / "published"
        report = imp.run(self.folder, output, path, batch_size=1)
        self.assertEqual(check_data(output), (2, 1))
        self.assertEqual(validator.validate(output), report["row_counts"])
        self.assertEqual(report["row_counts"]["accepted_rows"], 2)
        for name, spec in report["outputs"].items():
            dl.verify(output / name, spec)
        (output / "flight.txt").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validator.validate(output)
        # A schema change must fail without publishing an output directory.
        pq.write_table(pa.table({"unrelated": ["bad"]}), self.folder / "flights.parquet")
        manifest["files"]["flights.parquet"] = dl.fingerprint(self.folder / "flights.parquet")
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            imp.run(self.folder, self.folder / "failed", path)
        self.assertFalse((self.folder / "failed").exists())


if __name__ == "__main__":
    unittest.main()
