"""Offline checksum tampering and teammate setup orchestration regressions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_lock as locked
import setup_dataset as setup
from download_phase3 import fingerprint


class DatasetSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.raw, self.output = self.folder / "raw", self.folder / "output"
        self.raw.mkdir()
        self.output.mkdir()
        self.lock = json.loads(locked.LOCK.read_text(encoding="utf-8"))
        self.manifest = copy.deepcopy(self.lock["sources"])
        for name in locked.INPUTS:
            (self.raw / name).write_bytes(("synthetic input: " + name).encode())
            self.manifest["files"][name].update(fingerprint(self.raw / name))
        self.lock["sources"] = self.manifest
        for group in ("outputs", "notices"):
            for name in self.lock[group]:
                (self.output / name).write_bytes(("synthetic output: " + name).encode())
                self.lock[group][name] = fingerprint(self.output / name)
        self.report = {**self.lock["expected_report"], "source_manifest": self.manifest, "outputs": copy.deepcopy(self.lock["outputs"])}
        self.source_path, self.lock_path = self.folder / "sources.json", self.folder / "lock.json"
        self.save()

    def save(self):
        for path, value in ((self.source_path, self.manifest), (self.lock_path, self.lock), (self.output / "report.json", self.report)):
            path.write_text(json.dumps(value), encoding="utf-8")

    def verify_output(self):
        return locked.verify_outputs(self.output, self.source_path, self.lock_path)

    def test_committed_official_source_and_output_locks_match(self):
        source, lock = locked.check_pins()
        self.assertEqual(source["source_commit"], "d4906dedba893bea4f7ad5966a81409d6a62336c")
        self.assertEqual(source["asset_id"], 637792988)
        self.assertEqual(set(lock["outputs"]), locked.TABLES)

    def test_changed_source_pin_fails(self):
        # The separately serialized lock remains the reviewed value.
        self.manifest["files"]["flights.parquet"]["sha256"] = "0" * 64
        self.source_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from reviewed"):
            locked.check_pins(self.source_path, self.lock_path)

    def test_incomplete_lock_fails(self):
        self.lock["outputs"].pop("flight.txt")
        self.save()
        with self.assertRaisesRegex(ValueError, "file set"):
            locked.check_pins(self.source_path, self.lock_path)

    def test_all_pinned_input_and_output_bytes_are_checked(self):
        locked.verify_inputs(self.raw, self.source_path, self.lock_path)
        # Format/provenance validation has its own real-Parquet integration test;
        # these deliberately tiny files exercise the independent checksum layer.
        with patch.object(locked, "validate", return_value=self.report["row_counts"]) as validate:
            self.assertEqual(self.verify_output(), self.report["row_counts"])
            validate.assert_called_once_with(self.output)
        (self.raw / "flights.parquet").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            locked.verify_inputs(self.raw, self.source_path, self.lock_path)

    def test_changing_output_and_its_report_cannot_bypass_reviewed_lock(self):
        (self.output / "flight.txt").write_bytes(b"changed")
        self.report["outputs"]["flight.txt"] = fingerprint(self.output / "flight.txt")
        self.save()
        with self.assertRaisesRegex(ValueError, "hashes differ from reviewed"):
            self.verify_output()

    def test_missing_license_notice_is_rejected(self):
        (self.output / "LICENSE-ODbL.txt").unlink()
        with self.assertRaises(OSError):
            self.verify_output()

    def test_changed_counts_are_rejected(self):
        self.report["row_counts"] = dict(self.report["row_counts"], cities=1)
        self.save()
        with self.assertRaisesRegex(ValueError, "counts/policy"):
            self.verify_output()

    def test_offline_rerun_verifies_without_downloading_or_overwriting(self):
        counts = self.report["row_counts"]
        with patch.object(setup, "check_pins", return_value=(self.manifest, self.lock)), \
             patch.object(setup, "verify_outputs", return_value=counts) as outputs, \
             patch.object(setup, "verify_inputs") as inputs, \
             patch.object(setup, "download") as download, patch.object(setup, "run") as run:
            setup.provision(self.raw, self.output, offline=True)
            outputs.assert_called_once_with(self.output)
            inputs.assert_called_once_with(self.raw)
            download.assert_not_called()
            run.assert_not_called()

    def test_invalid_existing_output_stops_before_download(self):
        with patch.object(setup, "check_pins", return_value=(self.manifest, self.lock)), \
             patch.object(setup, "verify_outputs", side_effect=ValueError("existing output mismatch")), \
             patch.object(setup, "download") as download, patch.object(setup, "run") as run:
            with self.assertRaisesRegex(ValueError, "existing output mismatch"):
                setup.provision(self.raw, self.output)
            download.assert_not_called()
            run.assert_not_called()

    def test_failed_child_command_returns_failure(self):
        with patch.object(setup, "check_pins"), patch.object(setup, "prepare_environment", return_value=Path(sys.executable)), \
             patch.object(setup, "call", side_effect=subprocess.CalledProcessError(1, "tests")):
            self.assertEqual(setup.main([]), 1)


if __name__ == "__main__":
    unittest.main()
