"""Exercise the compiled CLI, including failure exit codes and directed paths."""
from pathlib import Path
import subprocess
import sys
import unittest

CLI = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([str(CLI), *args], text=True, encoding="utf-8",
                              capture_output=True, timeout=30)

    def sample(self, *args):
        return self.run_cli("--data-dir", str(SAMPLE), *args)

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: airline_graph", result.stdout)

    def test_counts(self):
        result = self.sample("--expect-cities", "12", "--expect-routes", "20")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("12 cities; 20 directed routes", result.stdout)

    def test_bad_counts(self):
        for option in ("--expect-cities", "--expect-routes"):
            for value in ("-1", "+12", " 12", "12 ", "12x", "1.0", "", "9999999999999999999999999999999"):
                with self.subTest(option=option, value=value):
                    result = self.sample(option, value)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("invalid nonnegative count", result.stderr)

    def test_count_mismatch(self):
        for option, value in (("--expect-cities", "0"), ("--expect-routes", "21")):
            result = self.sample(option, value)
            self.assertEqual(result.returncode, 1)
            self.assertIn("differs from expected counts", result.stderr)

    def test_shortest_path(self):
        result = self.sample("--from", "Dallas, United States", "--to", "Auckland, New Zealand")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(9 flights): Dallas, United States -> New York, United States", result.stdout)
        self.assertIn("Sydney, Australia -> Auckland, New Zealand", result.stdout)

    def test_same_city(self):
        result = self.sample("--from", "Dallas, United States", "--to", "Dallas, United States")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(0 flights): Dallas, United States", result.stdout)

    def test_unreachable(self):
        result = self.sample("--from", "Auckland, New Zealand", "--to", "Dallas, United States")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No directed route exists", result.stdout)
        self.assertIn("Historical observed connectivity", result.stdout)

    def test_unknown_city(self):
        result = self.sample("--from", "Missing, Test", "--to", "Dallas, United States")
        self.assertEqual(result.returncode, 1)
        self.assertIn("city not found", result.stderr)

    def test_missing_endpoint(self):
        for flag in ("--from", "--to"):
            result = self.sample(flag, "Dallas, United States")
            self.assertEqual(result.returncode, 1)
            self.assertIn("supplied together", result.stderr)

    def test_missing_value_and_unknown_flag(self):
        for args in (("--data-dir",), ("--expect-cities",), ("--unknown", "value")):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR:", result.stderr)

    def test_missing_dataset(self):
        result = self.run_cli("--data-dir", str(SAMPLE / "does-not-exist"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot open", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
