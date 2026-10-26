# Person 1: Phase 1 setup

Verified repository: https://github.com/k-Darshan-chowdary/World-Airline-Route-Search
The live Chrome repository tab and signed-in account both identify
`k-Darshan-chowdary`. The repository is private.

Working folder: `%USERPROFILE%\OneDrive\Desktop\World-Airline-Route-Search`
(this computer redirects the Windows Desktop to OneDrive).
Cloned from `main`; feature branch: `feature/person1-graph-q1-q2`.
Use this branch for changes and a draft PR targeting `main`; merge only after
the user's review. The original `Airline_Team_Roles.docx` and `.gitignore`
are preserved, and the original README introduction is retained.

Tool versions verified in the VS Code integrated terminal on 2026-10-26:

| Tool | Version |
| --- | --- |
| Git | 2.55.0.windows.3 |
| g++ / GCC | 16.2.0, MSYS2 UCRT64 Rev3 |
| Python | 3.13.1 |

The compiler is not old; no compiler installation or upgrade was performed.
No C++ source or compilation is required for these phases. This does not certify
future C++ features, third-party libraries, or GUI dependencies. Python checks
use only the standard library. If another machine has an older GCC, record its
version and supported C++ standard before later graph work; do not assume
C++17/20 support or replace software unnecessarily.

To recheck in VS Code, open Terminal > New Terminal from the project folder:

```powershell
git --version
g++ --version
gcc --version
python --version
git status --short --branch
python scripts/check_phase2.py --expect-cities 12 --expect-edges 20
python -m unittest discover -s tests -v
```

Scope ends at repository setup, folder structure, documented synthetic data,
and data validation. Graph loading, `Graph.cpp`, BFS, Q1, and Q2 algorithms
remain for later phases. The branch name reserves that future responsibility;
it does not imply those algorithms are complete.

Validation on 2026-10-26: the checker passed with 12 cities, 20 directed
edges and 12 coordinate records; all 13 unittest cases passed in the VS Code
integrated terminal.
