"""Dependency-free Q1/Q2 subprocess example; see docs/backend_api_contract.md.

This is transport/validation glue for Person 3, without a GUI or map dependency.
Run it from a worker when integrating into a GUI, since subprocess.run blocks.
"""
import json
from pathlib import Path
import subprocess


class BackendProtocolError(RuntimeError):
    """The process did not follow the versioned JSON/exit-code contract."""


class BackendError(RuntimeError):
    """A valid backend error response (bad input, missing/malformed dataset)."""

    def __init__(self, payload, stderr):
        super().__init__(payload['message'])
        self.payload = payload
        self.stderr = stderr


def validate_result(value, returncode):
    """Validate v1 required fields and invariants; allow future additive fields.

    Dataset membership/coordinates must be joined separately using the exact
    cities.tsv used by the process; IDs are scoped to its metadata row order.
    """
    def require(condition, message):
        if not condition:
            raise BackendProtocolError(message)

    require(type(value) is dict, 'response must be an object')
    require(type(value.get('schema_version')) is int and value['schema_version'] == 1,
            'unsupported schema_version')
    status = value.get('status')
    if status == 'error':
        require(returncode == 1 and type(value.get('message')) is str and bool(value['message']),
                'invalid error response/exit code')
        return value
    require(returncode == 0, 'unexpected process exit code')
    if status == 'help':
        require(type(value.get('usage')) is str and bool(value['usage']), 'missing help usage')
        return value
    query = value.get('query')
    require(query in ('q1', 'q2'), 'unknown query')
    require(status in (('found', 'unreachable', 'connection_limit') if query == 'q1'
                       else ('found', 'unreachable')), 'unknown status')
    for key in ('from', 'to') + (('via_b', 'via_c') if query == 'q2' else ()):
        require(type(value.get(key)) is str, f'missing string {key}')
    require(value.get('historical_observed_connectivity') is True, 'missing historical flag')

    def nodes(key):
        require(type(value.get(key)) is list, f'missing array {key}')
        for node in value[key]:
            require(type(node) is dict and type(node.get('id')) is int and node['id'] >= 0
                    and type(node.get('city')) is str and bool(node['city']), 'invalid city node')
        return value[key]

    route = nodes('route')
    for key in ('flights', 'connections'):
        require(key in value and (value[key] is None or
                (type(value[key]) is int and value[key] >= 0)), f'invalid count {key}')
    flights, connections = value['flights'], value['connections']
    if status == 'unreachable':
        require(flights is None and connections is None and route == [], 'invalid unreachable result')
    else:
        require(flights is not None and connections == max(flights - 1, 0), 'invalid flight counts')
        if status == 'found':
            require(len(route) == flights + 1 and route[0]['city'] == value['from'] and
                    route[-1]['city'] == value['to'], 'invalid route endpoints/length')
        else:
            require(route == [], 'over-limit route must be empty')
    if query == 'q1':
        limit = value.get('exclusive_connection_limit')
        require(type(limit) is int and 0 <= limit <= 9223372036854775807, 'invalid Q1 limit')
        if status != 'unreachable':
            require((connections < limit) == (status == 'found'), 'incorrect strict Q1 limit')
    else:
        order = nodes('waypoint_order')
        expected = []
        seen = set()
        for node in route:
            if node['city'] in (value['via_b'], value['via_c']) and node['city'] not in seen:
                expected.append(node)
                seen.add(node['city'])
        require(order == expected, 'incorrect waypoint first-encounter order')
        if status == 'found':
            require(seen == {value['via_b'], value['via_c']}, 'required city missing')
    return value


def query_backend(executable, data_dir, *, from_city, to_city,
                  exclusive_connection_limit=None, via_b=None, via_c=None, timeout=30):
    """Return a validated v1 dict for Q1/Q2, including valid no-result statuses.

    BackendError carries a valid error payload; BackendProtocolError reports a
    transport/contract failure. FileNotFoundError, UnicodeError and subprocess
    TimeoutExpired propagate. Never assemble shell command strings from labels.
    """
    args = [str(Path(executable).resolve()), '--data-dir', str(Path(data_dir).resolve()),
            '--from', from_city, '--to', to_city]
    if exclusive_connection_limit is not None:
        if type(exclusive_connection_limit) is not int or not 0 <= exclusive_connection_limit <= 9223372036854775807:
            raise ValueError('exclusive_connection_limit must be an int in [0, 9223372036854775807]')
        if via_b is not None or via_c is not None:
            raise ValueError('select either Q1 or Q2')
        args += ['--max-connections', str(exclusive_connection_limit)]
    else:
        if via_b is None or via_c is None:
            raise ValueError('Q2 requires via_b and via_c')
        args += ['--via-b', via_b, '--via-c', via_c]
    result = subprocess.run(args + ['--json'], shell=False, capture_output=True,
                            text=True, encoding='utf-8', errors='strict', timeout=timeout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BackendProtocolError('stdout must contain exactly one JSON object') from exc
    validate_result(payload, result.returncode)
    if payload['status'] == 'error':
        raise BackendError(payload, result.stderr)
    if result.stderr:
        raise BackendProtocolError('successful query emitted unexpected diagnostics')
    expected_query = 'q1' if exclusive_connection_limit is not None else 'q2'
    expected_fields = {'query': expected_query, 'from': from_city, 'to': to_city}
    if expected_query == 'q1':
        expected_fields['exclusive_connection_limit'] = exclusive_connection_limit
    else:
        expected_fields.update(via_b=via_b, via_c=via_c)
    if any(payload.get(key) != expected for key, expected in expected_fields.items()):
        raise BackendProtocolError('response does not match the requested query')
    return payload
