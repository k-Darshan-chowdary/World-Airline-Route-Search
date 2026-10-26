"""Download the pinned Phase 3 inputs without loading them into memory."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def verify(path, spec):
    actual = fingerprint(path)
    if any(actual[key] != spec[key] for key in ("bytes", "sha256")):
        raise ValueError(f"{path.name}: size or SHA-256 differs from sources.json")
    return actual


def download(folder, manifest):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, spec in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("manifest filenames must be plain basenames")
        target = folder / name
        if target.exists():
            verify(target, spec)
            print(f"Verified existing {name}", flush=True)
            continue
        temporary = folder / (name + ".part")
        # Restart a partial download, but never replace an existing final input.
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "World-Airline-Route-Search/phase3"})
        try:
            received, last = 0, time.monotonic()
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    received += len(block)
                    if received > spec["bytes"]:
                        raise ValueError(f"{name}: exceeds pinned byte count")
                    output.write(block)
                    if time.monotonic() - last >= 10:
                        print(f"{name}: {received:,}/{spec['bytes']:,} bytes", flush=True)
                        last = time.monotonic()
            verify(temporary, spec)
            temporary.rename(target)
            print(f"Downloaded and verified {name}: {received:,} bytes", flush=True)
        finally:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "sources.json")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw" / "phase3")
    args = parser.parse_args(argv)
    try:
        download(args.raw_dir, json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
