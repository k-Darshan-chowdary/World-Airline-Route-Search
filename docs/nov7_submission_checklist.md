# November 7 CSCE 2110 submission checklist

This is an action checklist for the three-person team, not a claim that unchecked items are complete.

## November 3 — Implement and stabilize
- [x] Preserve the already merged Person 1 dataset, graph, BFS, Q1, Q2 and backend contract.
- [x] Start Q3/Q4 implementations and basic tests on a review branch.
- [x] Start the GUI prototype and Python subprocess adapter.
- [ ] Obtain passing CI on the **final** commit; review failures and correct them.
- [ ] Have the actual teammates examine and understand the code for their assigned areas.

## November 4 — Run in VS Code
- [ ] Person 2: compile Q3/Q4, demonstrate both a valid and an impossible Q3 walk, meeting-city Q4 and edge cases. Review exact/heuristic limitation.
- [ ] Person 3: install the documented PySide6 and Folium dependencies, launch all four GUI forms, verify maps and error messages, capture real screenshots.
- [ ] All: agree on examples in the bundled synthetic sample and local verified historical dataset.
- [ ] Review and merge the integration PR only after tests and user approval.

## November 5 — Complete integration
- [ ] Build Debug and Release and run the original offline Python suite and every CTest target.
- [ ] Validate the checksum-locked 819-city dataset locally if present.
- [ ] Run Q1/Q2/Q3/Q4 from a fresh checkout against the submitted fixture.
- [ ] Verify UTF-8 labels, Q3 approximation disclosures, Q4 directed-distance semantics and map labels.
- [ ] Inspect contributors' own work; fix regressions before presentation screenshots.

## November 6 — Presentation and packaging
- [ ] Create the complete team PowerPoint including design, data structures, algorithms, pseudocode, Big O, tests, expected/actual output, responsibilities and reflection, and references.
- [ ] Put the **creator's full name in the footer of every slide** and list all member names on the title slide. Each member must actually contribute slides.
- [ ] List contributions and approximate work percentages that sum to 100%, reflecting actual effort, not nominal assignments.
- [ ] Capture readable, real screenshots of each operation and a failing/unreachable case.
- [ ] Package source .cpp/.h files, necessary sample data/tests, and README into ONE ZIP; submit PPTX separately. Do not include the 1GB raw data or binaries as substitutes for source.
- [ ] Extract the ZIP into a new folder and follow its README to compile and test successfully.
- [ ] Follow the instructor's filename convention using every team member's last name.
- [ ] Rehearse the complete talk; do not claim heuristic Q3 globally optimal.

## November 7 — Submit
- [ ] Confirm final deadline/time in Canvas, submit PPTX and ZIP through Canvas with time to correct upload issues.
- [ ] Open the submitted PPTX and ZIP after upload and verify they are correct.

## Remaining limitations
- Global data reflect incomplete historical ADS-B observed connectivity, not current routes, schedules, or bookings.
- Q3 with more than 14 reachable cities uses a heuristic and is not guaranteed minimum.
- GUI test automation does not substitute for a live Windows graphical smoke test.
