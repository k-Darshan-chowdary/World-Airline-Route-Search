"""Q2 subprocess contract and an independent visited-mask BFS oracle."""
from collections import deque
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()
GLOBAL = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None
LABELS = ['Alpha "quoted"\\hub, Test', 'München, Germany', '東京, Japan',
          'Delta, Test', 'Extra, Test', 'Island, Test', 'Other, Test']
A, B, C, D, E, F, G = LABELS


def shortest_walk(neighbors, a, b, c, d):
    def mask(u):
        return (1 if u == b else 0) | (2 if u == c else 0)
    queue = deque([(a, mask(a), 0)])
    seen = {(a, mask(a))}
    while queue:
        u, visited, flights = queue.popleft()
        if u == d and visited == 3:
            return flights
        for v in neighbors[u]:
            state = (v, visited | mask(v))
            if state not in seen:
                seen.add(state)
                queue.append((*state, flights + 1))
    return None


def read_data(folder):
    cities = [line.split('\t')[0] for line in (folder/'cities.tsv').read_text(encoding='utf-8-sig').splitlines()[1:]]
    edges = {tuple(line.split('\t')) for line in (folder/'flight.txt').read_text(encoding='utf-8-sig').splitlines()
             if line.strip() and not line.lstrip().startswith('#')}
    neighbors = {city: [] for city in cities}
    for u, v in edges:
        neighbors[u].append(v)
    return cities, edges, neighbors


class Q2CLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='airline-q2-')
        cls.root = Path(cls.tmp.name) / '東京 datasets'
        cls.root.mkdir()
        cls.counter = 0
        cls.data = cls.fixture([(0,1),(1,4),(4,2),(2,3),(0,2),(2,1),(1,3)])

    @classmethod
    def fixture(cls, edges):
        cls.counter += 1
        folder = cls.root / str(cls.counter)
        folder.mkdir()
        # Every metadata city occurs in an edge; separate component for no-path tests.
        edges = sorted(set(edges) | {(4,3),(5,6)})
        (folder/'cities.tsv').write_text('city\tlatitude\tlongitude\n' + ''.join(
            f'{city}\t0\t0\n' for city in LABELS), encoding='utf-8')
        (folder/'flight.txt').write_text(''.join(f'{LABELS[u]}\t{LABELS[v]}\n' for u,v in edges), encoding='utf-8')
        return folder

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cli(self, *args, data=None):
        return subprocess.run([str(CLI), '--data-dir', str(data or self.data), *args],
                              text=True, encoding='utf-8', capture_output=True, timeout=30)

    def query(self, a=A, b=B, c=C, d=D, data=None, json_output=True):
        args = ['--from', a, '--via-b', b, '--via-c', c, '--to', d]
        if json_output:
            args.append('--json')
        return self.run_cli(*args, data=data)

    def payload(self, result, code=0):
        self.assertEqual(result.returncode, code, result.stderr)
        r = json.loads(result.stdout)
        self.assertEqual(r['schema_version'], 1)
        if code:
            self.assertEqual(r['status'], 'error')
            self.assertTrue(r['message'])
            self.assertIn('ERROR:', result.stderr)
        else:
            self.assertEqual(result.stderr, '')
        return r

    def verify(self, a=A, b=B, c=C, d=D, data=None):
        folder = data or self.data
        cities, edges, neighbors = read_data(folder)
        expected = shortest_walk(neighbors,a,b,c,d)
        r = self.payload(self.query(a,b,c,d,data=folder))
        self.assertEqual((r['query'],r['from'],r['via_b'],r['via_c'],r['to']), ('q2',a,b,c,d))
        self.assertIs(r['historical_observed_connectivity'], True)
        self.assertNotIn('exclusive_connection_limit', r)
        if expected is None:
            self.assertEqual(r['status'], 'unreachable')
            self.assertEqual((r['route'],r['waypoint_order']), ([],[]))
            self.assertIsNone(r['flights'])
            self.assertIsNone(r['connections'])
        else:
            self.assertEqual(r['status'], 'found')
            self.assertEqual((r['flights'],r['connections']), (expected,max(expected-1,0)))
            path = [node['city'] for node in r['route']]
            self.assertEqual((path[0],path[-1],len(path)), (a,d,expected+1))
            self.assertTrue(all((u,v) in edges for u,v in zip(path,path[1:])))
            self.assertTrue(b in path and c in path)
            for node in r['route'] + r['waypoint_order']:
                self.assertEqual(cities[node['id']], node['city'])
            order = list(dict.fromkeys(u for u in path if u in {b,c}))
            self.assertEqual([node['city'] for node in r['waypoint_order']], order)
        return r

    def test_both_permutations_and_shortest(self):
        self.assertEqual([n['city'] for n in self.verify()['route']], [A,C,B,D])
        self.assertEqual([n['city'] for n in self.verify(b=C,c=B)['route']], [A,C,B,D])

    def test_tie_is_deterministic(self):
        data = self.fixture([(0,2),(0,1),(1,2),(2,1),(1,3),(2,3)])
        for _ in range(3):
            self.assertEqual([n['city'] for n in self.verify(data=data)['route']], [A,B,C,D])
        data = self.fixture([(0,4),(0,1),(4,2),(1,2),(2,3)])
        self.assertEqual([n['city'] for n in self.verify(b=C,c=D,data=data)['route']], [A,B,C,D])

    def test_incidental_visit_and_required_revisit(self):
        data = self.fixture([(0,2),(2,1),(1,2),(2,3)])
        r = self.verify(data=data)
        self.assertEqual([n['city'] for n in r['route']], [A,C,B,C,D])
        self.assertEqual([n['city'] for n in r['waypoint_order']], [C,B])
        self.verify(a=C,b=B,c=C,d=C,data=data)

    def test_aliases(self):
        for args in [(A,A,C,D),(A,B,B,D),(A,B,D,D),(A,A,A,A),
                     (A,B,C,A),(A,D,C,D),(B,B,B,B),(C,B,C,C)]:
            with self.subTest(args=args):
                self.verify(*args)

    def test_unreachable_and_directed_asymmetry(self):
        for args in [(D,B,C,A),(A,F,C,D),(A,B,F,D),(A,B,C,F)]:
            self.verify(*args)

    def test_invalid_labels_all_positions(self):
        for position in range(4):
            for missing in ['', 'Missing, Test', B.lower(), B+' ', 'Munchen, Germany']:
                args = [A,B,C,D]
                args[position] = missing
                self.assertIn('city not found', self.payload(self.query(*args),1)['message'])

    def test_malformed_options_and_loading_errors(self):
        base = ['--from',A,'--to',D,'--via-b',B,'--via-c',C]
        for args in [base+['--max-connections','2'], base+['--unknown','value'],
                     base+['--via-c'], base+['--expect-cities','1'],
                     ['--via-b',B], ['--via-c',C], ['--via-b',B,'--via-c',C],
                     ['--from',A,'--via-b',B,'--via-c',C],
                     ['--to',D,'--via-b',B,'--via-c',C],
                     ['--from',A,'--to',D,'--via-b','--via-c',C]]:
            with self.subTest(args=args):
                self.payload(self.run_cli(*args,'--json'),1)
        self.payload(self.query(data=self.root/'missing'),1)

    def test_human_output_and_help(self):
        r = self.query(json_output=False)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('3 flights; 2 connections',r.stdout)
        self.assertIn('Historical observed connectivity; not current/bookable flights.',r.stdout)
        r = self.query(d=F,json_output=False)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('No directed route through both required cities exists.',r.stdout)
        r = self.run_cli('--help','--json',data=self.root/'missing')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('--via-b',r.stdout)

    def test_preserved_sample(self):
        self.verify('Dallas, United States','London, United Kingdom','Tokyo, Japan','Auckland, New Zealand',data=SAMPLE)
        self.verify('Auckland, New Zealand','London, United Kingdom','Tokyo, Japan','Dallas, United States',data=SAMPLE)

    def verify_official_dataset(self):
        cities, edges, _ = read_data(GLOBAL)
        self.assertEqual((len(cities),len(edges)), (819,19283))
        # Fixed real labels plus spread-out tuples, checked independently at runtime.
        known = self.verify('London, United Kingdom','Paris, France','Dubai, United Arab Emirates','Tokyo, Japan',data=GLOBAL)
        self.assertEqual((known['status'],known['flights'],known['connections']), ('found',3,2))
        for offset in [0,37,181,409,818]:
            self.verify(*(cities[(offset+k)%819] for k in [0,1,17,89]),data=GLOBAL)
        self.verify(*(cities[0] for _ in range(4)),data=GLOBAL)


if GLOBAL is not None:
    Q2CLI.test_official_dataset = Q2CLI.verify_official_dataset

if __name__ == '__main__':
    unittest.main(verbosity=2)
