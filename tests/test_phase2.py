"""Dataset validation tests only; no graph or BFS implementation."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_phase2", ROOT / "scripts" / "check_phase2.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.cities = "city\tlatitude\tlongitude\nAlpha, Country A\t1\t2\nBeta, Country B\t3\t4\n"
        self.edges = "# Synthetic fixture\nAlpha, Country A\tBeta, Country B\n"

    def write_fixture(self):
        (self.folder / "cities.tsv").write_text(self.cities, encoding="utf-8")
        (self.folder / "flight.txt").write_text(self.edges, encoding="utf-8")

    def assert_invalid(self, message):
        self.write_fixture()
        with self.assertRaisesRegex(ValueError, message):
            CHECK.check_data(self.folder)

    def test_sample_counts(self):
        self.assertEqual(CHECK.check_data(ROOT / "data" / "sample"), (12, 20))

    def test_one_way_edge_needs_no_reverse(self):
        self.write_fixture()
        self.assertEqual(CHECK.check_data(self.folder), (2, 1))

    def test_duplicate_edge(self):
        self.edges += "Alpha, Country A\tBeta, Country B\n"
        self.assert_invalid("duplicate directed edge")

    def test_unknown_endpoint(self):
        self.edges = "Alpha, Country A\tGamma, Country C\n"
        self.assert_invalid("missing city metadata")

    def test_non_finite_coordinate(self):
        self.cities = self.cities.replace("\t1\t2", "\tnan\t2")
        self.assert_invalid("finite")

    def test_out_of_range_coordinate(self):
        self.cities = self.cities.replace("\t1\t2", "\t91\t2")
        self.assert_invalid("geographic bounds")

    def test_duplicate_city(self):
        self.cities += "Alpha, Country A\t1\t2\n"
        self.assert_invalid("duplicate city")

    def test_wrong_delimiter(self):
        self.edges = "Alpha, Country A|Beta, Country B\n"
        self.assert_invalid("two TAB-separated")

    def test_invalid_label(self):
        self.cities = self.cities.replace("Alpha, Country A", "Alpha")
        self.assert_invalid("invalid City, Country")

    def test_self_loop(self):
        self.edges = "Alpha, Country A\tAlpha, Country A\n"
        self.assert_invalid("self-loop")

    def test_unused_city(self):
        self.cities += "Gamma, Country C\t5\t6\n"
        self.assert_invalid("without route endpoints")

    def test_empty_edges(self):
        self.edges = "# only comments\n"
        self.assert_invalid("no directed edges")

    def test_cli_rejects_wrong_counts(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_phase2.py"), "--expect-edges", "999"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 999 directed edges, found 20", result.stderr)


if __name__ == "__main__":
    unittest.main()
