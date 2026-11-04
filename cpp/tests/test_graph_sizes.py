"""Repeatable small/medium graph checks with actual subprocess timing.

This intentionally measures wall-clock launch + load + search rather than
claiming it measures algorithm time alone. It never downloads data.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter
import unittest

EXE = Path(sys.argv.pop(1)).resolve()


def fixture(folder: Path, count: int):
    names = [f"City{i}, Testland" for i in range(count)]
    (folder / "cities.tsv").write_text(
        "city\tlatitude\tlongitude\n"
        + "".join(f"{city}\t0\t0\n" for city in names), encoding="utf-8"
    )
    (folder / "flight.txt").write_text(
        "".join(
            f"{names[i]}\t{names[(i + 1) % count]}\n"
            for i in range(count)
        ), encoding="utf-8"
    )
    return names


def run(exe: Path, directory: Path, *args):
    start = perf_counter()
    completed = subprocess.run(
        [str(exe), "--data-dir", str(directory), *args, "--json"],
        capture_output=True, encoding="utf-8", text=True, timeout=20
    )
    elapsed_ms = (perf_counter() - start) * 1000
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout), elapsed_ms


class ScalingTests(unittest.TestCase):
    def test_six_twenty_and_fifty_vertices(self):
        with tempfile.TemporaryDirectory(prefix="airline-size-check-") as tmp:
            directory = Path(tmp)
            for count in (6, 18, 20, 50):
                names = fixture(directory, count)
                q1, elapsed_q1 = run(
                    EXE, directory, "--from", names[0], "--to",
                    names[-1], "--max-connections", str(count)
                )
                self.assertEqual(q1["status"], "found")
                self.assertEqual(q1["flights"], count - 1)
                q3, elapsed_q3 = run(
                    EXE, directory, "--round-trip", names[0]
                )
                self.assertEqual(q3["status"], "found")
                self.assertEqual(q3["flights"], count)
                self.assertEqual(q3["reachable_cities"], count)
                self.assertEqual(q3["method"], "exact" if count <= 18 else "heuristic")
                if count > 18:
                    self.assertFalse(q3["optimal"])
                else:
                    self.assertTrue(q3["optimal"])
                q4, elapsed_q4 = run(
                    EXE, directory, "--meeting-a", names[0],
                    "--meeting-b", names[1], "--meeting-c", names[2]
                )
                self.assertEqual(q4["status"], "found")
                self.assertEqual(q4["meeting_city"]["city"], names[3])
                print(
                    f"{count} vertices / {count} directed edges: "
                    f"Q1 {elapsed_q1:.2f} ms, "
                    f"Q3 {elapsed_q3:.2f} ms, "
                    f"Q4 {elapsed_q4:.2f} ms "
                    "(end-to-end including process start and graph load)"
                )


if __name__ == "__main__":
    unittest.main()
