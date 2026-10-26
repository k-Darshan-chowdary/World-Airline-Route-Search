"""Cross-language v1 integration, metadata joins and subprocess adapter tests.

No network/dependencies. Optional official data must pass CTest's checksum fixture.
"""
from collections import deque
import copy
import csv
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(sys.argv.pop(1)).resolve()
SAMPLE = Path(sys.argv.pop(1)).resolve()
GLOBAL = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('backend_client', ROOT/'examples/backend_client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
COMMON = {'schema_version', 'query', 'status', 'from', 'to', 'flights', 'connections',
          'historical_observed_connectivity', 'route'}
Q1_KEYS = COMMON | {'exclusive_connection_limit'}
Q2_KEYS = COMMON | {'via_b', 'via_c', 'waypoint_order'}
LABELS = ['Alpha "quoted"\\hub, Test', 'München, Germany', '東京, Japan',
          'Delta, Test', 'Island, Test', 'Tail, Test', '😀, Test']
A, B, C, D, E, F, G = LABELS


def metadata(folder):
    with (folder/'cities.tsv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    edges = {tuple(line.split('\t')) for line in (folder/'flight.txt').read_text(
        encoding='utf-8-sig').splitlines() if line.strip() and not line.lstrip().startswith('#')}
    return rows, edges


def oracle(edges, start, finish, required=()):
    """Independent BFS over (city, visited-required-set), not segment concatenation."""
    needed = frozenset(required)
    adjacency = {}
    for a, b in edges:
        adjacency.setdefault(a, []).append(b)
    queue = deque([(start, needed & {start}, 0)])
    seen = {(start, needed & {start})}
    while queue:
        here, visited, distance = queue.popleft()
        if here == finish and visited == needed:
            return distance
        for there in adjacency.get(here, ()):
            state = (there, visited | (needed & {there}))
            if state not in seen:
                seen.add(state)
                queue.append((*state, distance + 1))
    return None


class BackendContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='airline-contract-')
        cls.data = Path(cls.tmp.name)/'東京 data with spaces'
        cls.data.mkdir()
        cls.city_text = 'city\tlatitude\tlongitude\n' + ''.join(
            f'{label}\t{index}.25\t-{index}.5\n' for index, label in enumerate(LABELS))
        cls.route_text = '\n# directed fixture\n \t\n' + ''.join(
            f'{LABELS[a]}\t{LABELS[b]}\n' for a, b in
            [(0, 2), (0, 1), (1, 2), (2, 1), (1, 3), (2, 3), (4, 5), (5, 6)])
        (cls.data/'cities.tsv').write_text(cls.city_text, encoding='utf-8')
        (cls.data/'flight.txt').write_text(cls.route_text, encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def raw(self, *args, folder=None):
        return subprocess.run([str(CLI), '--data-dir', str(folder or self.data), *args],
                              capture_output=True, timeout=30)

    def payload(self, process, code=0):
        self.assertEqual(process.returncode, code, process.stderr.decode('utf-8'))
        stdout = process.stdout.decode('utf-8', errors='strict')
        value = json.loads(stdout)  # rejects banners, trailing objects and text
        self.assertEqual(type(value), dict)
        self.assertEqual(len(stdout.splitlines()), 1)
        self.assertEqual(client.validate_result(value, code), value)
        if code:
            self.assertEqual(set(value), {'schema_version', 'status', 'message'})
            self.assertTrue(process.stderr.decode('utf-8').startswith('ERROR: '))
        else:
            self.assertEqual(process.stderr, b'')
        if value['status'] not in ('error', 'help'):
            self.assertEqual(set(value), Q1_KEYS if value['query'] == 'q1' else Q2_KEYS)
            for node in value['route'] + value.get('waypoint_order', []):
                self.assertEqual(set(node), {'id', 'city'})
        return value

    def q1(self, a=A, d=D, limit='2', folder=None):
        return self.payload(self.raw('--from', a, '--to', d, '--max-connections', str(limit),
                                     '--json', folder=folder))

    def q2(self, a=A, b=B, c=C, d=D, folder=None):
        return self.payload(self.raw('--from', a, '--via-b', b, '--via-c', c, '--to', d,
                                     '--json', folder=folder))

    def verify_join_and_shortest(self, value, folder):
        rows, edges = metadata(folder)
        required = (value['via_b'], value['via_c']) if value['query'] == 'q2' else ()
        expected = oracle(edges, value['from'], value['to'], required)
        self.assertEqual(value['flights'], expected)
        path = value['route']
        for node in path + value.get('waypoint_order', []):
            row = rows[node['id']]
            self.assertEqual(row['city'], node['city'])
            lat, lon = float(row['latitude']), float(row['longitude'])
            self.assertTrue(math.isfinite(lat) and -90 <= lat <= 90)
            self.assertTrue(math.isfinite(lon) and -180 <= lon <= 180)
        self.assertTrue(all((u['city'], v['city']) in edges for u, v in zip(path, path[1:])))

    def test_q1_all_statuses_and_strict_boundaries(self):
        for a, d, limit, status, flights in [(A,D,2,'found',2), (A,D,1,'connection_limit',2),
                (A,B,0,'connection_limit',1), (A,B,1,'found',1), (D,A,20,'unreachable',None),
                (A,E,0,'unreachable',None), (A,A,0,'connection_limit',0), (A,A,1,'found',0)]:
            with self.subTest(a=a, d=d, limit=limit):
                value = self.q1(a,d,limit)
                self.assertEqual((value['status'],value['flights']), (status,flights))
                self.verify_join_and_shortest(value,self.data)

    def test_q2_waypoints_aliases_cycles_and_no_path(self):
        for args in [(A,B,C,D), (A,C,B,D), (A,A,C,D), (A,B,B,D), (A,B,D,D),
                     (A,A,A,A), (B,C,B,B), (D,B,C,A), (A,E,C,D), (E,F,G,G)]:
            with self.subTest(args=args):
                value = self.q2(*args)
                self.verify_join_and_shortest(value,self.data)
        self.assertEqual([n['city'] for n in self.q2()['route']], [A,B,C,D])
        self.assertEqual(self.q2(D,B,C,A)['status'], 'unreachable')

    def test_deterministic_byte_output_and_unicode_escaping(self):
        args = ['--from',A,'--to',D,'--via-b',B,'--via-c',C,'--json']
        outputs = [self.raw(*args).stdout for _ in range(4)]
        self.assertTrue(all(output == outputs[0] for output in outputs))
        self.assertIn(b'\\"quoted\\"\\\\hub', outputs[0])
        self.assertIn('München'.encode(), outputs[0])
        self.assertIn('東京'.encode(), outputs[0])
        self.assertEqual(self.q1(E,G,2)['route'][-1]['city'], G)

    def test_error_contract_for_labels_and_limits(self):
        for label in ['', 'Missing, Test', B.lower(), 'Munchen, Germany', B+' ', B+'\n']:
            for flags in [('--max-connections','2'), ('--via-b',label,'--via-c',C)]:
                self.payload(self.raw('--from',label,'--to',D,*flags,'--json'),1)
        for limit in ['', '-1', '+1', '1.0', '1e2', ' 2', '2 ', '9223372036854775808']:
            self.payload(self.raw('--from',A,'--to',D,'--max-connections',limit,'--json'),1)
        self.assertEqual(self.q1(limit='0002')['exclusive_connection_limit'],2)
        self.assertEqual(self.q1(limit='9223372036854775807')['status'],'found')

    def test_error_contract_for_options_and_data(self):
        for args in [[], ['--from',A], ['--from',A,'--to',D], ['--via-b',B],
                ['--from',A,'--to',D,'--via-b',B,'--via-c',C,'--max-connections','2'],
                ['--unknown','value'], ['--from',A,'--to',D,'--max-connections']]:
            self.payload(self.raw(*args,'--json'),1)
        missing = self.data/'不存在'
        value = self.payload(self.raw('--from',A,'--to',D,'--max-connections','2',
                                      '--json',folder=missing),1)
        self.assertIn('不存在',value['message'])
        self.payload(self.raw('--from',A,'--to',D,'--max-connections','2','--json',
                              '--expect-cities','1'),1)

    def test_json_help_and_legacy_help(self):
        for args in [('--help','--json'), ('--json','--help')]:
            value = self.payload(self.raw(*args,folder=self.data/'missing'))
            self.assertEqual(set(value),{'schema_version','status','usage'})
            self.assertEqual(value['status'],'help')
            self.assertIn('--via-b',value['usage'])
        legacy = self.raw('--help')
        self.assertEqual((legacy.returncode,legacy.stderr),(0,b''))
        self.assertTrue(legacy.stdout.startswith(b'Usage:'))

    def test_error_escaping_and_repeated_option_compatibility(self):
        flag = '--bad"\n\\東京'
        value = self.payload(self.raw(flag,'value','--json'),1)
        self.assertEqual(value['message'],'unknown argument '+flag)
        value = self.payload(self.raw('--from',A,'--to',D,'--to',B,
            '--max-connections','0','--max-connections','1','--json','--json'))
        self.assertEqual((value['to'],value['status'],value['exclusive_connection_limit']),
                         (B,'found',1))

    def test_malformed_tables_and_duplicate_labels(self):
        cases = [('\n'+self.city_text,self.route_text),
                 (self.city_text+'\n',self.route_text),
                 (self.city_text+f'{A}\t0\t0\n',self.route_text),
                 (self.city_text,self.route_text+f'{A}\t{B}\n'),
                 (self.city_text,self.route_text+f'{A}\t{A}\n'),
                 (self.city_text,self.route_text+f'{A}\tMissing, Test\n'),
                 (self.city_text.replace('0.25','91',1),self.route_text),
                 (self.city_text.encode()+b'\xff',self.route_text)]
        for index,(cities,routes) in enumerate(cases):
            with self.subTest(index=index):
                folder = self.data/f'bad {index}'
                folder.mkdir()
                (folder/'cities.tsv').write_bytes(cities if isinstance(cities,bytes) else cities.encode())
                (folder/'flight.txt').write_text(routes,encoding='utf-8')
                self.payload(self.raw('--from',A,'--to',D,'--max-connections','2',
                                      '--json',folder=folder),1)

    def test_blank_routes_bom_crlf_and_reordered_edges(self):
        folder = self.data/'BOM CRLF'
        folder.mkdir()
        (folder/'cities.tsv').write_bytes(b'\xef\xbb\xbf'+self.city_text.replace('\n','\r\n').encode())
        routes = '\n'.join(reversed(self.route_text.splitlines()))+'\n'
        (folder/'flight.txt').write_bytes(b'\xef\xbb\xbf'+routes.replace('\n','\r\n').encode())
        self.assertEqual(self.q1(folder=folder),self.q1())
        self.assertEqual(self.q2(folder=folder),self.q2())

    def test_preserved_sample_results_and_metadata(self):
        a,d = 'Dallas, United States','Auckland, New Zealand'
        q1 = self.q1(a,d,9,folder=SAMPLE)
        self.assertEqual((q1['status'],q1['flights'],q1['connections']),('found',9,8))
        self.verify_join_and_shortest(q1,SAMPLE)
        q2 = self.q2(a,'London, United Kingdom','Tokyo, Japan',d,folder=SAMPLE)
        self.assertEqual((q2['status'],q2['flights'],q2['connections']),('found',10,9))
        self.verify_join_and_shortest(q2,SAMPLE)
        rows,_ = metadata(SAMPLE)
        self.assertEqual((rows[0]['city'],float(rows[0]['latitude']),float(rows[0]['longitude'])),
                         (a,32.7767,-96.7970))

    def test_documented_json_examples_match_executable(self):
        contract = (ROOT/'docs/backend_api_contract.md').read_text(encoding='utf-8')
        examples = re.findall(r'```json\n(.*?)\n```',contract,re.DOTALL)
        self.assertEqual(len(examples),6)
        for example in examples:
            expected = json.loads(example)
            with self.subTest(status=expected['status'],query=expected.get('query')):
                if expected['status'] == 'error':
                    actual = self.payload(self.raw('--from','Missing, Test','--to',D,
                        '--max-connections','1','--json'),1)
                elif expected['query'] == 'q1':
                    actual = self.q1(expected['from'],expected['to'],
                        expected['exclusive_connection_limit'],folder=SAMPLE)
                else:
                    actual = self.q2(expected['from'],expected['via_b'],expected['via_c'],
                        expected['to'],folder=SAMPLE)
                self.assertEqual(actual,expected)

    def test_adapter_round_trip_and_backend_error(self):
        self.assertEqual(client.query_backend(CLI,self.data,from_city=A,to_city=D,
                         exclusive_connection_limit=2),self.q1())
        self.assertEqual(client.query_backend(CLI,self.data,from_city=A,to_city=D,
                         via_b=B,via_c=C),self.q2())
        for limit in [0,1]:
            self.assertEqual(client.query_backend(CLI,self.data,from_city=A,to_city=D,
                             exclusive_connection_limit=limit)['status'],'connection_limit')
        self.assertEqual(client.query_backend(CLI,self.data,from_city=D,to_city=A,
                         via_b=B,via_c=C)['status'],'unreachable')
        with self.assertRaises(client.BackendError) as caught:
            client.query_backend(CLI,self.data,from_city='Missing, Test',to_city=D,
                                 exclusive_connection_limit=2)
        self.assertEqual(caught.exception.payload['status'],'error')
        self.assertIn('ERROR:',caught.exception.stderr)

    def test_consumer_rejects_incompatible_payloads(self):
        good = self.q1()
        mutations = [('schema_version',2),('schema_version',True),('route',[{'id':True,'city':A}]),
                     ('flights','2'),('connections',True),('connections',0),('status','booked'),
                     ('historical_observed_connectivity',False),('exclusive_connection_limit',1)]
        for key,value in mutations:
            bad = copy.deepcopy(good)
            bad[key] = value
            with self.subTest(key=key,value=value),self.assertRaises(client.BackendProtocolError):
                client.validate_result(bad,0)
        for value,code in [(good,1),([],0),({'schema_version':1,'status':'error','message':'bad'},0)]:
            with self.assertRaises(client.BackendProtocolError):
                client.validate_result(value,code)
        bad = self.q2()
        bad['waypoint_order'].reverse()
        with self.assertRaises(client.BackendProtocolError):
            client.validate_result(bad,0)

    def verify_official_dataset(self):
        rows,edges = metadata(GLOBAL)
        self.assertEqual((len(rows),len(edges)),(819,19283))
        with (GLOBAL/'city_representatives.tsv').open(encoding='utf-8',newline='') as stream:
            representatives = {row['city']:row['representative_airport_ident']
                               for row in csv.DictReader(stream,delimiter='\t')}
        with (GLOBAL/'airports.tsv').open(encoding='utf-8',newline='') as stream:
            airports = {row['ident']:row for row in csv.DictReader(stream,delimiter='\t')}
        for row in rows:
            airport = airports[representatives[row['city']]]
            for key in ('latitude','longitude'):
                self.assertAlmostEqual(float(row[key]),float(airport[key]),delta=0.00000051)
        self.assertEqual((rows[0]['city'],rows[0]['latitude'],rows[0]['longitude']),
                         ('Aalborg, Denmark','57.094763','9.849930'))
        self.assertEqual(representatives['Aalborg, Denmark'],'EKYT')
        self.verify_join_and_shortest(self.q1('São Paulo, Brazil','São Paulo, Brazil',
                                             1,folder=GLOBAL),GLOBAL)
        self.verify_join_and_shortest(self.q1('London, United Kingdom','Tokyo, Japan',
                                             819,folder=GLOBAL),GLOBAL)
        self.verify_join_and_shortest(self.q2('London, United Kingdom','Paris, France',
            'Dubai, United Arab Emirates','Tokyo, Japan',folder=GLOBAL),GLOBAL)
        for index in [0,37,181,409,818]:
            label = rows[index]['city']
            for value in [self.q1(label,label,1,folder=GLOBAL),
                          self.q2(label,label,label,label,folder=GLOBAL)]:
                self.assertEqual(value['route'],[{'id':index,'city':label}])
                self.verify_join_and_shortest(value,GLOBAL)


if GLOBAL is not None:
    BackendContract.test_official_dataset = BackendContract.verify_official_dataset

if os.name != 'nt':
    def invalid_posix_arguments(self):
        for raw in [b'\xff',b'\xc0\xaf',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xe2\x82']:
            result = subprocess.run([os.fsencode(CLI),b'--unknown',raw,b'--json'],
                                    capture_output=True,timeout=30)
            value = self.payload(result,1)
            self.assertEqual(value['message'],'invalid UTF-8 argument')
    BackendContract.test_invalid_posix_utf8_arguments = invalid_posix_arguments
else:
    def invalid_windows_arguments(self):
        for raw in ['\ud800','\udfff','\ud800x','\udfff\ud800']:
            result = subprocess.run([str(CLI),'--unknown',raw,'--json'],
                                    capture_output=True,timeout=30)
            value = self.payload(result,1)
            self.assertEqual(value['message'],'invalid Unicode argument')
    BackendContract.test_invalid_windows_utf16_arguments = invalid_windows_arguments

if __name__ == '__main__':
    unittest.main(verbosity=2)
