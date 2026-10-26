"""One-command teammate environment, tests, pinned downloads/import and verification."""
import argparse
from pathlib import Path
import subprocess
import sys
import venv

from dataset_lock import check_pins, verify_inputs, verify_outputs, RAW, OUTPUT, SOURCES, ROOT
from download_phase3 import download
from import_global import run


def call(command):
    subprocess.run([str(item) for item in command], cwd=ROOT, check=True)


def prepare_environment():
    if sys.version_info[:2] != (3, 13):
        raise ValueError("Use CPython 3.13: on Windows run py -3.13 scripts/setup_dataset.py")
    folder = ROOT / ".venv"
    python = folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not folder.exists():
        venv.EnvBuilder(with_pip=True).create(folder)
    elif not python.is_file():
        raise ValueError("Existing .venv is incomplete; preserve it and choose a clean checkout")
    probe = subprocess.run([str(python), "-c", "import sys; print(sys.version_info[:2] == (3, 13))"], check=True, capture_output=True, text=True)
    if probe.stdout.strip() != "True":
        raise ValueError("Existing .venv must use Python 3.13; use a clean checkout")
    call([python, "-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", ROOT / "requirements-import.lock"])
    return python


def provision(raw_dir=RAW, output_dir=OUTPUT, offline=False):
    manifest, _ = check_pins()
    # Validate existing output before downloading anything or importing. Never
    # overwrite a teammate's different/partial output or bless it with new hashes.
    if output_dir.exists():
        counts = verify_outputs(output_dir)
    else:
        counts = None
    if not offline:
        download(raw_dir, manifest)
    verify_inputs(raw_dir)
    if counts is None:
        run(raw_dir, output_dir, SOURCES)
        counts = verify_outputs(output_dir)
    print(f"READY: {counts['cities']:,} cities; {counts['unique_city_edges']:,} directed routes; {counts['countries']} countries/territories", flush=True)
    print(f"Dataset: {output_dir.resolve()}", flush=True)
    print("Historical observed connectivity; inferred airlines; incomplete coverage. See README.md to build and run the backend.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Reuse installed environment and raw inputs; no installation/download")
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        check_pins()
        if not args.worker:
            if args.offline:
                python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                if not python.is_file():
                    raise ValueError("Offline setup needs an existing .venv; run online setup first")
            else:
                python = prepare_environment()
            call([python, __file__, "--worker", "--raw-dir", args.raw_dir.resolve(), "--output-dir", args.output_dir.resolve()] + (["--offline"] if args.offline else []))
        else:
            call([sys.executable, ROOT / "scripts/run_tests.py"])
            call([sys.executable, ROOT / "scripts/check_phase2.py", "--expect-cities", "12", "--expect-edges", "20"])
            provision(args.raw_dir, args.output_dir, args.offline)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
