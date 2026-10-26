"""Run every test offline; fail for skipped tests, missing PyArrow or failures."""
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    try:
        import pyarrow
        if pyarrow.__version__ != "23.0.1":
            raise ValueError("PyArrow must match requirements-import.lock (23.0.1)")
    except (ImportError, ValueError) as exc:
        print(f"FAIL: {exc}; install requirements-import.lock", file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    if suite.countTestCases() < 36:
        print("FAIL: expected at least the 36 existing tests", file=sys.stderr)
        return 1
    blocked = AssertionError("Network is disabled during dataset tests; use local fixtures/mocks")
    with patch.object(socket.socket, "connect", side_effect=blocked), \
         patch.object(socket.socket, "connect_ex", side_effect=blocked), \
         patch.object(urllib.request, "urlopen", side_effect=blocked):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"Tests: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}; skipped: {len(result.skipped)}", flush=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
