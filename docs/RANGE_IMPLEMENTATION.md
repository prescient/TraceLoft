# Driving range implementation checklist

Requested 2026-10-01. This is the execution plan for the first usable range, based on
[range research](DRIVING_RANGE_PLAN.md), the SQLite proposal and the dark studio principles.
Checkboxes are checked only after implementation and the stated verification.

## Product and design contract

Practice → Driving range setup → open-ended live range → completed results / Sessions review.
Use the existing dark studio, compact bag column and club circles. Healthy capture stays in the
header. Large latest carry/total/offline tiles lead; the dispersion chart and modeled side flight
are the central feedback. Shot management sits below, with clear scope, selection count and Undo.
Start with free practice or an optional distance target/window. Target edits apply to future shots.

Foresight remains the reported-distance source. OpenGolfCoach is an independent, pinned estimate
from launch inputs only. Never feed reported carry/total into the prediction. Carry and total
scatter choices must identify their coordinate source. Foresight offline is not proven to be the
carry landing offset; show it as reported offline versus distance, not a verified landing map.
OpenGolfCoach landing coordinates support an estimated carry map. Total lateral rollout requires
a separately identified projection because the library's offline output is at landing.
Do not present inferred club delivery, smash factor, grades or simulated paths as measurements.

## Execution

- [x] 1. Inspect/pin OpenGolfCoach, verify API, coordinate/sign conventions, license and failure behavior.
- [x] 2. Implement a versioned flight adapter: immutable inputs/results, model assumptions, trajectory,
      handed shot names, carry/total/height/descent/time estimates and explicit unavailable reasons.
- [x] 3. Add an open-ended Python range session with frozen targets/equipment, receipt deduplication,
      durable SQLite saves, completion/abandonment/review and recoverable session deletion.
- [x] 4. Implement atomic bulk cleanup by exact stable shot keys: exclude/include, remove/restore,
      retag bag/club, mandatory reason, explicit before/after confirmation, durable audit and Undo.
      Preserve original measurements/tags. Reject stale cleanup revisions and invalid memberships.
- [x] 5. Build setup and live/review UI: bag picker, optional target, latest metrics, carry/total scatter,
      source choice, linked shot inspection, modeled flight and shape distribution, per-club statistics.
- [x] 6. Build shot workspace: club/bag/shape/state/text filters, sorting, visible-filter selection,
      row/bulk actions, removed-shot recovery and CSV of the displayed cohort with provenance.
- [x] 7. Verify units, symmetry, missing/zero data, model failures, immutable predictions, persistence,
      cleanup rollback/Undo/conflicts and existing drill regression through automated tests.
- [x] 8. Review real browser UI on isolated data at desktop, tablet and phone widths; test empty/live/
      ended/review, controls, keyboard selection, exits, refresh, filtering and every cleanup path.
- [x] 9. Finish docs/backlog/navigation/third-party notices, retain screenshots and verification evidence.
- [x] 10. Back up and safely reload the local service if idle; preserve an active session if present.
      Verify the real app opens with no test data added and report remaining live acceptance work.
- [x] 11. User-added test harness: Demo range mode, one or ten synthetic shots, clear labels,
      session filtering, recoverable cleanup, and strict separation from live session/capture data.

## Verification boundaries and later work

Real full-swing OCR, source offline semantics, Foresight/model agreement and physical phone networking
need user shots/hardware. Isolated test data cannot establish those. Model inputs/results and source
definitions stay reviewable. No model calibration is inferred from synthetic examples.

First-release cleanup is session-scoped. Cross-session analysis sets, trend/outlier policy histories,
club gapping, wedge matrices, multivariate dispersion ellipses, environment scenarios and games remain
separate work. Range misses are preserved in all-recorded counts; cleanup never removes raw captures.

## Progress / evidence

- Planning complete: reviewed range/backlog, storage, lifecycle and dark studio references.
- Backend complete: pinned OpenGolfCoach 0.3.0 native wheel; adapter calls measured about 0.27 ms
  per sample. Full final regression: **143 Python tests and 7 Node tests passed**; JS syntax passed.
- Isolated browser review passed at 1440×1100, 850×1100 and 390×844: setup/empty/live/ended/review,
  single/ten-shot generation, multiple clubs/bags, target changes, carry/total and source switches,
  club filtering, exact filtered CSV, bulk retag/Undo, exclusion/inclusion and removal/restoration.
- Navigation/lifecycle passed: refresh, copied setup, Return to active drill, blocked replacement,
  Exit Cancel, completion while capture remains running, Abandon Cancel/Apply, saved-review Exit,
  cleanup in review, Back closing an unapplied dialog, demo deletion/Undo. Keyboard chart inspection
  updates the selected shot; table controls provide individual access to overlapping chart points.
- Phone document width 375 within 390 px viewport; club controls 44 px. Charts/table remain within
  their containers; enlarged mobile graph labels and tighter desktop feedback spacing were reviewed.
  No browser console errors/warnings. Actual screenshots saved under designs/driving-range-*.png.
- Documentation/navigation/backlog/model notices updated. Real service was idle, backed up and
  reloaded at localhost:8765; real app opens Driving range setup. All state-changing QA used isolated
  storage. Pre/post hashes matched for 7 sessions, 30 attempts, 213 shots and 273 observations.
- Verified pre-reload snapshot: `%USERPROFILE%/GolfData/data/backups/golfdata-20261002T033649-8fdfb1d4.sqlite3`.
  Temporary QA service stopped and viewport reset. No real demo/test sessions were created.
- Remaining physical acceptance is listed above; no accuracy, real full-swing OCR or remote-phone
  validation is claimed from synthetic tests. Google Drive backup remains separate proposed work.
