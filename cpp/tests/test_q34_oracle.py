"""Independent randomized CLI checks for the Q3/Q4 graph algorithms.

Generates small directed graphs and compares C++ results to Python oracles.
No network, third-party packages, or historical dataset required.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

EXECUTABLE = Path(sys.argv.pop(1)).resolve()


def labels(n):
    return [f"City{i}, Testland" for i in range(n)]


def make_data(folder, names, edges):
    folder.mkdir(exist_ok=True)
    (folder / "cities.tsv").write_text(
        "city\tlatitude\tlongitude\n"
        + "".join(f"{name}\t0\t0\n" for name in names),
        encoding="utf-8",
    )
    (folder / "flight.txt").write_text(
        "".join(f"{names[a]}\t{names[b]}\n" for a, b in sorted(edges)),
        encoding="utf-8",
    )


def query(directory, *flags):
    p = subprocess.run(
        [str(EXECUTABLE), "--data-dir", str(directory), *flags, "--json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", timeout=20,
    )
    if p.returncode != 0:
        raise AssertionError(f"Backend error: {p.stderr}")
    return json.loads(p.stdout)


def bfs_dist(n, edges, source):
    adjacency = [[] for _ in range(n)]
    for a, b in edges:
        adjacency[a].append(b)
    distances = [-1] * n
    distances[source] = 0
    todo = deque([source])
    while todo:
        vertex = todo.popleft()
        for neighbor in adjacency[vertex]:
            if distances[neighbor] == -1:
                distances[neighbor] = distances[vertex] + 1
                todo.append(neighbor)
    return distances


def exact_tour(n, edges, start):
    """Independent shortest search with NO intermediate return to start."""
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
    reachable = {i for i, d in enumerate(bfs_dist(n, edges, start)) if d >= 0}
    mask_all = sum(1 << i for i in reachable)
    todo = deque([(start, 1 << start, 0)])
    visited = {(start, 1 << start)}
    while todo:
        city, mask, steps = todo.popleft()
        if city == start and mask == mask_all and steps > 0:
            return steps
        for nxt in adj[city]:
            nmask = mask | (1 << nxt)
            if nxt == start and nmask != mask_all:
                continue
            state = (nxt, nmask)
            if state not in visited:
                visited.add(state)
                todo.append((nxt, nmask, steps + 1))
    return 0 if len(reachable) == 1 else None


def meeting_oracle(n, edges):
    distances = [bfs_dist(n, edges, v) for v in range(3)]
    eligible = []
    for city in range(3, n):
        d = [distances[i][city] for i in range(3)]
        if all(x >= 0 for x in d):
            eligible.append((sum(d), city, d))
    return min(eligible, default=None)


class IndependentOracleTests(unittest.TestCase):
    def test_randomized_small_graphs(self):
        rng = random.Random(2110)
        with tempfile.TemporaryDirectory(prefix="airline-oracle-") as temp:
            folder = Path(temp)
            for case in range(72):
                n = rng.randrange(3, 8)
                names = labels(n)
                edges = set()
                # Half the cases have a directed Hamiltonian cycle. The
                # others have an A-centered bidirectional star, where a
                # no-early-return tour may be impossible.
                if case % 2:
                    edges.update((i, (i + 1) % n) for i in range(n))
                else:
                    edges.update((0, i) for i in range(1, n))
                    edges.update((i, 0) for i in range(1, n))
                for a in range(n):
                    for b in range(n):
                        if a != b and rng.random() < 0.13:
                            edges.add((a, b))
                make_data(folder, names, edges)

                q3 = query(folder, "--round-trip", names[0])
                optimum = exact_tour(n, edges, 0)
                if optimum is None:
                    self.assertEqual(q3["status"], "no_tour", case)
                    self.assertEqual(q3["route"], [], case)
                else:
                    self.assertEqual(q3["status"], "found", case)
                    self.assertEqual(q3["method"], "exact", case)
                    self.assertEqual(q3["flights"], optimum, case)
                    path = [node["id"] for node in q3["route"]]
                    self.assertEqual(path[0], 0, case)
                    self.assertEqual(path[-1], 0, case)
                    self.assertNotIn(0, path[1:-1], case)
                    self.assertTrue(
                        all((a, b) in edges for a, b in zip(path, path[1:])),
                        case,
                    )

                q4 = query(folder, "--meeting-a", names[0],
                           "--meeting-b", names[1],
                           "--meeting-c", names[2])
                optimum4 = meeting_oracle(n, edges)
                if optimum4 is None:
                    self.assertEqual(q4["status"], "unreachable", case)
                    self.assertIsNone(q4["meeting_city"])
                else:
                    total, city, distances = optimum4
                    self.assertEqual(q4["status"], "found", case)
                    self.assertEqual(q4["meeting_city"]["id"], city, case)
                    self.assertEqual(q4["total_flights"], total, case)
                    for ix, key in enumerate(("from_a", "from_b", "from_c")):
                        route = [node["id"] for node in q4["routes"][key]]
                        self.assertEqual(route[0], ix, case)
                        self.assertEqual(route[-1], city, case)
                        self.assertEqual(len(route) - 1, distances[ix], case)
                        self.assertTrue(
                            all((a, b) in edges for a, b in zip(route, route[1:])),
                            case,
                        )


if __name__ == "__main__":
    unittest.main()
