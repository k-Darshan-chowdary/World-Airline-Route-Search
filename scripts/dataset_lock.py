"""Verify reviewed source pins and dataset hashes independently of generated reports."""
import argparse
import json
from pathlib import Path
import sys

from download_phase3 import verify
from validate_global import validate

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "data/dataset_2026_q3.lock.json"
SOURCES = ROOT / "data/sources.json"
RAW = ROOT / "data/raw/phase3"
OUTPUT = ROOT / "data/generated/2026-q3"
TABLES = {"airports.tsv", "cities.tsv", "city_representatives.tsv", "flight.txt", "route_provenance.tsv"}
INPUTS = {"airports.csv", "countries.csv", "README-MrAirspace.md", "LICENSE-ODbL.txt", "flights.parquet"}
NOTICES = {"ATTRIBUTION.txt", "LICENSE-ODbL.txt"}


def check_pins(manifest_path=SOURCES, lock_path=LOCK):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    if lock["lock_version"] != 1 or manifest != lock["sources"]:
        raise ValueError("source manifest differs from reviewed dataset lock")
    if set(manifest["files"]) != INPUTS or set(lock["outputs"]) != TABLES or set(lock["notices"]) != NOTICES:
        raise ValueError("dataset lock has an incomplete or unexpected file set")
    for group in (manifest["files"], lock["outputs"], lock["notices"]):
        for name, spec in group.items():
            if Path(name).name != name or spec["bytes"] <= 0 or len(spec["sha256"]) != 64:
                raise ValueError("invalid dataset lock entry")
            int(spec["sha256"], 16)
    return manifest, lock


def verify_inputs(raw_dir=RAW, manifest_path=SOURCES, lock_path=LOCK):
    manifest, _ = check_pins(manifest_path, lock_path)
    for name, spec in manifest["files"].items():
        verify(Path(raw_dir) / name, spec)
        print(f"Input SHA-256 verified: {name}", flush=True)


def source_identity(manifest):
    # Preserve pre-onboarding reports using short source commit URLs; the bytes,
    # period, license and source identity must still match the reviewed locks.
    keys = ("ourairports_commit", "release_tag", "published_at", "period_start_utc",
            "period_end_exclusive_utc", "license", "release_url", "airport_terms_url")
    return {**{k: manifest[k] for k in keys}, "files": {
        name: {k: spec[k] for k in ("bytes", "sha256")} for name, spec in manifest["files"].items()}}


def verify_outputs(folder=OUTPUT, manifest_path=SOURCES, lock_path=LOCK):
    folder = Path(folder)
    manifest, lock = check_pins(manifest_path, lock_path)
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    if source_identity(report["source_manifest"]) != source_identity(manifest):
        raise ValueError("generated report source identity differs from reviewed source pins")
    if any(report[k] != value for k, value in lock["expected_report"].items()):
        raise ValueError("generated counts/policy differ from reviewed dataset lock")
    if report["outputs"] != lock["outputs"]:
        raise ValueError("generated report hashes differ from reviewed dataset lock")
    for name, spec in {**lock["outputs"], **lock["notices"]}.items():
        verify(folder / name, spec)
        print(f"Output SHA-256 verified: {name}", flush=True)
    return validate(folder)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pins-only", action="store_true", help="Check committed locks; no downloads or local data required")
    mode.add_argument("--inputs-only", action="store_true")
    mode.add_argument("--outputs-only", action="store_true")
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--data-dir", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        check_pins()
        if not args.pins_only:
            if not args.outputs_only:
                verify_inputs(args.raw_dir)
            if not args.inputs_only:
                verify_outputs(args.data_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: reviewed dataset pins/checksums verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
