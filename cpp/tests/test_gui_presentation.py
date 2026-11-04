"""Presentation summaries are pure Python and do not require Qt."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.gui.presentation import describe_result, Q4_COLORS


def city(name, index):
    return {"city": name, "id": index}


class PresentationTests(unittest.TestCase):
    def test_q1_direct_route_and_connection_limit(self):
        data = {
            "query": "q1", "status": "found", "flights": 1,
            "connections": 0, "exclusive_connection_limit": 1,
            "route": [city("Dallas", 0), city("New York", 1)],
        }
        description = describe_result(data)
        self.assertIn("Shortest", description.title)
        self.assertIn("1 flight", description.metric)
        self.assertIn("Dallas", description.lines[0])
        self.assertIn("New York", description.lines[0])

    def test_q1_same_city(self):
        data = {
            "query": "q1", "status": "found", "flights": 0,
            "connections": 0, "exclusive_connection_limit": 3,
            "route": [city("Dallas", 0)],
        }
        description = describe_result(data)
        self.assertEqual(description.title, "Already at destination")
        self.assertEqual(description.metric, "0 flights · 0 connections")

    def test_q1_limit_failure(self):
        data = {"query": "q1", "status": "connection_limit"}
        description = describe_result(data)
        self.assertIn("limit", description.detail)
        self.assertEqual(description.lines, ())

    def test_q2_required_stops(self):
        data = {
            "query": "q2", "status": "found", "flights": 3,
            "connections": 2,
            "waypoint_order": [city("London", 2), city("Paris", 3)],
            "route": [city("Dallas", 0), city("London", 2),
                      city("Paris", 3), city("Tokyo", 4)],
        }
        result = describe_result(data)
        self.assertIn("London → Paris", result.detail)
        self.assertIn("3 flights", result.metric)

    def test_q3_exact(self):
        data = {
            "query": "q3", "status": "found", "flights": 3,
            "reachable_cities": 3, "method": "exact", "optimal": True,
            "route": [city("A", 0), city("B", 1), city("C", 2), city("A", 0)],
        }
        result = describe_result(data)
        self.assertIn("Shortest", result.title)
        self.assertIn("EXACT", result.metric)
        self.assertFalse(result.warning)

    def test_q3_heuristic(self):
        data = {
            "query": "q3", "status": "found", "flights": 20,
            "reachable_cities": 15, "method": "heuristic", "optimal": False,
            "route": [city("A", 0), city("B", 1), city("A", 0)],
        }
        result = describe_result(data)
        self.assertIn("Approximate", result.title)
        self.assertIn("HEURISTIC", result.metric)
        self.assertIn("not guaranteed", result.warning)

    def test_q3_no_tour_and_heuristic_failed(self):
        no_tour = describe_result({"query": "q3", "status": "no_tour"})
        failed = describe_result({"query": "q3", "status": "heuristic_failed"})
        self.assertNotEqual(no_tour.detail, failed.detail)
        self.assertIn("may still exist", failed.detail)
        self.assertIn("does not prove", failed.warning)

    def test_q4_three_routes_and_legend(self):
        data = {
            "query": "q4", "status": "found", "total_flights": 6,
            "meeting_city": city("Paris", 3),
            "routes": {
                "from_a": [city("Dallas", 0), city("Paris", 3)],
                "from_b": [city("New York", 1), city("Paris", 3)],
                "from_c": [city("London", 2), city("Paris", 3)],
            },
            "distances": {"from_a": 3, "from_b": 2, "from_c": 1},
        }
        result = describe_result(data)
        self.assertIn("Paris", result.title)
        self.assertEqual(len(result.lines), 3)
        self.assertEqual(len(result.legend), 3)
        self.assertEqual([color for _, color in result.legend], list(Q4_COLORS.values()))
        self.assertIn("6 flight legs · 3 connections", result.metric)

    def test_long_round_trip_is_readable(self):
        nodes = [city(f"Long City {i}, Testland", i) for i in range(40)]
        nodes.append(nodes[0])
        result = describe_result({
            "query": "q3", "status": "found", "flights": 40,
            "reachable_cities": 40, "method": "heuristic", "optimal": False,
            "route": nodes,
        })
        self.assertLess(len(result.lines[0]), 260)
        self.assertIn("full path in JSON", result.lines[0])
        self.assertIn("not guaranteed", result.warning)

    def test_no_meeting(self):
        result = describe_result({"query": "q4", "status": "unreachable"})
        self.assertIn("meeting", result.title.lower())

    def test_invalid_question(self):
        with self.assertRaises(ValueError):
            describe_result({"query": "q5", "status": "found"})


if __name__ == "__main__":
    unittest.main()
