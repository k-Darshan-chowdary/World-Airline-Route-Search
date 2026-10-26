# Same Phase 3 dataset for all three teammates

Each teammate runs the same command on their own Windows computer. This setup
is only the Phase 3 dataset foundation; it does not run a route-search GUI,
compile C++, implement BFS, or start Phase 4.

## First-time Windows / VS Code onboarding

1. Have access to the private GitHub repository, Git for Windows, VS Code, and
   **64-bit CPython 3.13** with the Python launcher. Python **3.13.1** is the
   tested CI/baseline patch; the script accepts 3.13 patch releases and checks
   output hashes rather than assuming compatibility. Confirm `git --version`
   and `py -3.13 --version` in a PowerShell terminal. Allow at least **3 GB** free
   disk space and internet access for the first run. The flight file alone is
   1,026,954,012 bytes; do not send it through Git or chat attachments.
2. Use a separate clone for this review branch, especially if your existing
   checkout has work in progress. In a folder you choose, run:

   ```powershell
   git clone --branch feature/phase3-team-dataset-setup https://github.com/k-Darshan-chowdary/World-Airline-Route-Search.git World-Airline-Route-Search-Phase3
   code World-Airline-Route-Search-Phase3
   ```

   If using an existing **clean** clone, fetch the branch and switch to it;
   preserve uncommitted work first. Do not switch or reset another teammate's
   branch, force-push, merge the draft PRs, or copy data over `data/sample/`.
3. In VS Code use **Terminal > New Terminal**, choose PowerShell, and confirm
   the terminal is at the repository root (where this guide and `scripts/` are).
   Run the one-command setup:

   ```powershell
   py -3.13 scripts/setup_dataset.py
   ```

   No Python environment activation, administrator shell, or PowerShell
   execution-policy change is required. If Python is installed without `py`,
   `python scripts/setup_dataset.py` works when `python --version` is 3.13.

The command creates/reuses project-local `.venv`, installs **PyArrow 23.0.1**
using official PyPI wheel SHA-256s in `requirements-import.lock`, runs every
test offline with zero skips, checks the original synthetic fixture, downloads
and verifies the pinned inputs, imports missing output, and independently
checks all reviewed generated hashes, provenance and count accounting.

It ends with:

```text
READY: 819 cities; 19,283 directed routes; 85 countries/territories
Dataset: <your clone>\data\generated\2026-q3
```

All three teammates must see those counts **and** a successful exit. A matching
count alone is insufficient: the reviewed SHA-256s must also pass. Tests now
total **46**: all 36 existing tests plus 10 setup/checksum regression tests.
The setup stops if any test fails, errors, or skips.

## What is locked and where the files go

| Committed file | Purpose |
| --- | --- |
| `data/sources.json` | Exact official Q3 release, full upstream commit, asset ID, URLs, dates, sizes and SHA-256s |
| `data/dataset_2026_q3.lock.json` | Independent reviewed source pins, five table hashes, two notice hashes, exact policy and counts |
| `requirements-import.lock` | PyArrow 23.0.1 CPython 3.13 binary wheel hashes |
| `data/schema_2026_q3.json` | Inspected source schema: 18 string fields, 16,018,874 input rows |
| `docs/phase3_validation.json` | Original full-import measurement and provenance record |

Official source: [MrAirspace 2026 Q3 detailed release](https://github.com/MrAirspace/aircraft-flight-schedules/releases/tag/aircraft_flight_schedules_2026_quarter3),
published **2026-10-13**, asset **637792988**, source commit
`d4906dedba893bea4f7ad5966a81409d6a62336c`.
[OurAirports metadata](https://ourairports.com/data/) is pinned to commit
`d97df1673cc5ba61a09b17ab5936091a669a04ca` (downloaded 2026-10-26).
No `latest` URL or moving branch is used by the setup. Replaced upstream bytes
fail verification even if the release URL remains unchanged.

Ignored local inputs are under `data/raw/phase3/`; output is under
`data/generated/2026-q3/`. Neither is added to Git. Output files:

- `flight.txt`: unique directed `City, Country` pairs, tab-separated, no header.
- `cities.tsv`: compatible city labels and representative airport coordinates.
- `airports.tsv`: OurAirports IDs/idents, ICAO/IATA codes, region and coordinates.
- `city_representatives.tsv`: airport used for each map marker.
- `route_provenance.tsv`: airport-pair/inferred-airline evidence and input-row counts.
- `report.json`, `ATTRIBUTION.txt`, `LICENSE-ODbL.txt`: provenance and legal notices.

Every input and the five data tables plus two notices are byte-hashed against
the committed lock. A generated report cannot authorize its own changed hashes.
The report's source identity, period, counts and filtering policy must also
match. Earlier Phase 3 reports with shortened upstream commit URLs are accepted
only when their source identity and exact input hashes match; they are preserved.
The report JSON itself is checked structurally, not byte-hashed. Data tables
use UTF-8/LF. Attribution uses explicit CRLF to retain the original Windows
notice hash on every platform; the upstream license retains its downloaded bytes.

## Reruns and troubleshooting

Run the same command again to verify an existing dataset. It does not replace
existing inputs/output or download a verified file again. With the environment
and raw files already available, avoid all installation/download requests:

```powershell
py -3.13 scripts/setup_dataset.py --offline
```

To verify independently without installing/importing:

```powershell
.\.venv\Scripts\python.exe scripts/dataset_lock.py
.\.venv\Scripts\python.exe scripts/validate_global.py
```

The first checks the five raw inputs and reviewed table/notice hashes; the
second checks formats, links, counts, dates and representative coordinates.
Use `dataset_lock.py --inputs-only`, `--outputs-only`, or `--pins-only` to narrow
the check. `--pins-only` needs no download or generated files.

If a checksum fails, preserve the file and error message. Check the branch and
local edits with `git status`; do not generate new expected hashes or weaken
the checks. For a clean import alongside existing output, use:

```powershell
py -3.13 scripts/setup_dataset.py --output-dir data/generated/2026-q3-clean
```

A changed input needs a separate raw folder as well:
`--raw-dir data/raw/phase3-clean`. Never delete teammate work to make setup pass.
An incomplete `.venv` is reported instead of replaced; use a fresh clone.
Interrupted downloads restart on rerun. Only completed, hash-verified source
files are published; partial imports are never announced as a ready dataset.
If the upstream URL becomes unavailable, report the failed URL and use a
previously verified local copy; do not silently substitute another dataset.

## CI and review boundaries

`.github/workflows/dataset-tests.yml` runs on pull requests and pushes to
`main`/`feature/**`. Its Windows Server 2022 and Ubuntu 24.04 jobs use CPython
3.13.1, immutable
checkout/setup-python action revisions and the hash-locked PyArrow wheels.
Tests use small synthetic fixtures, including actual Parquet IO. Network calls
are blocked during the test run, skipped tests fail CI, and CI never calls
`download_phase3.py`, `import_global.py` or `setup_dataset.py` as a job step.
Dependency installation needs internet; regular CI does **not** download or
claim to revalidate the 1 GB worldwide source. Full input/output verification
is the teammate setup's job and was also performed locally.

Branch stack: PR #1's `feature/person1-graph-q1-q2` -> PR #2's
`feature/phase3-global-dataset-importer` -> `feature/phase3-team-dataset-setup`.
This branch's draft PR targets the Phase 3 importer branch. Keep PR #1 and #2
unchanged, do not merge, and coordinate dependent PR bases after review.

## Data interpretation and redistribution

This is **incomplete historical observed connectivity**, not all world routes,
live schedules, verified passenger service, or verified operating-airline data.
Strict filters retained 1,241,591 of 16,018,874 input rows. Airline codes are
callsign-inferred; evidence-row counts are not unique flight frequencies.
See `docs/phase3_import.md` for filtering and airport/city matching caveats.

Flight-derived databases carry **ODbL 1.0**, with attribution to MrAirspace /
Sebastiaan Menger and ADSB.lol. OurAirports metadata is Public Domain. Preserve
the included attribution, license, report and required ODbL terms when sharing
the adapted database. No source or license notices are removed by onboarding.
