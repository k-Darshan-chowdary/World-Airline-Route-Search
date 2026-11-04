"""Smoke test the standard-library GUI bridge with the actual compiled CLI."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.gui.route_bridge import query, read_cities, route_coordinates

EXE = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()

class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cities = read_cities(SAMPLE)
        cls.labels = [city["city"] for city in cls.cities]

    def test_metadata(self):
        self.assertEqual(len(self.cities), 12)
        self.assertEqual(self.cities[0]["city"], "Dallas, United States")
        self.assertEqual(self.cities[0]["id"], 0)

    def test_q1(self):
        response = query(EXE, SAMPLE, "q1", {
            "from": "Dallas, United States",
            "to": "New York, United States",
            "max_connections": "1",
        })
        self.assertEqual(response["status"], "found")
        self.assertEqual(response["flights"], 1)
        self.assertEqual(len(route_coordinates(response, self.cities)), 2)

    def test_q2(self):
        response = query(EXE, SAMPLE, "q2", {
            "from": "Dallas, United States", "to": "Paris, France",
            "via_b": "New York, United States",
            "via_c": "London, United Kingdom",
        })
        self.assertEqual(response["status"], "found")
        self.assertEqual(response["flights"], 3)
        self.assertEqual(len(route_coordinates(response, self.cities)), 4)

    def test_q3(self):
        response = query(EXE, SAMPLE, "q3", {
            "round_trip": "Auckland, New Zealand",
        })
        self.assertEqual(response["status"], "found")
        self.assertTrue(response["optimal"])
        self.assertEqual(len(route_coordinates(response, self.cities)), 3)

    def test_q4(self):
        response = query(EXE, SAMPLE, "q4", {
            "meeting_a": "Dallas, United States",
            "meeting_b": "New York, United States",
            "meeting_c": "London, United Kingdom",
        })
        self.assertEqual(response["status"], "found")
        self.assertEqual(response["meeting_city"]["city"], "Paris, France")
        self.assertEqual(response["total_flights"], 6)

    def test_bad_query(self):
        with self.assertRaises(ValueError):
            query(EXE, SAMPLE, "q6", {})

    def test_unknown_city(self):
        with self.assertRaises(RuntimeError):
            query(EXE, SAMPLE, "q3", {"round_trip": "Not Here, None"})

    def test_coordinate_metadata_mismatch(self):
        with self.assertRaises(ValueError):
            route_coordinates({"route": [{"id": 0, "city": "Wrong, Country"}]},
                              self.cities)

if __name__ == "__main__":
    unittest.main()
