"""Q1 CLI contract; optional official data is checksum-verified by CTest first."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()
GLOBAL = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None
A = 'Alpha "quoted"\\hub, Test'
B = 'München, Germany'
C = '東京, Japan'
D = 'Delta, Test'
E = 'Tail, Test'
F = 'Island, Test'
G = 'Other, Test'
LABELS = [A, B, C, D, E, F, G]


class Q1CLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='airline-q1-')
        cls.data = Path(cls.tmp.name) / '東京 dataset'
        cls.data.mkdir()
        (cls.data / 'cities.tsv').write_text('city\tlatitude\tlongitude\n' + ''.join(
            f'{city}\t0\t0\n' for city in LABELS), encoding='utf-8')
        (cls.data / 'flight.txt').write_text(''.join(
            f'{LABELS[a]}\t{LABELS[b]}\n' for a, b in
            [(0, 2), (0, 1), (2, 3), (1, 3), (2, 4), (4, 3), (5, 6)]), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cli(self, *args, data=None):
        return subprocess.run([str(CLI), '--data-dir', str(data or self.data), *args],
                              text=True, encoding='utf-8', capture_output=True, timeout=30)

    def query(self, a=A, b=D, limit='2', data=None, json_output=True):
        args = ['--from', a, '--to', b, '--max-connections', str(limit)]
        if json_output:
            args.append('--json')
        return self.run_cli(*args, data=data)

    def payload(self, result, code=0):
        self.assertEqual(result.returncode, code, result.stderr)
        value = json.loads(result.stdout)  # Rejects any banner or extra JSON text.
        self.assertEqual(value['schema_version'], 1)
        if code == 0:
            self.assertEqual(result.stderr, '')
        else:
            self.assertEqual(value['status'], 'error')
            self.assertTrue(value['message'])
            self.assertIn('ERROR:', result.stderr)
        return value

    def test_strict_boundaries_and_same_city(self):
        for a, b, flights in [(A, B, 1), (A, D, 2), (A, A, 0), (F, F, 0)]:
            connections = max(flights-1, 0)
            for x in range(connections+2):
                with self.subTest(a=a, b=b, x=x):
                    r = self.payload(self.query(a, b, x))
                    self.assertEqual((r['flights'], r['connections']), (flights, connections))
                    self.assertEqual(r['exclusive_connection_limit'], x)
                    self.assertEqual(r['status'], 'found' if connections < x else 'connection_limit')
                    self.assertEqual(bool(r['route']), connections < x)
                    if r['route']:
                        self.assertEqual((r['route'][0]['city'], r['route'][-1]['city']), (a, b))

    def test_shortest_and_deterministic_unicode_json_escaping(self):
        for _ in range(3):
            for x in ['2', '0002', '100', '9223372036854775807']:
                r = self.payload(self.query(limit=x))
                self.assertEqual(r['status'], 'found')
                self.assertEqual(r['route'], [{'id': 0, 'city': A}, {'id': 1, 'city': B}, {'id': 3, 'city': D}])
                self.assertEqual(r['from'], A)
                self.assertEqual(r['query'], 'q1')
                self.assertIs(r['historical_observed_connectivity'], True)
        r = self.payload(self.query(A, C, 1))
        self.assertEqual(r['route'][-1]['city'], C)

    def test_unreachable_direction_and_null_counts(self):
        for a, b in [(D, A), (A, F)]:
            for x in ['0', '1', '9223372036854775807']:
                r = self.payload(self.query(a, b, x))
                self.assertEqual(r['status'], 'unreachable')
                self.assertEqual(r['route'], [])
                self.assertIsNone(r['flights'])
                self.assertIsNone(r['connections'])

    def test_invalid_bounds(self):
        for x in ['-1', '-0', '+1', '1.0', '1e2', ' 1', '1 ', '1x', '', '9223372036854775808', '9'*100]:
            with self.subTest(x=x):
                r = self.payload(self.query(limit=x), 1)
                self.assertIn('invalid nonnegative count', r['message'])

    def test_invalid_city_exact_lookup(self):
        for missing in ['', 'Missing, Test', A.lower(), A+' ', 'Munchen, Germany']:
            for a, b in [(missing, B), (A, missing)]:
                r = self.payload(self.query(a, b, 0), 1)
                self.assertIn('city not found', r['message'])

    def test_missing_options_and_json_errors(self):
        for args in [('--json',), ('--max-connections', '1', '--json'),
                     ('--from', A, '--max-connections', '1', '--json'),
                     ('--from', A, '--to', B, '--json'),
                     ('--from', A, '--to', B, '--json', '--max-connections'),
                     ('--unknown', 'value', '--json')]:
            with self.subTest(args=args):
                self.payload(self.run_cli(*args), 1)
        self.payload(self.query(data=self.data / 'missing'), 1)
        self.payload(self.run_cli('--json', '--from', A, '--to', B, '--max-connections', '1', '--expect-cities', '1'), 1)

    def test_human_messages(self):
        for a, b, x, expected in [(A, B, 1, '1 flights; 0 connections'),
                                   (A, D, 1, 'No qualifying route: shortest route has 1 connections'),
                                   (D, A, 10, 'No qualifying route: no directed route exists')]:
            r = self.query(a, b, x, json_output=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(expected, r.stdout)
            self.assertIn('Historical observed connectivity', r.stdout)
        self.assertIn('connections < X', self.run_cli('--help').stdout)

    def test_preserved_sample_q1(self):
        for x, status in [(0, 'connection_limit'), (8, 'connection_limit'), (9, 'found')]:
            r = self.payload(self.query('Dallas, United States', 'Auckland, New Zealand', x, data=SAMPLE))
            self.assertEqual(r['status'], status)
            self.assertEqual((r['flights'], r['connections']), (9, 8))
        r = self.payload(self.query('Auckland, New Zealand', 'Dallas, United States', 100, data=SAMPLE))
        self.assertEqual(r['status'], 'unreachable')

    def verify_official_dataset(self):
        cities = [line.split('\t')[0] for line in (GLOBAL/'cities.tsv').read_text(encoding='utf-8-sig').splitlines()[1:]]
        edges = [tuple(line.split('\t')) for line in (GLOBAL/'flight.txt').read_text(encoding='utf-8-sig').splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        self.assertEqual((len(cities), len(edges)), (819, 19283))
        edge_set = set(edges)
        # Independent Python BFS chooses a multi-flight pair and an unreachable pair.
        from collections import deque
        neighbors = {city: [] for city in cities}
        for a, b in edges:
            neighbors[a].append(b)
        multi = unreachable = None
        for a in cities:
            distances = {a: 0}
            queue = deque([a])
            while queue:
                u = queue.popleft()
                for b in neighbors[u]:
                    if b not in distances:
                        distances[b] = distances[u] + 1
                        queue.append(b)
            if multi is None:
                multi = next(((a, b, d) for b, d in distances.items() if d >= 2), None)
            if unreachable is None:
                unreachable = next(((a, b) for b in cities if b not in distances), None)
            if multi and unreachable:
                break
        self.assertIsNotNone(multi)
        self.assertIsNotNone(unreachable)
        a, b, flights = multi
        for x, status in [(flights-1, 'connection_limit'), (flights, 'found')]:
            r = self.payload(self.query(a, b, x, data=GLOBAL))
            self.assertEqual(r['status'], status)
            self.assertEqual((r['flights'], r['connections']), (flights, flights-1))
            if status == 'found':
                self.assertEqual(len(r['route']), flights+1)
                self.assertTrue(all((u['city'], v['city']) in edge_set for u, v in zip(r['route'], r['route'][1:])))
        self.assertEqual(self.payload(self.query(*unreachable, limit=100, data=GLOBAL))['status'], 'unreachable')
        a, b = edges[0]
        self.assertEqual(self.payload(self.query(a, b, 1, data=GLOBAL))['connections'], 0)
        self.assertEqual(self.payload(self.query(a, a, 1, data=GLOBAL))['flights'], 0)


if GLOBAL is not None:
    Q1CLI.test_official_dataset = Q1CLI.verify_official_dataset


if __name__ == '__main__':
    unittest.main(verbosity=2)
