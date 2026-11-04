"""Quick Q3/Q4 CLI and JSON regression checks on the bundled sample."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

EXE = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()

def call(*flags):
    return subprocess.run(
        [str(EXE), "--data-dir", str(SAMPLE), *flags],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )

class RouteTests(unittest.TestCase):
    def test_q3_exact(self):
        p = call("--round-trip", "Auckland, New Zealand", "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout)
        self.assertEqual((r["query"], r["status"], r["method"]), ("q3", "found", "exact"))
        self.assertTrue(r["optimal"])
        self.assertEqual(r["flights"], 2)
        self.assertEqual(r["reachable_cities"], 2)
        self.assertEqual([x["city"] for x in r["route"]],
                         ["Auckland, New Zealand", "Sydney, Australia", "Auckland, New Zealand"])

    def test_q3_no_return(self):
        p = call("--round-trip", "Dallas, United States", "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout)
        self.assertEqual((r["query"], r["status"]), ("q3", "no_return"))
        self.assertEqual(r["route"], [])
        self.assertIsNone(r["flights"])

    def test_q4_meeting(self):
        p = call("--meeting-a", "Dallas, United States",
                 "--meeting-b", "New York, United States",
                 "--meeting-c", "London, United Kingdom", "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout)
        self.assertEqual((r["query"], r["status"]), ("q4", "found"))
        self.assertEqual(r["meeting_city"]["city"], "Paris, France")
        self.assertEqual(r["total_flights"], 6)
        self.assertEqual(r["distances"], {"from_a": 3, "from_b": 2, "from_c": 1})

    def test_q4_missing_flag(self):
        p = call("--meeting-a", "Dallas, United States", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["status"], "error")

    def test_q3_unknown_city(self):
        p = call("--round-trip", "Unknown, Country", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["status"], "error")

    def test_q3_q4_conflict(self):
        p = call("--round-trip", "Dallas, United States",
                 "--meeting-a", "Dallas, United States",
                 "--meeting-b", "London, United Kingdom",
                 "--meeting-c", "Paris, France", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["status"], "error")

if __name__ == "__main__":
    unittest.main()
