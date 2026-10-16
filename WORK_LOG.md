# TraceLoft work log

## 2026-10-16 — Source alerts under the header (D73)

- `shot_input.source_alerts()`; heartbeats set `input.alerts`, disconnect clears it.
- `web/recording.js sourceAlerts()`, `#source-alerts` under the header (index.html), `.source-alert`
  styles, rendered in `navigation()`; hidden while the browser is offline.
- **Verification:** 257 Python tests (new: alerts kept, capped, left alone by shots, cleared on
  disconnect) and 86 UI tests (labels, escaping) pass. Live: the Relay page showed the red "Not
  recording" banner for rēlā and the amber "Attention" banner for GSPro not answering, with the exact
  messages TraceCapture sent.

## 2026-10-16 — Estimates for every non-putt shot, schema 7 (D71)

- `shot_schema.shot_estimates()` and `is_putt()`; `Store.shot_estimates()` runs it in a savepoint after
  each accepted shot (ingest, practice links and attempt saves). `club_model.estimate(..., club=)`
  accepts an explicit club type.
- Schema 7 (`v0007_shot_estimates`): five `shot_derived_metrics` club columns, `v_shots_analysis`
  rebuilt as one row per shot, and a backfill of all existing shots.
- `write_result` inserts only supplied columns, so released steps keep working on older schemas.
- The CSV export adds `shots_analysis.csv`.
- **Verification:**
  - 256 Python tests pass (5 new in `tests/test_shot_estimates.py`). The first full run found 111
    failures: practice saves delete a temporary shot's results, and the new flight trajectory rows
    blocked that (foreign key). The cleanup now removes trajectories too.
  - Live: the service upgraded the real database 6 → 7 with a verified backup. The backfill estimated
    7 of 9 shots; the 2 putts (no spin) got none. TraceLoft's modeled carry matched rēlā's within
    0.06 yd on all 4 chips that have rēlā estimates. Face angle mostly agreed in direction. TraceLoft's
    dynamic loft ran 7-23° above rēlā's.
  - Not yet seen live: a new shot estimated at intake (the backfill path ran; intake is covered by tests).

## 2026-10-16 — Source estimates table, schema 6 (D70)

- First live rēlā shots (via TraceCapture's rēlā source): 2 putts and 3 chips stored with correct ball
  data and null putt spin. But rēlā's face, lie and loft for the chips were stored as measurements;
  rēlā's log shows the LPi measured none of them.
- Schema 6 (`migrations/v0006_source_estimates.py`, `sql/0006_source_estimates.sql`) adds
  `source_estimates`. `shot_input.source_estimates()` validates `TraceLoft.SourceEstimates`;
  `Store._source_estimates` writes the rows inside `_observation`. The CSV export includes the table.
- The v1 upgrade test now expects one backup per step (`SCHEMA_VERSION - 1`) instead of a fixed 4.
- **Verification:**
  - 251 Python tests pass, including 2 new intake tests (rows stored apart from `metric_values`,
    carry converted to metres, out-of-range value left out, updates refused, malformed blocks → 501).
    Ruff is not installed on this PC, so lint did not run.
  - Live: the service upgraded the real database 5 → 6 with a verified backup; the 5 existing shots
    are intact.
  - Live, 3 rēlā chips at 12:56: each has 7 `source_estimates` rows matching rēlā's packets exactly
    (carry 1.3 yd → 1.18872 m), and only club speed, attack angle and path in `metric_values`.
    TraceLoft computed no D64 estimates for them: they were not in a range-family session.

## 2026-10-16 — Simulator on another PC (D69)

- New PC setup: Python 3.12.10 via winget, `.venv` from `requirements-lock.txt`, fresh database.
- `shot_input.simulator_host()` accepts this PC or a private-network IP address and refuses names and
  public addresses. `Relay.configure` uses it; the input/simulator port conflict applies only on this PC.
- Relay → Connection details has a Simulator address field ("Save connection"). Changing the
  destination keeps the address.
- **Verification:**
  - 249 Python tests pass, including three new address tests. 85 UI tests pass (GitHub Desktop's
    Electron as Node). The Relay page change has no browser-helper test.
  - Live: Relay saved GSPro at 10.10.0.190:921 and TraceCapture received it in its context. In the
    browser, Connection details shows the address and port and the page says TraceCapture delivers.
  - Not verified: an actual connection to GSPro. This PC's WireGuard tunnel ("GolfLaptop") blocks
    untunneled LAN traffic (WinError 10013), so nothing could reach 10.10.0.190 yet.

## 2026-10-15 — Random distances (D67)

- New Full swing drill `random-distances` ("Random distances"), chosen by the user as its own drill
  with no club hint and a fixed number of targets. `random_distances.RandomDistanceSession` extends
  the driving range:
  - It draws a carry target from a grid (shortest + whole steps), each at least the minimum change
    from the last and never a repeat.
  - Each scored shot advances; the session finishes itself after the chosen count.
  - A shot without carry is unscored and keeps the target.
  - The session's draw, not the published context, is the scoring target.
  - Exclusions change the score, not progression.
  - `summary()['targets']` adds in-window, mean and mean absolute error, and short/long counts.
- Range hooks: `DrivingRangeSession.shot_context()` and `advance()` (no behavior change for the
  range). Demo shots in this drill aim at the drawn target: `demo_speed()` inverts the flight
  model by bisection.
- Registry: `RandomDistanceParams` and a shared `TargetWindow` mixin (drill_params.py), a catalog
  entry, factory and scorer, and `session_kind()` → `random_distances` from `target_plan: 'random'`
  (no migration). The service refuses Change target for this drill.
- Browser:
  - `web/random-distances.js` holds the setup screen with a live preview that explains invalid
    setups, and the runner decoration: a next-target panel above the club picker, the last result in
    words, the score and progress, and a result headline when finished.
  - Registered in `web/features.js`, `web/navigation.js` and the Full swing category.
  - The range runner now receives the server summary.
  - The progress bar is SVG because the CSP forbids inline styles.
- Tests:
  - `tests/test_random_distances.py` (11): grid and gap; progression to completion and the
    published next target; unscored shots; stale context; refused target change; setup validation;
    exclusion vs progression; restore after restart; demo aiming; Analyze and the CSV export.
  - `tests/test_random_distances_ui.mjs` (4): grid parity, setup preview, result wording,
    route/category/feature.
  - `tests/test_drills.py` updated for the catalog, envelope (53 fields) and session kind.
- Browser check in an isolated instance (fresh database, input 9902, HTTP 8798):
  - The Full swing card leads to setup; the invalid-setup message showed for 100–110 yd with a
    15 yd change.
  - Demo of 6: the target advanced after every shot with ≥ 15 yd change (110 → 65 → 180 → 110 …).
    The result line and score updated, and the session ended itself with Session over and the
    result panel.
  - After reload, the finished live view titles without "review". Sessions shows
    "4 in window · Complete". The saved review highlights Sessions. Edit setup copied every
    parameter.
  - Live session of 3: synthetic Open Connect shots to port 9902 were scored against 170, 75 and
    90 yd in turn. Each reply's `range_context` carried the next target and none after
    completion. The club tag was kept.
  - A shot without spin is rejected by Open Connect itself (501), so the unscored path is covered
    by the unit test only.
  - Abandon returned to Practice with the banner and notice. No script errors.
  - Layouts: 1366 × 1024 and 1366 × 900 show the next target and the club picker above the fold;
    390 × 844 stacks with no horizontal overflow.
- Not verified: a physical iPad and a real shot source.
- Verified: `python verify.py` passed **246 Python** and **85 JavaScript** tests and lint.

## 2026-10-13 — Shot input from other machines (D66)

- `--remote-input` (web_app.py, launch_web.py) makes the Open Connect input bind 0.0.0.0:900 through
  `ShotInput.accept_remote()`. The default stays 127.0.0.1.
- `Launch TraceLoft LAN.cmd` passes it, and so does TraceCapture's `launch_capture.py --lan`.
- launch_web refuses to reuse a running service that lacks it.
- The runtime file records `remote_input`, and startup prints the address to point a source at.
- **Relay page:** the chip reads "any machine"; the hint gives this PC's address plus a no-password
  warning; the source line names a remote source's address (`input.peer`).
- **Verification:**
  - New relay test: the default binds 127.0.0.1 and records the peer, which clears on disconnect.
    Remote mode binds 0.0.0.0, accepts a connection, and still refuses a second source with 503.
  - Full `verify.py` before commit.
  - Not checked: a real connection from another machine. That needs the Windows Firewall rule for
    TCP 900 and the VPN or VM in place.

## 2026-10-13 — Club estimates under both Analyze bases

- After the restart the golfer saw the four estimates in the picker but no values. Analyze opens on
  "Source-reported metrics", where the estimates were unavailable by design: n=0 there, n=103 under
  the analytical basis.
- They have no source reading to replace, so `metric_values` now computes them for both bases.
  Labels still say "Estimated". Frozen collections, which use source values, now also record them.
- **Verification:** `verify.py` passed; the test now checks that both bases give the same value.
  Checked on the live service after a restart (below).

## 2026-10-13 — Club estimates in Analyze

- Analyze lacked the D64 club estimates: face angle, face to path, dynamic loft and spin loft. The
  range page computes them, but they were never written to SQL, which Analyze reads.
- **Change:**
  - `analysis.METRICS` gains the four as "Estimated …" metrics.
  - Under the "Selected analytical calculations" basis, `analysis_schema.metric_values` computes them
    with `club_model.estimate`. It uses the stored source readings and the effective club tag, the same
    function as the range page. The basis method text names the model.
  - Under the source basis they stay unavailable.
- **Not persisted:** they are computed on read, not stored as versioned calculation results. Storing
  them would need a schema migration (new derived-metric columns). That is in BACKLOG as an option.
- The OpenGolfCoach distances, apex, descent and hang time, plus calculated smash and rollout, were
  already in the analytical basis (saved attempt flight snapshots).
- **Verification:**
  - `verify.py` passed: Python 234, JavaScript 81, ruff clean.
  - New tests: the values equal `club_model.estimate`, with the iron weights checked by hand; the
    source basis and missing inputs stay unavailable; CSV has the new columns.
  - An isolated instance (temp database and ports) served `/api/analysis` with metric `face_angle`, the
    new labels and the method text. It had no shots.
  - Not checked on real data: the running service still has the old code until a restart.

## 2026-10-13 — Club snapshot shows every latest-shot metric

- The range Club snapshot now has a median/IQR column for each metric of the latest-shot panel:
  - **Always:** carry, total, absolute offline, ball speed, total spin, launch and descent.
  - **In sessions with club data:** club speed, smash factor, angle of attack, club path, and the D64
    estimates (face angle, face to path, dynamic loft, spin loft).
- **Smash factor** falls back to ball speed / club speed, as on the latest shot.
- **Signed angles** show the median's direction for the session's handedness.
- **Shared wording:** the direction words (up/down, in-to-out, open/closed) are now one set of helpers
  for the tiles and the table.
- **Layout:** the club column is pinned while the table scrolls sideways.
- Corrected DRIVING_RANGE.md, which still said the snapshot used reported distances only (pre-D63).
- **Verification:**
  - `verify.py` passed: Python suite, JavaScript 81, ruff clean.
  - New test: the column set with and without club data; medians for club values, the smash fallback
    and estimates; direction words for both hands; missing stays missing.
  - The existing latest-shot tests still pass after the shared-helper refactor.
  - In the browser, on the real 100-shot import review (read only):
    - all 15 columns with plausible values; club columns n=98, because two shots had `-`;
    - the club name stays put while scrolling;
    - no page overflow at 390 px.
  - Screenshots could not be captured, so the look was checked through the DOM, not by eye.
  - Not checked: real iPad Safari.

## 2026-10-13 — iPad table import sessions (D65, TraceLoft side)

- `shot_input.import_batch()` validates the `TraceLoft.Import` block.
- `ShotInput.import_session()` loads or creates the batch's driving range session: the batch id as the
  session id, the chosen bag/club, no target, and `import_source`. It finishes once every index has arrived (delivery order is not guaranteed; tested out of order).
- Import shots are recovered (never live or forwarded) with provenance `ipad_import`, and the
  import's club and session replace the packet's context.
- `find_overlap()` flags matches with live captures from the last 30 days.
- Context adds `equipment_catalog`.
- `DrivingRangeSession` accepts `session_id` and `import_source`.
- Range page: "Imported from iPad table" with a possible-duplicate count, and per-shot flags.
- **Verification:**
  - New relay test: an import alongside an active range session, with one matching live shot. Result:
    its own finished session, the chosen club, one duplicate flagged, the active session untouched,
    nothing forwarded, invalid batch refused.
  - Relay 15 tests and JavaScript 80 pass; full verify before commit.
  - Not done: the TraceCapture side and a live scroll import.

## 2026-10-12 — Range descent, peak height and hang time from OpenGolfCoach

- The Descent angle tile still read the source's value, which the iPad club table doesn't report. The
  range values (D63) now also hold OpenGolfCoach descent (°), peak height (ft) and hang time (s).
  Tiles and the club snapshot use them, labeled "est.".
- Older OpenGolfCoach-basis shots get them filled from their stored flight when the session loads.
  Scoring is unchanged.
- **Verification:** Python 231, JavaScript 80, lint clean; new assertions for modeled descent, peak
  and hang time, the load-time fill, and the JavaScript fallback.

## 2026-10-12 — Estimated face angle, face to path, dynamic loft, spin loft (D64)

- New `club_model.py` (D-plane estimates with weights per club type).
  - Range shots store `club_estimates` at capture, recalculated when a retag or undo changes the
    effective club.
  - The Club delivery panel adds four labeled estimate tiles (open/closed by handedness).
  - CSV `est_*` columns, including the spin-axis face-to-path cross-check.
- **Verification:**
  - `tests/test_club_model.py`: formulas, club types, missing inputs.
  - JavaScript test for open/closed by handedness.
  - Python 230, JavaScript 79, lint clean.
  - Not yet seen with a live shot (the iPad's mirroring was disconnected).

## 2026-10-12 — Club delivery on the range's latest shot

- New "Club delivery" row under the latest-shot readings: club speed, smash factor, angle of attack
  (up/down) and club path (in-to-out/out-to-in by session handedness). It is shown only when the
  session has club data.
  - A source smash factor is used when reported; otherwise ball/club speed, labeled "calc.".
- `range-data.js`: `clubReadings()` and `hasClubData()`; `studio.css`: `.range-club-metrics` (4 columns,
  2 at ≤600 px).
- **Verification:**
  - JavaScript tests: direction words, a left-handed path, the calculated smash label, unavailable
    values, and session detection.
  - Isolated instance with a club-data shot: the row read "86.4 mph · 1.39 · 3.2° down ·
    2.3° in-to-out" at 1376 × 1032, and at 390 px it shows two per row with no horizontal overflow.
  - Not verified: a real iPad Safari check.

## 2026-10-12 — Range distances always from OpenGolfCoach (D63)

- `driving_range.range_distances()`: each new range shot stores `range_vals` (carry, total, and
  offline at the total endpoint) and `distance_basis`. It is `opengolfcoach` whenever the model runs,
  and `reported` only as the labeled fallback. Scoring, the distance window and `summary()` use it.
  `range_value()` keeps older shots on their reported values.
- `flight_model.with_spin_pair()`: total spin and axis are derived from back/side spin when only that
  pair is reported, for the model only.
- `publish_context`: range-family drills no longer require a reported carry/total column from the
  source.
- Page: `rangeValue()` and `estimated()` in `range-data.js` drive tiles, the shot table, sorting,
  statistics, club snapshot and CSV (new `range_*` columns). Modeled distances are labeled "est.",
  and the setup hint is updated.
- **Verification:**
  - `python verify.py`: 227 Python and 77 JavaScript tests, lint clean.
  - New tests:
    - a no-distance shot and a reported-carry shot both scored on the model;
    - measurements untouched; reload round-trip;
    - the reported fallback; legacy shots; no required distance;
    - the back/side-only model; the JavaScript helper and CSV.
  - Isolated instance (temp database, ports 9911/8791): two shots over Open Connect were scored on
    OpenGolfCoach (144.1 yd in the window; 177.6 yd outside it, despite a reported 170). The page at
    1376 × 1032 shows the labeled estimate tiles, the statistics basis and the club snapshot.
  - Not verified: live shots from the club table into the user's real range session.

## 2026-10-12 — Owner-allowed addresses in LAN mode (D62)

- `web_app.extra_hosts()` reads `allowed_hosts.txt` (gitignored; one host per line, # comments) at
  startup in LAN mode. The host check accepts those names too, and startup prints them.
- The user's file lists the home public IP for a simulator screen reached through a port forward. The
  user accepted that TraceLoft has no login.
- **Verification:**
  - New `tests/test_access.py`:
    - the file format;
    - local mode refuses the public address;
    - LAN mode refuses it until it is listed, then accepts it;
    - other names stay refused.
  - Ruff clean.
  - After a LAN-mode restart, test requests addressed to the public IP and the LAN IP got 200; an
    unlisted name got 400.
  - Live: the user connected from the simulator screen through the port forward (2026-10-12).

## 2026-10-11 — Simulator hand-off to TraceCapture; live flight estimates (D61)

- `ShotInput.context()` adds `simulator` (Relay destination, host, port) to every Code 200 context.
- `Relay.delegate()`: a connected sender whose packets declare `TraceLoft.SimulatorDelivery: 'source'`
  makes the relay:
  - release the simulator connection and idle ("Sent directly by the shot source");
  - forward nothing, while each such shot is audited `handled_by_source`.
  The relay reconnects when that sender disconnects. Relay's page explains the state.
- `live_estimate()`: when a shot reports no carry but has spin and launch above zero, the live read
  carries an OpenGolfCoach estimate of carry, total and offline. Relay shows it under "Estimated
  flight", labeled as modeled. Stored measurements and drill scoring are unchanged.
- Tests (`tests/test_relay.py`):
  - takeover with a fake simulator: context, release, no forwarding, audit row, resume on disconnect;
  - estimates for a swing, none with reported carry, none for a putt.
- **Verification:**
  - Isolated tests pass.
  - A cross-repo smoke ran against an isolated instance (temp database, input 9901, web 8791) with a
    fake simulator and TraceCapture's real packet code and simulator link: exactly two shots reached
    the simulator, both on TraceCapture's connection; the relay released and later resumed; the putt
    played as zero spin; the swing got estimates (carry 181.9, total 187.5, offline 6.5 yd).
  - Not verified: a real GSPro or Infinite Tees session, a real browser check of the Relay page, and
    the user's real service (not restarted yet).

## 2026-10-11 — Shots measured without spin (Premier memory putts)

- TraceCapture's new Premier memory source reads Foresight putts, which the LPi measures without spin
  (`SpinIsValid = 0`). Until now every ball packet needed a spin pair.
- `open_connect.validate_packet` now accepts BallData without spin when the private extension
  declares `TraceLoft.SpinUnavailable: true`. Only a literal `true` counts, and such a packet must
  carry no spin field. Spin is stored as null, never zero (missing is not zero).
- `simulator_packet` forwards such shots with TotalSpin, SpinAxis, BackSpin and SideSpin set to 0,
  the user's choice for simulators (2026-10-11). Measured spin is forwarded unchanged.
- Tests (`tests/test_relay.py`):
  - a protocol test for validation, the forwarded zero spin and the rejected variants;
  - an end-to-end test that sends a TraceCapture-style putt over TCP, checks it is stored with four
    null spin metrics plus club speed, and checks the flag is preserved in `raw_packet`.
- Verified with isolated tests only. The real service was not restarted. The live check comes from the
  user's putting session after a restart.

## 2026-10-11 — Browser feature registry and runner lifecycle

- Added `web/features.js`, the browser half of the drill registry. Five features (golf,
  collection, range, distance ladder, putting) declare:
  - their setup ids and the sessions they `runs`;
  - capabilities: navigation section, prompt unit, Sessions-list result, and whether the runner
    depends on the sessions revision;
  - `setup()` and a runner `mount()` returning `{ update(view), dispose() }`.
- `app.js` dispatches setup, runner, navigation highlight, exit/abandon prompts and
  destinations, the Sessions-list outcome and the render key through features. It no longer
  branches on drill ids, drill names or session kinds. Runner callbacks (golf aim/simulate/
  correct, range cleanup/target, equipment) moved into the features and use a host bound to
  the mounted session (`runnerHost()`).
- The putting setup and runner moved from `app.js` to `web/putting.js` unchanged.
- Lifecycle: a runner mounts when it opens or when its session, golfer or live/review mode
  changes. It is disposed on navigation and before a remount. Disposal disconnects the course
  camera and range scatter ResizeObservers and cancels the replay frame without resetting the
  replay clock. Before, observers lingered until their next callback. Per-session view choices
  (range filters, golf panels/zoom) still persist by design. `update()` still repaints the whole
  runner inside `preserveInteraction`; incremental updates are not implemented.
- Tests (`tests/test_features.mjs`):
  - every catalog id in `drills.py` has exactly one setup feature, and every setup id parses as
    a route;
  - session routing, with putting as the fallback;
  - capability values and the golf/putting result lines;
  - a putting runner mounts, updates for live and review, and disposes;
  - golf disposal disconnects the camera observer.
- DOM comparison in the isolated instance (separate database, input 9901, HTTP 8799, 1366×1024).
  The old code and the new code each ran three passes from the same restored database snapshot:
  - Pass 1 (40 screens with the range session active): identical.
  - Pass 2 (10 mutation states): only the random demo shot's values differed.
  - Pass 3 (39 screens with no active session, so every setup screen renders): only data
    created in pass 2 differed (start times, demo values, new session id prefixes, Analyze config
    order). The golf Sessions line from the new `result` capability matched.
- Manual checks in the same instance:
  - golf: Play highlighted; abandon/exit prompts say "round" and "Play"; abandon returns to
    Play with the notice; the camera ResizeObserver disconnects on leaving the runner and a new
    one is made on return;
  - `#setup/pace` launched through the moved setup form with the entered repetitions;
  - two synthetic putts sent to port 9901 appeared live; row selection and exclusion worked;
  - abandon returned to Practice with "Start a new drill"; the saved review shows Sessions
    highlighted and "Exit review" returns to Sessions;
  - no script exceptions in the console.
- Navigation routes and guards are unchanged, so NAVIGATION.md needed no update.
- Verified: `python verify.py` passed **217 Python** and **76 JavaScript** tests and lint.

## 2026-10-11 — Every UI template escapes by default

- Converted the remaining `innerHTML` templates in all `web/*.js` modules to the `html` tag and
  removed every hand-written `esc()` call. Chart helpers (`trend`, `gauge`, `progress`,
  `distanceTrend`) return `html` and build lists from arrays instead of string concatenation.
- `html` now renders booleans like a plain template literal ("true"/"false"). Rendering `false` as
  nothing would have emptied `aria-pressed="false"` attributes; the DOM comparison below caught
  it. Optional fragments therefore use ternaries (`cond ? html`…` : ''`) everywhere.
- Fixed an existing bug: the empty putting log printed the literal text `${modeled?9:6}` as its
  `colspan` value because that template was not a template literal.
- Tests: `tests/test_html.mjs` covers the boolean and truthiness semantics.
  `tests/test_html_usage.mjs` fails on any markup template without the `html` tag, any
  `cond && html` fragment and any remaining `esc()`. The UI tests that match markup with regular
  expressions convert the returned `SafeHtml` to a string.
- Verified with a DOM regression comparison in an isolated instance (separate database,
  input 9901, HTTP 8799). The same seeded data was rendered with the old and new web code at
  1366×1024, and `#app` plus open dialogs were captured after rendering settled:
  - 42 screens: every route, Sessions/Analyze/Calculations/Play/Equipment views, setup screens
    and finished-session reviews. The old and new markup was byte-identical.
  - 10 mutation states (restored from the same database snapshot): range cleanup/target/tag
    dialogs, top-view inspection, course-import preview, empty putting and ladder runners,
    a wedge demo after a shot, and the 2D golf preview and after-shot. Ids and timestamps were
    normalized. The only differences were the colspan fix and the random demo shot's values in
    the wedge demo (a structural comparison with numbers masked showed only data-driven changes).
- Verified: `python verify.py` passed **217 Python** and **71 JavaScript** tests and lint.

## 2026-10-11 — Typed per-drill request models

- Added `drill_params.py`: one Pydantic model per scorer (putting, distance ladder, range,
  collection, golf), each declaring exactly the fields its session receives. Shared fields
  (equipment choice, demo, handedness, Stimp, distance metric) are declared once in mixins.
- `PracticeParams`, the POST /api/practice body, is now derived as the union with unknown keys
  rejected. A conflicting redefinition of a shared field fails at import. Its JSON schema
  (48 fields, bounds, defaults, required) was compared with the removed hand-written model and
  is identical.
- `drills.create()` validates with the drill's own model and passes the typed object to its
  factory, replacing the field-name filtering. Direct service calls (scripts, tests) now get the
  API's defaults and bounds instead of each constructor's own defaults.
- Tests (`tests/test_drills.py`): each scorer's fields equal what its session receives; the
  envelope is the union and rejects unknown keys; conflicts are rejected; bounds/defaults apply
  and other drills' fields are ignored; a direct launch equals an API launch.
- Verified: `python verify.py` passed **217 Python** and **67 JavaScript** tests and lint.

## 2026-10-11 — Frozen per-version migrations

- `migrations.py` became the `migrations/` package:
  - `sql/0001_base.sql` (schema 1, which Store creates for a new database) and
    `sql/0002…0005_*.sql` hold each step's DDL, rendered exactly as the code executed it
    (generated views from `SOURCE_FIELDS` and the analysis query included). The script asserted
    each file equals the previous constant.
  - `v0002…v0005_*.py` hold each step's prepare/backfill/reconcile code, with frozen copies of
    the backfill entry functions.
  - `__init__.py` holds the runner and `STEPS`.
- Removed the now-duplicated `DDL`/`SCHEMA` constants, the two DDL-only column constants and the
  moved `backfill()` functions from `storage.py` and the schema modules, so each schema
  version's DDL exists once. `storage.SCHEMA` loads the frozen base file.
- Tests: `tests/test_migrations.py` pins the SHA-256 (LF-normalized) of every released step and
  SQL file, requires every file to be pinned and each step to target `version + 1`, and checks
  the base schema loads from its file. `pyproject.toml` excludes released steps from formatting.
  The existing v1→v5 upgrade and rollback tests (now patching the frozen v2 backfill) exercise
  the real steps.
- Limit: backfills call shared writers (`write_source`, `write_session`, `save_collection`, …).
  A future change to one of them that breaks an old step fails the v1 upgrade test; the fix is
  to freeze a copy of the old writer inside that step.
- Verified: `python verify.py` passed **212 Python** and **67 JavaScript** tests and lint.

## 2026-10-11 — Isolated instances leave web_runtime.json alone

- Fixed the follow-up from the browser QA entry. `web_app.main()` wrote `web_runtime.json` for
  every instance, so an isolated QA service overwrote, then deleted, the record that `launch_web.py`
  and Stop TraceLoft.cmd use to find the real service. `runtime_file()` now returns None when
  `GOLFDATA_DATABASE` is set. A second owner of the default database still cannot start (the
  service lease rejects it before the file is written).
- Tests (`tests/test_launch_web.py`): an isolated instance leaves an existing record untouched
  while running and after exit; the default-database service writes its record and removes it.

## 2026-10-11 — Browser QA of the review changes (isolated instance)

- Ran an isolated service (separate database, input 9901, HTTP 8799) from a scratchpad script that
  calls `create_app` directly. Running `web_app.py` would have overwritten and then deleted the
  repository's `web_runtime.json`, which belongs to the user's real service.
- Checked at 1366×1024:
  - Practice selector from the drill registry; `#setup/pace` → Launch → runner with the
    "Waiting for source" warning.
  - Two synthetic Open Connect putts arrived through live revisions (2/10, latest putt, In window).
  - The abandon confirmation markup (`html` helper) was byte-exact, and confirm returned to Practice.
  - Sessions list (threaded snapshot read), Delete → notice with Undo → restored.
  - Relay → Back up database (verified snapshot path shown). The post-abandon background
    backup also produced a verified copy and manifest.
  - Analyze and Play loaded; a demo round's preview/recommendations endpoints returned 200.
- Checked at 390×844: Sessions had no horizontal overflow.
- No console errors.
- The user's real service (8765/900, PID unchanged, unfinished session) was not touched and still
  runs the previous backend until its next normal restart. The web UI files are served from the
  working tree, so its browsers load the new JavaScript; those changes need no new API.
- Not verified: physical iPad Safari/touch, and every drill/game journey (only the ones above).
- Follow-up suggestion, not implemented: `web_app.main()` writes `web_runtime.json` for any
  instance, so a second instance started with `web_app.py` clobbers the launcher's runtime file.

## 2026-10-11 — Documentation reorganized to current state

- DESIGN_PRINCIPLES.md: the ~12 sections appended after "Related documents" (some unheaded) are
  regrouped under "11. Feature-specific rules" (Range, Cross-session analysis, Play, On-course
  dispersion, Courses/artwork/imports, Ball replay, Relay, Golfers/equipment/calculations,
  Product name). A script confirmed all 299 content lines were preserved verbatim. Resolved the
  §9 contradiction: forwarding defaults to Off and the saved Relay choice is restored on restart
  (matches D48, the Relay section and the code).
- NAVIGATION.md: the current map, screens, shared navigation and transition tables now come first.
  They are corrected for the Capture→Relay change (Relay row, Export CSV/Back up database on Relay,
  "TraceLoft home", every current `#setup/<drill>` route from `web/navigation.js`, `#play/import`),
  and the obsolete Start/Stop capture row is removed. Feature path notes follow under topical
  headings. Dated verification evidence, the removed Capture/VDD screen and the retired
  fictional-hole library moved to a final "Verification history" section. A script listed every
  line not carried verbatim; all were old dated headings or the intended corrections.
- README.md: schema 2/3/5 history notes merged into one current storage section; course
  paragraphs grouped under Play; tooling, snapshot reads and CLAUDE.md referenced. Fixed a stale
  claim that the redesign plan still tracks users and relational equipment (implemented in schema 3).
- BACKLOG: the architecture item records today's completed work and what remains.
- Checks: relative links in the edited documents resolve. Documentation only; no application
  behavior changed.

## 2026-10-11 — Escape-by-default HTML templates

- Added an `html` template tag and `raw()` to `web/charts.js`. Interpolations are escaped unless
  they are nested `html` output or explicitly trusted; arrays join; null/undefined/false render
  nothing. The result converts to a string for `innerHTML`.
- Converted the shared notice and confirmation dialogs. `button()` now escapes its label (all
  callers pass literal text).
- Audit of the other ~70 `innerHTML` templates: the user-text sinks spot-checked (golfer, bag,
  club, cohort and course names) already used `esc()` or `textContent`. The remaining templates
  convert as they are edited.
- Prettier formats `html`-tagged templates as embedded HTML, which would change rendered
  whitespace. `.prettierrc.json` now sets `embeddedLanguageFormatting: off`; the two converted
  templates were restored to their exact markup.
- Added `tests/test_html.mjs` (escaping, nesting/raw, arrays/empty values, string conversion).

## 2026-10-11 — Drill registry (architecture stage 4, server side)

- Added `drills.py`. It holds the catalog (previously `web_service.DRILLS`), one creation factory
  per scorer (previously an if/elif chain on drill names in `create_practice`) and `restore()`
  driven by `session_kind()` (previously `distance_ladder.restore_model`).
- Documented that drill `id` and `drill` names are persisted identifiers, not copy.
- The `/api/drills` DTO is identical to the old literal (checked against git history), and scorer
  selection uses the same persisted fields, so no data migration is needed.
- Not done: typed per-drill request models and the browser feature lifecycle.
- Added `tests/test_drills.py`: a stable catalog DTO and identifiers; `session_kind` and restore
  for every scorer class; every catalog drill launching through the API and reopening with the
  same scorer and data; unknown drill names still rejected.
- Verified: `python verify.py` passed **207 Python** and **63 JavaScript** tests and lint.

## 2026-10-11 — Storage module split and table-driven migrations

- Moved the four schema upgrades out of `Store` into `migrations.py`: a `STEPS` table and one
  `_apply` runner for backup, `BEGIN IMMEDIATE`, reconciliation, report, version bump and
  rollback. Store.__init__ replaces four copy-pasted lease/upgrade blocks with one call; the
  lease is now held across consecutive steps. Reports keep their previous keys.
- Moved `export()` to `storage_export.py` (Store.export delegates) and the pre-SQLite import
  (`legacy_files`, `inspect_legacy`, `import_legacy`) to `legacy_import.py`. `storage.py` went
  from about 1,650 to 1,137 formatted lines. No schema or behavior change.
- Added `tests/test_migrations.py` (contiguous steps reach SCHEMA_VERSION; failed reconciliation
  rolls back DDL, report and version; success records a report with its backup). The existing
  v1→v5 upgrade test still covers the real steps.
- Verified: `python verify.py` passed **202 Python** and **63 JavaScript** tests and lint.
- Commit `3db186f` accidentally re-encoded this log (a PowerShell ANSI read). The follow-up commit
  restores it byte-for-byte from `5431e26` plus this entry; no other file was affected.

## 2026-10-11 — Event loop no longer waits on background database work

- Problem: exports, backups and calculation staging ran on worker threads while holding the
  single writer lock (staging for its whole selection). The event loop took that same lock for
  every live-revision check (about 3/s per tab), every state request and every shot. One long export
  could therefore freeze shot intake, WebSocket updates and all requests.
- Fix:
  - `Store.reading()` gives a private read-only WAL snapshot connection. Inside the caller's
    own write transaction it yields the writer connection, so uncommitted rows stay visible.
  - Analysis, export, backups, calculation previews/history/batches, collection analysis, the
    Sessions list and Play preview/recommendations now read from snapshots on worker threads.
    The Play endpoints copy round data on the loop first.
  - Live revisions use `PRAGMA data_version` on a separate connection
    (`Store.committed_version()`), and state requests read golfer rows the same way; neither
    takes the lock. Record counters replace the `id()`-based history fingerprint.
  - Calculation staging plans from a snapshot and re-plans under the lock only if a commit
    happened meanwhile.
  - Post-session backups (previously a full copy plus integrity check on the event loop,
    including from shot intake) run on a thread that `Store.close()` waits for.
  - The Open Connect duplicate check now reads the shared connection under its lock.
- Sessions list: other golfers' sessions are filtered in SQL, and each session is read once
  instead of twice. `read_session`/`hydrate_session` now use a fixed number of queries per
  session instead of two to four per attempt.
- Remaining: a write transaction on another thread still delays event-loop writes until it
  commits; keep writes short.
- Tests: `tests/test_concurrency.py` (reads, state, export, backup and listing complete while
  another thread holds an open write; uncommitted work is not announced; read-your-writes inside
  a transaction; the post-session backup leaves the loop free; query count is independent of
  attempt count; the Sessions list filters other golfers and reads each session once), plus
  staging snapshot/re-plan tests.
- Verified: `python verify.py` passed **199 Python** and **63 JavaScript** tests and lint.
  The first run exposed a Windows temp-cleanup race with the background backup; the store now
  joins background copies on close.

## 2026-10-11 — Atomic service mutations and legacy-path removal

- Fixed: `change_practice` restored in-memory state only for `OSError`. A `ValueError` (or any
  other error) during finish/abandon/exclude could leave the live session saying "ended" while
  SQLite did not. Every mutation now uses `GolfService._changing(session)`: one transaction, with
  the previous state restored on any exception. This replaces nine copies of the pattern.
  `_require_saved()` replaces the repeated flush-then-refuse guard; `target_range` now retries
  queued saves instead of refusing until the 5 s retry loop.
- Removed dead compatibility code: the always-false desktop capture detector and its four
  endpoint checks, the no-op `drain_worker()`, the unused no-database JSON-file service mode
  (`database=False`, `.trash` paths, legacy branches in web_app), `worker`/`displays`/
  `context_path`, and the frame/read event kinds. Scorer-level JSON saving (used by scorer unit
  tests) is unchanged. `Store._audit` is now the public `Store.audit`. The `/api/state` DTO no
  longer carries the always-empty `profiles` and `displays` keys; no browser code read them.
- Added `tests/test_service_mutations.py` (ValueError and unexpected-error rollback,
  database-write rollback within a change, target change after a queued save).
- Verified: `python verify.py` passed **192 Python** and **63 JavaScript** tests and lint.

## 2026-10-11 — One-time formatting commit

- At the user's request, formatted all Python with ruff (`6371296`) and web JS/CSS/test modules with
  prettier 3.6.2. The commit is formatting only and is listed in `.git-blame-ignore-revs`.
  Prettier leaves HTML template literals unchanged, so some JS lines remain long.
- Verified: `node --check` on every `web/*.js`; `python verify.py` passed 188 Python and 63
  JavaScript tests and lint. A real-browser smoke test follows the later behavior commits.

## 2026-10-11 — Reproducible installs, lint and verification tooling

- Added `requirements-lock.txt` (exact transitive pins from the verified venv; Setup now installs
  it), `requirements-dev.txt` (ruff 0.17.0) and `pyproject.toml` with a correctness-only lint set
  (pyflakes, syntax, likely bugs). Removed unused imports/variables. Renamed a `match` variable that
  ruff's parser rejected, and bound a demo closure variable explicitly. A flagged closure in
  `courses/refine_boulder_fairways.py` was a false positive (called within its own iteration).
- `verify.py` now finds Node from `--node`, `TRACELOFT_NODE`, PATH or Program Files. It reports a
  missing required suite as "not run" and fails, tolerates a missing git, and runs ruff when
  installed. Added `tests/test_verify.py`.
- Verified: `python verify.py` passed **188 Python**, **63 JavaScript** tests and lint.

## 2026-10-11 — CLAUDE.md and codebase review

- Added `CLAUDE.md` for Claude Code. It imports AGENTS.md and condenses DESIGN_PRINCIPLES.md,
  the module map, live-data isolation, architectural invariants and code conventions. It notes
  that the saved Relay choice is restored on restart (D48); §9 of the design principles still
  says sending stays off on startup.
- Documentation only; no application behavior changed. Checked the CLAUDE.md links and checked
  its claims against `web_service.py`, `web_app.py`, `storage.py` and `shot_input.py`. Full suites
  passed: **184 Python tests and 63 JavaScript tests**. `node` was not on this shell's PATH, so
  `verify.py` could not run as written; the suites were run directly instead.
- The maintainability/extensibility/reliability findings were reported to the user. They are not
  yet in BACKLOG.md.

## 2026-10-10 — Repeatable verification and handoff

- Added `python verify.py`: selects the project venv when present, runs Python discovery and all
  JavaScript helper/controller tests, exits nonzero on failure and writes logs plus a commit/dirty-tree
  report outside the repository by default. Manual browser checks remain explicitly separate.
  Fixed Windows cp1252 printing of Node's Unicode test markers after the first reporting run failed.
- Final end-to-end command passed: **184 Python tests and 63 JavaScript tests**. Saved report/logs
  under the external `GolfData/architecture-qa/verification` folder; tablet screenshot is also there
  (one directory above). Backend/browser behavior checks use separate synthetic data.
- Additional browser QA: restarted the isolated service, restored its same 13-shot session and
  retained the unfinished draft/caret/focus; completed it, exited and opened saved review with its
  correct identity and exits. New browser code also opened the older production service without
  console errors. Closed temporary tabs, reset viewport and stopped the isolated service.
- Automatic approval review rejected the production restart command with a policy block and no
  more specific reason. The command did not execute. Production remains on its existing process,
  port 8765/input 900, with the same unfinished 40-shot session. Backend improvements are committed
  and tested but take effect after the normal service restart. No production test shots or cleanup.
- Remaining architecture work: incremental live deltas/lazy trajectories, typed neutral feature
  registry/browser lifecycle, shared SQL selection/paged detail, frozen migrations, and prediction/
  backup latency. Keep these incremental and preserve the established integrity/design boundaries.

## 2026-10-10 — Stable expansion during live updates

- Follow-up review replaced positional detail expansion with stable section identities. When the
  first shot adds provenance details, an open cleanup-history section keeps its state rather than
  transferring it to the new section. Three interaction-state regressions passed, including the
  new insertion/count-change case. No data or navigation changes.

## 2026-10-10 — Revision notifications and browser continuity

- Added server epoch/revision stamps and protocol-2 WebSocket change notices. Idle checks do not
  reconstruct history, calculate summary or inspect trajectories. Store locking prevents announcing
  another thread's in-flight database writes. Idle sockets detect disconnection; legacy clients get
  changed-only snapshots, and new clients accept older servers during an upgrade.
- Browser controller coalesces burst requests and discards superseded revisions, old-epoch/closed
  socket responses. API action snapshots cannot replace newer state; review refresh requests have
  sequence guards. Same-session runner and ball-animation repaints preserve dirty inputs, focus,
  caret, expanded details and scroll. External modal focus stays outside the runner.
- 40 affected Python tests and all 62 JavaScript tests passed. Four new backend tests cover cheap
  idle detection, database/stamp parity, idle protocol behavior and legacy compatibility; seven new
  JavaScript tests cover races/reconnect disposal and interaction-state restoration.
- Isolated browser QA (port 8778, separate synthetic database): arrival of shots 12/13 updated latest
  feedback while retaining draft text/caret/focus/scroll and an open target modal. Saving its target
  succeeded. Reviewed 1366×1024 and 1376×1032 iPad Pro landscape plus 390×844 phone; no page overflow,
  exits remain available. Found and fixed animation-finish repaint losing drafts during this review.
- Limit: changes still fetch full state and can repaint the runner; shot deltas/lazy trajectories and
  feature update/dispose remain explicit follow-ups. User's production 40-shot range was inspected
  read-only; no production shot changes were made for testing.

## 2026-10-10 — Incremental attempt persistence

- Scorers now append the new attempt and resulting state in the existing receipt transaction.
  Typed session fields synchronize only changed leaves; corrections synchronize only changed
  attempts. A bounded revision-aware digest cache publishes only after the outer commit, so failed
  receipts/retries cannot skip writes. Immutable original payloads and outcome pins remain intact.
- Isolated SQLite trigger probe: recording attempt 100 inserts only attempt 100's fields, with zero
  field writes to attempts 1–99. Changing a target writes no attempt fields; excluding attempt 2
  updates only its inclusion and reason leaves. Cold reads, container-shape changes, rollback/retry
  and rejection of removed/reordered attempts are covered by five new storage regressions.
- Full project-venv suite: 180 Python tests passed; 55 JavaScript tests passed. Initial global-Python
  discovery lacked FastAPI, so validation was rerun in the documented project environment. No
  production database edits or restart. Remaining costs include prefix validation/digest checks on
  general corrections, collection aggregation, summary calculation and prediction during ingestion.

## 2026-10-10 — Architecture review and recalculation cache

- Reviewed the supplied findings against storage/domain persistence, recalculation and live state.
  Kept the existing service/SQLite/browser architecture and documented the six-stage improvement
  plan and safeguards. Performance claims in the review remain isolated probes, not production SLA.
- Replaced eager `setdefault` reconstruction with a lazy per-session cache in batch staging.
  A five-attempt regression now reconstructs its session once. Seven recalculation tests passed,
  including publication, pinned outcomes, interruption/recovery, missing inputs and stale guards.
  No production data writes or service restart; incremental persistence is next.

## 2026-10-10 — Future desktop and swing-video backlog

- Added future desktop packaging and shot/attempt-linked swing video, including synchronization,
  playback, file recovery and separate retention/provenance. Retain tablet access and the private
  TraceCapture boundary. No desktop/video implementation is included in the current Analyze work.
- Checked the backlog wording and Git whitespace; documentation only, no data or runtime changes.

## 2026-10-10 — Relational golfers, equipment, session state and tags

- Added schema 3, verified v2 backup, transactional backfill/evidence reconciliation and exact DTO
  reconstruction. Relational rows replace editable equipment/session JSON; frozen artifacts remain JSON.
- Added golfer creation/selection and ownership guards, equipment configurations/membership, frozen
  context/plans, typed session state and audited shot/attempt tags with Undo. Retained unknown attribution.
- Added header golfer dialog, Manage bags Specifications/Replace and Range bulk Tags controls.
- Verification: 156 Python tests and 49 JS tests passed; four new relational tests and 29 affected
  storage/equipment/migration tests passed. Isolated real-data migration reconstructed all 47 sessions
  exactly with evidence/foreign-key checks. iPad 1366×1024/phone 390×844 browser review verified golfer
  creation, spec save, demo capture, tag save/Undo, end and golfer-dialog return; fixed submission CSS
  selector caught in review. Physical iPad remains unverified. Production stays on schema 2 until the
  analysis migration and final cutover checks.

## 2026-10-10 — Readable source/derived migration, stage 1

- Released schema 2 with 18 core named source columns including reported total distance, all-report
  evidence, per-field availability/quality and explicit whole-report selection. Source total never
  falls back to an estimate; missing historic/ordinary-protocol distance remains unavailable.
  Added supplied Smash Factor normalization v2 without changing archived v1 mapping or durable
  receipt identity. Source Smash Factor and the calculated speed ratio remain separate.
- Added immutable wide derived results, specifications, source dependencies, context fingerprints,
  trajectories, analytical selections and pinned attempt results. Extracted historical flight/putting
  outcomes without recomputation or invented code lineage; appended basic source-feature calculations.
  Compatible session readers hydrate numerical fields from wide storage while retaining original
  session/equipment authority for subsequent stages. Group analyses/users/context/tags remain pending.
- Added verified pre-upgrade backup and transactional DDL/backfill with exact typed-row evidence hashes,
  count/FK reconciliation and schema rollback on failure. Owner lease protects offline upgrade/CLI
  operations; verified v1/v2 restores create new destinations. Expanded CSV includes simple one-shot
  source/one-attempt views, all reports, all calculation versions and documented row shapes.
- Verification: full Python suite 156 passed and all 49 JS tests passed. After final reader/ownership
  refinements, 60 affected storage/relay/range/preview/analysis/correction/nine-hole tests passed;
  final export/retry refinements passed 22 storage/migration tests. New tests exercise real v1 upgrade,
  interruption rollback, verified snapshot restore, unchanged outcomes, quality/zero/missingness,
  old-receipt retry, immutable versions, cross-shot FK rejection and analytical selection without
  rescoring. Existing API journeys cover recording failures, cleanup/Undo and recoverable deletion.
- Migrated two isolated snapshots; final copy retained all 1,305 shots, 2,429 observations, 32,406
  original metric rows, 47 sessions and 1,089 attempts, with every session DTO identical. Isolated
  service resumed the unfinished session, matched all eight real/demo Analyze kind reports exactly
  against original payloads, loaded all 45 non-deleted reviews and exported analysis CSV. Copied
  simulator output was disabled and input used an ephemeral port. No synthetic production shots.
- Production service was already stopped. Acquired owner lease, created verified schema-1 snapshot
  `golfdata-20261011T004824-64827405.sqlite3`, then upgraded production with exact evidence/session/
  equipment/active-session/relay metadata equality and integrity/FK checks. Backfilled 2,429 reports
  and 2,364 derived results; 1,052 physical shots have reported total, all primaries resolved.
  Started normal service on 8765/input 900: active 40-shot session and equipment match saved state.
  No original shots/sessions/outcomes were deleted or rescored. Runtime reports/backups stay outside Git.
- Updated principles, operating/SQL/relay guides, D59 and backlog with implemented versus pending
  scope. Checked Markdown links, mapping JSON and whitespace. No navigation/visual-layout changes;
  responsive JS behavior remains passing, physical iPad/live-monitor acceptance was not rerun.

## 2026-10-10 — Database redesign application impact audit

- Mapped Relay, equipment, session/drill lifecycle, range cleanup, bag mapping/gapping, wedge matrix,
  putting, Play profiles/scoring, Analyze and exports/recovery to the proposed relational schema.
  Inspected storage/service, analysis, collection UI, model and preview implementation boundaries.
- Documented compatible browser DTOs over a relational authority, typed session/outcome DDL still
  to finalize, service-owned group calculations, scoped ownership/cleanup, explicit counting modes,
  source availability and selected model/profile lineage. Flagged current Play preview filtering by
  the model constant as a compatibility change needed for analytical version switching.
- Specified compact new UI and staged implementation/cutover; marked impact planning complete in
  backlog while migration remains pending. No production data/schema writes, app changes or restart.
- Verification: checked touched Markdown local links, implementation references and Git whitespace.
  Documentation-only audit; application tests/UI checks are acceptance work for implementation.

## 2026-10-10 — Club edits during active sessions

- Read current equipment edit/selection, receipt freezing, collection grouping and existing tests.
  Confirmed rename preserves club ID and old shot names, add creates ID, remove clears a removed
  selected club, and active next-shot labels refresh transactionally after pending receipts save.
- Documented current grouping limitation: renaming to represent a replacement can pool history by
  bag/club ID. Specified distinct next-shot switch, cosmetic rename, specification change, physical
  replacement and membership removal rules for the proposed revision schema. Frozen collection
  plans do not automatically adopt new clubs; historical retagging remains explicit/audited.
- Checked document links/whitespace; documentation only, no user bag edits or service/database changes.

## 2026-10-10 — Golfer ownership and relational core

- Extended database design with local users/golfer profiles and explicit ownership of bags, clubs,
  shots, sessions, tags and group analyses. Sources remain device identities, not users. Defined
  frozen player selection, single-player backfill/ambiguous attribution, cross-user guards and
  future shared-equipment/authentication distinctions. No login feature is implied or implemented.
- Core queryable/editable entities now explicitly require relational rows/keys/columns, including
  plans, labels and scalar results. JSON remains justified for raw packet evidence, immutable model
  parameter/legacy snapshots and full versioned geometry/path artifacts. Queryable keys are exposed
  relationally; retained snapshots are not a second editable authority.
- Updated D59/backlog and migration acceptance. Checked touched document links and Git whitespace.
  Design-only changes; no production database writes, service restart, UI or application behavior change.

## 2026-10-10 — Equipment/context and group-result schema clarification

- Verified implemented storage against equipment.py, collection.py, storage.py, driving_range.py,
  analysis.py and collection UI/docs: bag catalog in metadata JSON, frozen equipment/swing labels and
  corrections in attempt/session payloads, bag-map/matrix statistics computed from session shots.
  Source club code remains separate; general custom shot tags are proposed, not implemented.
- Extended redesign with explicit bag/club revision/membership, shot context/annotation/tag events,
  collection plans, group analysis/membership, bag-map/gap/matrix results and selected equipment
  profiles. Distinguished mutable next-shot defaults from frozen shot-time assignments and scoped
  corrections. Multiple bag-local IDs must not be silently merged into a physical club.
- Group summaries freeze exact selected inputs, inclusion/context/statistical revisions and
  per-metric coverage. Tag joins cannot duplicate shots; cleanup/version changes invalidate affected
  summaries without rewriting old results or scores. Added migration requirements and readable views.
- Updated D59/backlog; checked local links and whitespace consistency. Documentation only, no
  production writes/schema changes or test/UI rerun needed.

## 2026-10-10 — Confirmed GC3 column dictionary

- The user supplied four club and thirteen ball/flight labels (17 total). Updated the design table
  with all 17 named/unit-specific nullable columns, retaining existing total distance as an additional
  optional compatibility field. No fields dropped to match the earlier count of 16.
- Distinguished source Smash Factor from a separately versioned ball-speed/club-speed calculation;
  unavailable/invalid/nonpositive club speed cannot yield that ratio. Source Smash Factor has no current
  normalized mapping, and inspected club readings are unavailable; columns do not imply ingestion.
- Updated proposal, D59 and backlog. Checked dictionary against the supplied labels, local Markdown
  links and Git whitespace. Documentation only; no schema migration, live writes or recomputation.

## 2026-10-10 — Readable database redesign proposal

- Reviewed implemented schema, mappings, model payloads and prior database design/operations.
  Opened the production SQLite file read-only (without constructing Store): schema v1, 1,305 shots,
  2,429 observations, 32,406 values, 47 sessions and 1,089 attempts at inspection. 1,089 shots have
  multiple observations; none currently occur in multiple sessions. These are inventory observations,
  not a uniqueness guarantee or post-migration reconciliation. No live writes/restart/model recalculation.
- Proposed wide optional source-metric columns and separate versioned derived results, connected by
  stable shot ID, with explicit source/model selection, input/context lineage and readable wide views.
  Existing raw/typed evidence remains preserved. Recalculation appends results and publishes analytical
  selections; it never rewrites captured values or played game outcomes. Documented additive migration,
  missingness/conflicts, retagging/exclusion dependencies, versioned CSV and backup/rollback acceptance.
- Checked official GC3 metric list and Foresight launch/flight definitions; linked primary references.
  Current ball/flight mapping has 14 fields; generic mapping adds six optional club fields with no
  available club readings in the inspected database. Requested the user's exact 16 labels; not guessed.
  Named source-reported rather than measured because provider carry/total are already calculated.
- Updated database proposal/operations, README, D59 and backlog with clear design/implementation
  status. Checked touched Markdown local links and Git whitespace consistency. Documentation only;
  app behavior/schema are unchanged, so no application suite or UI review rerun was necessary.

## 2026-10-03 — Full 18 / Front 9 / Back 9

- Added touch-sized round choices with par/yardage in setup. Freeze selected holes/totals in the
  session; Back 9 starts at 10, Front 9 ends at 9. Scorecards/review contain only selected holes.
  Sessions identify Front/Back 9; edit setup retains selection. Imports retain the single-hole flow.
- Corrected the older replay assumption that hole number equals array index + 1: completion
  snapshots now follow saved hole IDs, preserving earlier back-nine scores during correction.
- Verification: full Python suite 131 tests passed; all 42 JavaScript tests passed. New API journeys
  complete both nines on both courses, check pause/resume/persistence, final-hole Misread/recompletion,
  selected totals and invalid choices. Existing full-course and correction tests remain passing.
- Isolated browser/SQLite at 8879 verified both course totals, Back 9 starting hole 10, scorecard
  10–18, holeout → Next 11 → Misread 10, End/review selection and edit setup → Front 9 start 1.
  Checked 1376×1032 iPad setup, 1366×900 map, 1600×1000 desktop and 390×844 phone. Phone has no
  horizontal page overflow. Saved setup screenshot in design notes. No physical iPad Safari/touch
  or LAN testing; no production simulated shots.
- Updated design/navigation/decisions, course guides, SQLite operating notes, README and backlog.
  Restarted production service on 8765 to load the API additions; it was idle before restart and
  remained idle afterward. Verified live catalog and all selected-nine totals. Existing data retained.

## 2026-10-03 — Fit full courses to the wide map

- Replaced square/letterboxed camera framing with a responsive viewBox. Landscape overview trims
  peripheral scenery; green view fills the panel and stays inside registered artwork. All layers
  retain uniform world scale. Phone overview keeps the full saved frame. No course files changed.
- Automated checks cover tee/pin/playing-line visibility, aspect ratio and artwork bounds for all
  36 holes at three landscape ratios, plus legacy/narrow framing and immutable coordinates.
  Isolated browser verified Boulder overview/green at 1366×900, aligned boundary overlay and map
  center tap converting to the correct world coordinates. Saved screenshot in design notes.
- Updated the approved layout notes and design principles to replace the former letterbox behavior.

## 2026-10-03 — Retire standalone starter holes

- Removed Meadow One, Willow Cove, Pine Bend and Meadow Reach from the built-in catalog and new
  round setup. Default API/constructor rounds now use Boulder Beach; removed the obsolete browser
  fallback to Meadow One. Retained versioned loaders/artwork for existing sessions and compatibility.
- Verified 19 Python game/geometry/library tests, including the new catalog and default course.
  Isolated browser on 8879 confirms only the two full courses in Play and setup. Production data
  unchanged. Updated README, navigation and backlog.

## 2026-10-03 — Map-first Play implementation

- Implemented approved Option 1 in the Vector interface: compact hole/round scorecard, club row,
  full-width map and on-map distance/lie/next-stroke/estimated putting pace. Removed the position
  sidebar. Kept the latest result and both aim distances legible over course artwork.
- Moved dispersion settings below the map; collapsed summaries retain club, endpoint choice,
  sample/source and overlay state. The heatmap continues rendering while the disclosure is closed.
  Shot log, map options/hole guide, synthetic input and suggestions expand independently.
- Retained ordered corrections/exits, source warnings, completion pause and saved-review identity.
  Scorecard and shot log open in ended/review views; current-hole components remain distinct from
  the overall round aggregate. No backend, schema, scoring or course-geometry changes.
- Verification: all 39 JavaScript tests pass, including a regression for reviewed-hole scores versus
  round totals. Isolated service/SQLite on 8879 verified club selection, tap/pin/numeric aim, preview
  modes and source, scoring boundaries, putting units/pace, gimme finish, Misread reopening and
  gimme removal, completion/Next hole, End round and historical-hole review. Browser console clean.
- Visually checked 1366×1024 and 1376×1032 iPad landscape, reduced-height 1366×900, 1600×1000 desktop
  and 390×844 phone. Phone has no horizontal document overflow; controls wrap and map readouts move
  outside the image. Saved the actual 1376×1032 demo screenshot and approved concept in
  [design notes](designs/play-map-first/README.md). Physical iPad Safari/touch and LAN were not tested.
- Updated design principles, navigation, decisions, course operation, README and backlog. Refreshed
  the existing production tab without creating shots or changing its session. No server restart
  required. Synthetic state-changing checks remained in the isolated database.

## 2026-10-03 — Compact Play actions and club selection

- Moved Mulligan and Misread into the round header before End round, Play menu and Exit round;
  removed the Replay a shot card. Target/effect help and correction eligibility remain intact.
- Moved correction counts into the scorecard summary with expandable audit history inside it;
  legacy single-hole games show those details in their hole score panel.
- Kept bag selection in course setup. Active Play now uses a full-width club row with the setup
  bag's name; club changes and clearing retain that bag. Practice keeps its full bag selector.
- Updated design principles, navigation, course instructions, backlog and empty-preview wording.
- Verification: all 38 JavaScript tests passed. Isolated browser/SQLite service on port 8879 checked
  setup → launch, repeated club changes, clear/reload, shot tags, header Mulligan, completed-hole
  Misread reopening, ended-round correction reopening, separate counts and expandable history.
  Visual checks at 1366×1024 iPad landscape, 1600×1000 desktop and 390×844 phone found no page
  overflow; club buttons and header actions wrap on phone. Production sessions/data were untouched.

## 2026-10-03 — Boulder Beach course name

- Renamed the coastal course from Pebble Boulder to Boulder Beach in its package, generator,
  current documentation, library, setup, round heading, scorecard, attribution and session-list display.
- Retained course/artwork IDs, document paths and immutable saved rounds. A presentation alias
  shows the new name for existing snapshots; original generation prompts/screenshots remain historical.
- Verification: 38 JavaScript tests passed; direct saved-scorecard rendering/immutability check passed.
  Compared the entire course package to HEAD: only name/attribution strings changed. Running API
  and browser library/setup both show Boulder Beach with the same 18 holes, 6,801 yards and par 72.
  No service restart, database writes, new session or geometry changes needed.

## 2026-10-03 — Sheboygan Straits complete course

- Reviewed current architecture, backlog, decisions, Vector design principles/navigation and the
  supplied official Straits hole gallery. Used official Blue pars/yardages: 7,142 yd / par 72.
- Built eighteen original routes and bunker complexes, then generated eighteen independent aerials
  with the built-in image generation tool. Retained original guides, base prompt and provenance.
- Traced the finished artwork into simplified scoring polygons; adjusted tee/pin/route registration,
  rejected reviewed rock/fescue fragments and stored asset hashes. Final package has 354 scoring sand
  areas, 11–27 per hole. OpenCV/NumPy tracing runs only in a temporary design environment; the app
  keeps its existing dependencies and reads JSON/PNG. No source photography is bundled.
- Added Sheboygan Straits to Play and optional per-hole strategy disclosures. Existing round,
  equipment, dispersion, putting, scorecard, correction and saved-review behavior is reused.
- Verification: complete suite **128 Python tests passed**, followed by the expanded course suite
  **4/4 passed** (129 distinct Python cases now); **38 JavaScript tests passed**. The course tests
  play all eighteen holes, verify putting/score/persistence/delete-restore, paused/stale input,
  bunker recovery, water penalty and corrections after completion. All geometry and asset hashes pass.
- Visual QA: all eighteen finished art/boundary overlays inspected; iPad Pro landscape 1366×1024,
  desktop 1536×960 and phone 390×844 CSS viewports checked (not physical-device tests). Exercised
  selection/setup, tagged demo shot, hole completion, Next hole, Misread back to previous hole,
  active-session library guard/return, End, final-hole historical review/green zoom and Exit.
  No horizontal document overflow. QA used isolated Temp/straits-qa SQLite/input/service on 8879.
- Production restarted normally on 8765 after confirming no active practice session; input remains
  on 900. Verified new library card and all eighteen image URLs (200 image/png). No production
  synthetic shots or data migration. Course docs, design principles, navigation and backlog updated.
- Known model limits remain explicit: flat endpoint scoring, configurable lie reduction, no dune
  elevation/bunker-face collision or green slope simulation. TraceLoft/TraceCapture separation kept.


## 2026-10-03 — Independent application and direct Relay

- Created a clean sibling repository without capture/OCR code, source calibration, glyphs or the
  rēlā adapter. The private combined history remains in GolfData; TraceCapture is a separate sibling.
- Kept SQLite and existing domain behavior; added standard Open Connect TCP input on localhost:900,
  preserved raw vendor payloads, normalized ball/club fields, atomic shot/session save, stable optional
  receipt IDs and duplicate protection. Unknown units reject rather than impute measurements.
- Added direct GSPro/Infinite Tees forwarding with bounded writes, heartbeat/status responses,
  reconnect without replay and separate socket evidence versus simulator acknowledgement.
- Replaced Capture with Relay, including old-route compatibility and links from live runners. A
  single destination choice saves automatically; optional port details collapse. Public source status
  excludes raw OCR diagnostics. Applied the concurrent fixed bag rail and diagnostic-copy decisions.
- Added independent launch/setup/stop shortcuts. Normal restart preserves the unfinished session.
- Verification so far: 105 inherited Python tests passed in a fresh environment without OCR packages;
  8 new protocol/storage tests and 34 JavaScript tests passed. TraceCapture has 43 passing tests.
  Separate-process TraceCapture client → isolated TraceLoft TCP → SQLite succeeded; duplicate retry
  retained one shot. Real Infinite Tees at localhost:999 acknowledged a no-shot heartbeat directly
  with Code 200 while rēlā was closed. No real shots were sent during verification.
- Browser QA: auto-save destination, direct Infinite Tees acknowledgement, record-only mode,
  Relay/Practice navigation and 1366×1024 / 390×844 layouts without page overflow. Physical iPad
  Safari, genuine putt/full swing forwarding and production handoff recorded below when completed.

- Final handoff: verified backup at golfdata-20261003T123358-639bb4c6.sqlite3; preserved all 39
  session payloads, 2,302 raw events, session attempts and equipment catalog exactly. Integrity and
  foreign-key checks passed. No active session existed at cutover. Production now runs from this
  repository on HTTP8765/TCP900; separate TraceCapture on8768 connects with capture still stopped.
- Final regression: 113 Python tests passed together; an additional settings/lifecycle/restart test
  then passed in the 9-test Relay suite. All 34 JavaScript and 43 private acquisition tests passed.
  A first broad rerun interfered with the private idle connection because legacy test roots used900;
  isolated service roots now use ephemeral input ports. Re-run passed in 28 seconds.
- Production UI refreshed to Relay. Destination set to direct Infinite Tees with protocol response;
  no synthetic production shots. Evidence and exact cutover report remain outside Git under the
  local QA directory relay-split-20261003. iPad/phone are CSS viewport checks, not physical devices.
- The sibling repositories acquired initial commits during implementation; retained those histories
  and the existing TraceLoft origin configuration. This feature does not push. Removed ignored runtime
  files from the private repository index while preserving local files and its initial commit.

- Restart QA found and fixed Python3.12 listener shutdown waiting on an open source transport.
  Client transports now close before server.wait_closed; a connected-source regression test passes.
  Normal production restart was repeated with TraceCapture still connected, retaining the saved
  Infinite Tees destination. No replay or extra records were created.

- Final complete run: **115 Python tests passed**, plus **34 JavaScript tests**. Separate private
  acquisition suite: **43 passed**. Current public tree contains no fs_bridge/fs_ui_worker, cv2 or
  tesserocr importable module; document link targets and git whitespace checks passed.

## 2026-10-03 — Black and blue TL browser icon

- Changed the browser icon to a black background, white T and Vector cobalt blue L; preserved
  its existing monogram geometry. Versioned the favicon URL so browsers request the new asset.
- Updated the interface reference. Verified SVG parsing, palette, geometry and favicon link;
  inspected Chromium renders at 16, 32 and 64 pixels. No service or session state changed.

## 2026-10-03 — Favicon cache follow-up

- User still saw the green tab icon. Confirmed the live HTTP service serves the blue SVG and
  updated HTML with no-store headers. Added a distinct black/blue asset filename and pointed
  the favicon link to it to bypass retained browser favicon identity.
- Verified the new live asset matches the approved SVG and the live HTML references it.

## 2026-10-03 — Sim page backlog and GSPro club contract

- Logged the requested minimal Sim page: bag/club selection and shot logging, reusing storage
  and shot-time equipment tags. Navigation/session guards remain implementation work.
- Checked official GSPro Open Connect v1 and in-game UI documentation: incoming ClubData has
  club measurements, no documented club-name/selection setter; Code 201 returns Player.Club.
  Logged live verification and explicit mapping/precedence as follow-up, without claiming sync.
- Documentation-only verification: checked backlog scope, source link and git whitespace.

## 2026-10-03 — Relay improvement backlog

- Added six planned improvements from the rēlā comparison: delivery inspector, simulator club/mode
  feedback, readiness states, late club measurements, capability-aware controls and auditable estimates.
  Prioritized the inspector and feedback; connected feedback to the existing Sim page scope.
- Preserved source separation, immutable measurements, manual selection precedence and the limits of
  simulator acknowledgements. Core rēlā code is not covered by its MIT connector example license.
- Documentation-only verification: checked relative link targets, consistency with docs/RELAY.md
  and the existing Sim backlog, and git whitespace. No runtime, capture or session changes.

## 2026-10-03 — Sim page mockup and Play outcome audit

- Generated a Vector iPad-landscape concept with large club targets and shot metrics, optional
  manual outcome tags and a detailed editable log. Saved image, generation prompt and behavior notes;
  linked the concept and outcome-entry scope from the backlog. Awaiting design review.
- Reviewed Play's per-shot game_outcome construction and SQLite session/attempt persistence:
  start/destination lies, endpoint, remaining distance, penalties/concessions and resulting score
  are retained; these are internal game results, not external simulator course telemetry.
- Visually inspected the bitmap and checked document links/whitespace. Generated table targets
  still require touch sizing in implementation. No application code, routes, live data or services
  changed; no responsive/runtime test is claimed for a bitmap mockup.

## 2026-10-03 — Defer Sim and consolidate outcome research

- Marked Sim explicitly on hold until reprioritized, including the mockup, manual outcome tagging,
  club/mode following and GSPro file investigation. Cross-referenced the deferred status from design
  notes and the relay feedback item; existing Relay and Play remain unchanged.
- Captured log location/rotation, currentRound.dat as an unverified research lead, documented practice
  CSV exports, protocol limits, controlled-event validation and read-only enrichment requirements.
  Distinguished existing Play persistence from unverified external simulator results.
- Documentation-only verification: relative links exist, research URLs match the prior investigation,
  deferred statuses agree and git whitespace checks pass. No code or runtime changes.

## 2026-10-03 — Immersive 2D simulation backlog

- Added the requested browser-friendly playable courses with realistic physics and animated
  flight, bounce and roll to the existing 2D simulator entry. Recorded lightweight rendering,
  validation, immutable model/replay provenance and optional reduced-motion/skip controls.
- Marked it planned and distinguished it from the current endpoint prototype; the new goal
  supersedes the earlier relaxed realism direction. Implementation and performance targets remain open.
- Documentation verification: checked consistency with the current game architecture and whitespace.
  Concurrent course implementation files were left untouched.

## 2026-10-03 — Ball physics research foundation

- Saved the user-approved research plan and initial literature log for flight, turf contact,
  ground travel, starting lies and simulator approaches. Recorded twelve academic/experimental
  sources, official vendor material, pinned implementation references and a bounce dataset lead.
- Distinguished inspected full-text sections, abstracts, unread leads and blocked downloads;
  checked citation metadata, correction scope and the flight paper's differing runtime figures.
  Source summaries separate evidence, vendor claims, inference and proposed application.
- Audited current launch inputs and endpoint placement. Proposed a 3D trajectory with lightweight
  2D presentation, separate launch/landing lie effects, candidate model comparisons and held-out
  validation. No engine, calibrated coefficients or new physics implementation was selected.
- Documentation verification: checked local Markdown targets, source/citation consistency and
  focused Git whitespace. No model experiments, simulator injections, runtime or device tests were
  performed. Concurrent course code, artwork and documentation changes remain outside this commit.

## 2026-10-03 — Pebble Boulder full coastal course

- Delivered 18 original coastal holes with registered continuous AI aerials, editable geometry
  references and prompt provenance. Verified January 2026 Blue yardages: 6,801 yards/par 72;
  hole 15 is 392 yards. Yardage follows the route; straight-line map distance remains distinct.
- Added durable per-hole state, monotonic turns and hole-tagged attempts to the existing SQLite
  session payload. Intermediate completion pauses until Next hole; final completion ends the round.
  Paused/stale inputs stay unscored, failed saves roll back and legacy one-hole games remain intact.
- Added compact expandable scorecard, next-tee banner, completed/partial round summaries and frozen
  per-hole review. Current-hole log/score/map filter by hole; exclusions cannot erase strokes.
  Review uses that hole's distance, and saved suggestions do not imply current planning results.
- Updated operating guide, design principles, navigation, decisions, artwork references and backlog.
  Sim companion remains deferred; animated/realistic physics and additional tees remain planned.
- Verification: 118 Python tests and 36 JavaScript tests passed. New full-course API journey played
  every route, approached/putted every green and checked totals, SQLite reload, deletion/restore,
  exclusions, pause/resume, late input and rollback. Additional all-asset checks passed for PNG
  registration, hazards and Blue scorecard. Full legacy importer/game/relay regression suite passed.
- Fresh isolated browser review (HTTP 8879, separate SQLite and ephemeral input port): library/setup,
  club tagging, first-hole finish, Next hole, active guard/return, partial ending, full 18-hole saved
  review, earlier-hole selection, review exit and phone Next hole. Checked 1366x1024, 1376x1032,
  1440x900 and 390x844; no page-level horizontal overflow. Physical Safari/iPad testing remains open.
  All generated artwork was visually inspected; registered boundary overlays were sampled in Play.
- No measured sessions or private capture files changed. Verification data stays in the isolated
  temporary service. Production was idle before the planned normal service reload.
- Completed a normal reload of the idle production service on 8765; verified the new 18-hole
  catalog entry and first artwork return successfully, with no active session introduced.
  Documentation relative links and git whitespace checks pass. Saved an isolated iPad runner
  screenshot in designs/pebble-boulder/qa-ipad-round.png.


## 2026-10-03 — Mulligan and Misread corrections

- Implemented explicit newest-first correction actions for Play, including single-hole completion,
  between-hole pause, an untouched next tee, manually ended rounds and completed hole 18 in review.
  Reopening review returns to the active Play route. Another active session cannot be displaced.
- Restore frozen pre-shot position/aim/lie/score and undo associated penalties/gimmes. Advance the
  current turn to invalidate delayed inputs. Keep original readings/outcomes, overlay the correction,
  record separate counts and a timestamped audit, and remove only affected hole-completion results.
  Misreads are excluded from analysis with a `game_misread` inclusion reason; mulligans preserve
  the existing inclusion flag. Atomic SQLite rollback protects failures after a session save.
- Added touch-sized controls above the scorecard/map, visible target, expandable correction history
  and shot-log correction labels. Effective shot counts and map endpoints ignore corrected attempts;
  ordinary analysis exclusions continue to preserve game scores.
- Verification: full Python suite passed (124 tests), then the expanded correction suite passed
  (7 tests, including the additional live-mode/manual-end case). All 38 JavaScript tests passed.
  Tests cover raw evidence preservation, penalty/gimme reversal, repeated/stale requests, late shots,
  18-hole completion/recompletion, persistence, ownership/deletion/abandon guards and disk rollback.
- Isolated service/database on 8879: browser confirmed Misread after hole completion, Mulligan after
  advancing to the next tee, and Misread from final-round saved review reopening hole 18. Reviewed
  1366×1024 and 1376×1032 iPad landscape, 1440×900 desktop and 390×844 phone; no horizontal page
  overflow and correction buttons at least 48px high. Screenshot in
  [design review](designs/game-corrections/ipad-replay-controls.png).
- Updated design principles, navigation paths/guards, D50, course guide, database operations,
  README and backlog. Restarted the idle production service on 8765; state remained idle and the
  new correction API passed a validation-only route check. No production test shots were created.

## 2026-10-03 — Physics research data and benchmark preparation

- Added research pass 2 and staged R1–R6 tasks: bounce grouping, isolated flight baseline,
  held-out bounce comparisons, putting/cup validation, lie coverage and browser budgets.
- Retrieved Ferguson's 2023 thesis coefficients and validation details; inspected the bunker paper,
  Penner's putting model, Holmes' original cup experiment and pinned OpenFairway equations/tests.
  Recorded experimental domains, approximate capture behavior and simulator-regression limitations.
- Downloaded and audited Biber's 330/693-row bounce campaigns in temporary storage. Saved an original
  local-ZIP audit script and derived inventory with hashes, native units, ranges and sign counts;
  identified absent repeat labels/radius/uncertainty metadata before grouped validation.
- Verification: audit output reproduced identically and matched the committed JSON; changed-archive
  rejection passed. Checked coefficient arithmetic and visually verified the typeset coefficients
  and inconsistent restitution-ratio definition. Checked local Markdown links and focused whitespace.
- No physics fit, application integration, engine execution or real-device benchmark was performed.
  Source PDFs/CSVs and downloaded engine code remain outside the repository. Concurrent course work
  is excluded from this research commit.

## 2026-10-03 — Range and Play ball animation

- Added source-anchored side/top Range flight replay and a white/cobalt ball and tracer on Play's
  registered course map. Use OpenGolfCoach's saved estimated hang time at its original duration;
  fit its path to source carry/total when valid, with explicit estimated lateral landing and roll
  timing. Keep modeled metric tiles separate. Missing model data uses endpoint-only movement.
- Save independent flight predictions on new applied full shots in Play. Synthetic demo input now
  includes zero spin axis to exercise the model. No source/scoring changes, schema migration or
  historical backfill; replay never writes data or adds strokes.
- Shared presentation clock baselines entry/reload, preserves elapsed time through redraws, uses
  only the latest arrival in batches, supports Replay/Skip and reduced motion, and clears on route,
  hole or correction changes. Completed approach animations retain the overview before normal green
  zoom resumes. Penalty/putt paths retain the saved endpoint and authoritative final position.
- Verification: all 48 JavaScript tests and 20 game/correction Python tests passed. Added tests for
  source anchors, model hang time, missing/invalid data, hazard endpoints, putts, corrected shots,
  duplicate/batch arrivals, baselines, reduced motion and independent model persistence.
- Isolated SQLite/service at port 8879: verified range arrival, Replay/Skip, top view, saved review,
  reload baseline, Play immediate scoring, hole-out/gimme completion, Misread reopen and Next hole.
  No browser errors. Checked iPad 1366×1024 and 1376×1032, reduced-height 1366×900, desktop
  1440×900 and 390×844 phone; no page overflow, 44px controls. Physical iPad Safari and realistic
  bounce/ground physics remain unverified/not implemented. Screenshots in designs/shot-motion.
- Updated README, design principles, D54, navigation controls, database operations and backlog.
- Restarted the idle production service on 8765 to load Play prediction saving; it remained idle.
  Production test shots were not created. Stopped the isolated QA service and restored browser sizing.

## 2026-10-03 — Carry landing terrain and rollout rules

- Full shots now classify the estimated carry landing point before applying remaining rollout.
  Sand removes all roll, rough removes 75% by default and out of bounds removes 100%; rough/OB
  percentages are adjustable in round setup. Existing starting-lie reductions apply first, and
  final-position penalties retain their existing behavior. Invalid/missing carry preserves the
  original endpoint with visible feedback. Putting remains unchanged.
- Preserve raw measurements and freeze landing surface, original endpoint, estimated carry point
  and rollout adjustment in each new v2 outcome. Existing active rounds use defaults for future
  shots without rescoring earlier outcomes. Animation follows those saved points and removes the
  roll phase for sand. Source carry/total/offline and game landing/roll are visible in the shot log.
  Demo shots accept optional reported carry for deterministic landing checks.
- Verification: 31 Python landing/game/correction/nine-hole tests and all 49 JavaScript tests passed;
  frontend syntax check passed. Coverage includes bunker landings that would otherwise roll clear,
  rough roll exiting rough, OB penalties, configurable percentages, missing carry, prior lie effects,
  frozen historical outcomes, corrections and animation endpoints/timing.
- Isolated SQLite/service on 8879: launched a demo round, entered carry 364.8 yd / total 420 yd,
  verified sand landing with zero rollout, animation/Skip, raw/game log evidence, reload and Misread
  restoration. Checked iPad 1366×1024 and 1376×1032, reduced 1366×900, desktop 1440×900 and phone
  390×844; no horizontal page overflow, 48px numeric controls and no browser errors. Setup screenshot
  is in designs/landing-rollout. Physical Safari and live monitor geometry remain unverified.
- Boundary overlay review exposed an existing Boulder Beach hole 1 art/scoring offset. Logged a
  separate P1 geometry registration audit; terrain rules correctly use saved boundaries. Continuous
  terrain crossing during rollout and terrain-adjusted heatmap previews remain future work.
- Updated operating/design/storage docs, D55 and backlog. Restarted production on 8765 and compared
  the complete active practice snapshot before/after: the two-shot round was preserved exactly.
  No production test shots were created. Stopped the isolated service, closed its tab and restored
  browser sizing.

## 2026-10-03 — Finished-art boundaries across both courses

- Reviewed all 36 holes against unmodified final artwork. Boulder Beach v1 retained schematic
  guide geometry that drifted in AI rendering. Retraced tees, greens, fairways, rough/nature edges,
  50 bunkers, shoreline and four ponds; rejected tree shadows mistaken for water. Sheboygan Straits
  retained its 354 traced bunkers/water and tee/pin/scale, with refined fairway edges and the full
  lobed hole 10 green. Soft turf/surf boundaries remain simplified vectors; image perimeter is game OB.
- Published immutable v2 JSON packages and switched new-round catalog/defaults. Original v1 JSON
  and all raster assets are unchanged. Existing active/saved rounds keep frozen geometry and scores.
  Added design-only deterministic registration/render scripts, six whole-course overlay sheets,
  green detail/browser screenshots and a manifest with asset/geometry/legacy hashes and 588 approved
  pixel classification probes. Reproduction against existing v2 passed the overwrite guard.
- Verification: full Python suite 146 passed; all 49 JavaScript tests passed. New tests cover every
  current hole, probes, uniform coordinate scale, original package/asset integrity, full 18-hole
  progression on each v2 course, bunker landing/Misread and old active v1 round reload. Camera tests
  cover all 72 current/legacy holes. Full-suite testing exposed two old demo helpers that assumed
  total travel despite default 93% carry; those endpoint tests now provide explicit carry=total.
  Separate landing-rule tests continue to verify sand/rough/OB rollout behavior.
- Isolated SQLite/service on 8879: Boulder full-round setup → overview/green boundary overlays →
  visible bunker landing at carry 366.2 / total 386.2 yd → sand/zero rollout → ended review → Play
  menu; Straits Back 9 setup → hole 10 green → artwork/vector terrain toggles → ended review.
  Checked 1366×1024/1376×1032 iPad, 1366×900 reduced height, 1440×900 desktop and 390×844 phone;
  no horizontal overflow or browser errors. Physical Safari/live-monitor geometry remains unverified.
- Updated design/operation/storage/navigation docs, decision D56 and completed the P1 registration
  backlog item. Gracefully restarted production on 8765; confirmed the new v2 catalog. Current demo
  range session ID/settings were retained. Its pre-restart memory had zero shots, while SQLite held
  40 existing simulated shots; reload rehydrated those saved shots and normalized the same start
  instant to UTC. Restored its prior Driver selection through the normal API without changing the
  saved shots. No production shots were generated or deleted. Stopped QA, closed its browser tab
  and reset viewport sizing. Full review evidence: designs/course-registration/README.md.

## 2026-10-03 — Individual-hole boundary review pack

- Added `--individual --output` to the design renderer: 36 original-resolution 1774×887 boundary
  images, course/hole anchor links in an offline HTML gallery and a ZIP with the images, six sheets,
  two green details and manifest. Individual exports also show the map's artificial OB perimeter.
  Published the requested local pack in Downloads/TraceLoft-course-boundary-review (52.3 MB ZIP).
  Large generated files stay outside Git; no course, database or live-service changes.
- Verified all 36 image sizes, every gallery file/anchor link, all 46 ZIP entries and archive integrity.
  Existing overview images/manifest match committed bytes. Visually checked native Boulder hole 1
  and Straits hole 10 exports. The in-app browser blocks file URLs, so browser interaction with the
  offline gallery was not verified; its static HTML links were checked directly. Documented command
  usage, tracing/review speedups and asset-specific extraction limits. No app test rerun needed for
  this design-only export change.

## 2026-10-03 — Boulder fairways 6, 16 and 18

- User review found a missed fairway/green connection on 6 and false mowing-stripe notches on
  16/18. Replaced those three fairway perimeters with reviewed native-art control points and smooth
  closed curves. Published Boulder v3; all other surfaces, transforms, artwork, playing lines and
  yardages are unchanged. Retained immutable v1/v2, original v2 review manifest/images and frozen
  sessions. Straits remains v2. Updated new-round defaults/catalog and version-aware export tooling.
- Added design-only standard-library builder with validation/overwrite protection. Regenerated
  overview sheets and a native-resolution gallery/ZIP in Downloads/TraceLoft-course-boundary-review-v3.
  Current fixture manifest contains 598 probes, including ten additional reviewed fairway landmarks.
  Tested exact unchanged-field comparison, green-footprint containment, fixed inside/outside points
  and historical v2 hashes. Full-art revised images and app screenshot are in the refinement guide.
- Verification: 23 targeted Python registration/game/nine-hole tests passed, including complete
  rounds on both current courses, bunker stopping, corrections and frozen legacy reload. After
  adding the new landmark fixtures, eight registration/fictional-course checks passed. Both JS
  camera tests passed across all 90 current/legacy holes. v3 builder reproduced the released candidate
  identically. Isolated API completed a synthetic 18-hole round; browser reviewed 6/16/18 overlays
  at 1366×1024 with no page overflow or console warnings/errors. Physical Safari remains unverified.
- Updated principles, guides, D57, navigation/catalog note and backlog. Gracefully restarted idle
  production recording on 8765; full current demo-range snapshot (40 existing shots, selected club,
  session/settings) matched exactly before/after. No production shots were generated or deleted.
  Confirmed catalog Straits v2 / Boulder v3, stopped QA, reset viewport and closed its review tab.

## 2026-10-03 — Judges Course

- Built all 18 holes from the supplied illustrated maps and exact yardages/pars: 6,163 yd / par 72,
  Front 9 3,066/par 36, Back 9 3,097/par 36. Four later supplied photos guide the wooded parkland,
  natural lakes, layered stone banks, pale sand and autumn accents. Built-in imagegen produced 18
  original aerials; saved exact prompts/source hashes and left reference files untouched.
- Traced finished-art turf with reviewed smooth controls and seeded bunker/water contours. Retained
  55 sand regions, grass cutouts on 2/5, separate fairways on 12/15 and water on 7/8/9/15/16/17.
  Rejected paths/shore rocks as sand and lake reflections as land. Corrected hole 1's false forest
  fairway extension and placed hole 16's selected middle tee on its visible pad. Published first
  immutable package and design-only deterministic builder. Native image proportions/uniform yard
  scale are retained, including hole 9's slightly different raster aspect. Widths/tee choice remain
  approximate; flat greens, decorative banks and simplified nature are documented game limits.
- Added the course to Play/full/front/back choices and made library tee labels read actual metadata.
  Generalized registration renderer/fixtures to native image dimensions and first-version packages;
  current evidence covers all 54 holes/722 fixed probes. Existing Boulder/Straits packages and images
  remain unchanged. The same saved polygons drive scoring, optional outlines and fallback rendering.
- Verification: final full Python suite 151 passed; all 49 JavaScript tests passed after the UI change,
  with both camera tests passing again after final tee registration (108 current/legacy holes).
  Targeted journeys exercise every new hole, putting/complete round, bunker stopping, Misread recovery,
  frozen saved geometry, selected nines, supplied totals and independent cutout/water-carry landmarks.
  Builder reproduced final package identically; all 18 aerial endpoints returned HTTP 200.
- Reviewed all 18 aerials and three finished boundary sheets. Isolated SQLite/service on 8879:
  Play library → Back 9 setup → club selection → hole/green view → scoring outlines → ended review
  → hole review → Play menu. Reviewed final hole 16 tee placement in a fresh QA round and saved iPad
  screenshot. Checked 1366×1024/1376×1032 iPad, 1366×900, 1440×900 desktop and 390×844 phone;
  no horizontal overflow or browser warnings/errors. Physical Safari/live-monitor acceptance remains
  unverified. Artwork/boundary review is an adaptation, not a surveyed course reconstruction.
- Updated guides, principles, D58, navigation, backlog and shared review documentation. Reloaded
  idle production through the normal launcher: complete current session snapshot matched before/after,
  including all 40 existing shots, selected equipment and settings. Confirmed all three course choices.
  No production shots were generated/deleted. Stopped QA, closed its tab and reset viewport sizing.

## 2026-10-10 — Schema 4 SQL analyses and collection results

Implemented SQL metric/context reads, tag any/all and config filters, immutable bag/wedge cohorts, per-metric coverage, gap results and Play profile publication/staleness. Verified 19 focused Python tests (SQL parity, tag counts, ownership, configuration changes, immutable cleanup cohorts/republication plus existing analysis/collection/preview/schema tests) and all 49 JavaScript tests. Isolated migrated-copy UI checked advanced Analyze controls and empty-user state. Production remains schema 2 until final cutover.

## 2026-10-10 — Schema 5 staged recalculation and version history

- Added immutable batch inputs/results/lineage, hashed calculation specifications, incremental
  resumable outputs, current-versus-proposed coverage previews and guarded atomic publication.
  Flight, saved/alternative putting models and source comparisons are supported. Source columns,
  original attempt pins, drills and game scores remain unchanged. Added owned history CSV, filtered
  export lineage and a readable current-metrics view; documented the implemented ERD.
- Fixed empty collection fingerprint collisions and restored practice identity to SQL-backed club
  recommendations. Migrated-copy reconciliation matches all 47 session DTOs and hashes all 12 original
  evidence tables; all eight real/demo × all/full/putting/game Analyze modes match legacy reports.
  Foreign keys are clean. No production test shots or calculation publications were created.
- Focused 32 Python tests and all 49 JavaScript tests passed. Isolated Vector UI reviewed calculation
  staging/publication/history and selected bag-map publication at 1366×1024; Analyze and bag-map
  controls/tables fit 390×844 without outer horizontal overflow. Physical iPad Safari remains unverified.
  Final full suite: 170 Python tests passed in 275.569s; 49 JavaScript tests passed.
  Wedge review shows all 12 persisted cells and publication controls. Preview table is bounded and
  keyboard-scrollable; screenshot saved outside the repository. Documentation links and diff checks pass.
  Production cutover results follow below.

### Live cutover and recovery verification

- Committed feature stages: a51f6ac (relational core), 8c4cfda (SQL/cohorts), 9d080c8
  (staged calculation/version workflow). Gracefully stopped production, acquired the service lease
  and upgraded schema 2→3→4→5. Verified backups precede each transition: UTC 20261011T015002,
  015005 and 015006 in `%USERPROFILE%/GolfData/data/backups`, with matching manifests.
- Exact reconciliation: all 47 session DTOs, all 12 original evidence-table hashes, 2,429 source
  reports and 1,059 original attempt result pins unchanged. Integrity check returns ok; foreign
  keys clean. Restored the schema-2 pre-cutover snapshot to an isolated new path, verified its
  evidence and re-upgraded to schema 5 with all 47 DTOs still exact. Production was not restored.
- Normal launcher restarted localhost:8765. Entire active range DTO is identical (session
  1b8a1f0f37334e1b94700c59ec8896e6, 40 shots, unfinished); input remains 900, relay off.
  Real/demo Analyze returns 36/1,020 included attempts; no production recalculation batches exist.
  Live browser refreshed to the golfer/expanded metric/calculation interface, with no console
  warnings/errors. QA stopped, its tab closed and temporary viewport sizing reset.
- Detailed cutover, restore and test evidence is outside the repository at
  `%USERPROFILE%/GolfData/migration-final-377cff4c`. Generated QA data stayed isolated.
  Physical Safari/touch and new live launch-monitor ingestion remain unverified in this turn.
  Google Drive/off-device backup and remote authentication remain future work.
## 2026-10-10 — Analyze redesign concepts

- Proposed one shared-scope Analyze workspace with multi-metric Trends, linked Explore and named
  Compare cohorts. Documented independent units, shared dates, robust per-metric coverage, multi-club
  configurations, numerical filter semantics, transient selection versus cleanup and frozen/dynamic
  saved-view distinctions. No design preference was treated as implementation approval.
- Created an interactive conversation preview with 216 deterministic synthetic shots. Reviewed
  metric toggles/shared inspection, club selection, chart-axis changes, linked 10–15 yd offline
  filtering (26/216 matching), detail rows and updated baseline/recent boundaries. Browser reviewed
  1366×1024/390×844 with no outer horizontal overflow or console warnings/errors; physical Safari
  remains unverified. Production app/service/database and routes were unchanged.
- Added proposal links and pending backlog scope. Only documentation is committed; the conversation
  preview remains outside the repository. No production tests needed for this concept-only change.

## 2026-10-10 — Collapsible Analyze selections and filters

- Refined all three Analyze concepts with a native expandable Selections & filters drawer,
  collapsed by default. Active clubs, dates, metrics/axes and numeric constraints remain visible;
  collapsing changes layout only. Added the requirement to design principles and pending backlog.
- Browser verified mouse and keyboard disclosure, adding descent/another club and retaining five
  charts after collapse, shared session inspection and selected-club legends. Explore retains its
  10–15 yd offline selection (26/216 shots and six preview rows); Compare retains the four-session
  boundary with its summary updated. Expanded/collapsed layouts fit 1366×1024 and 390×844 without
  outer horizontal overflow. JavaScript syntax check passed; no browser warnings/errors observed.
- Conversation preview remains outside the repository. Production app, database and routes were
  unchanged; implementation remains pending. Physical iPad Safari is unverified. Preview server
  stopped, QA tab closed and temporary viewport override reset.

## 2026-10-10 — Analyze shared selection foundation

- Implemented read-only multi-club OR selection and inclusive numeric metric ranges (AND across
  dimensions) in the authoritative report query. Summaries, groups, sessions and CSV share exact
  membership. Missing values fail only predicates on their metric; invalid/nonfinite bounds reject.
- Workspace context preserves pre-range, inclusion-scoped rows and their SQL lineage for faint
  chart context. No source, inclusion, session or calculation selection is changed by filtering.
- Eleven focused Python checks passed, including SQL endpoint/CSV parity, context lineage,
  missingness, exclusions and invalid range rejection. UI integration and live cutover follow.

## 2026-10-10 — Implemented Analyze workspace

- Replaced single-metric analysis with Trends / Explore / Compare, native collapsible selections,
  multiple metrics/clubs, stable bag/club colors, configuration/intent/version separation, robust
  native-unit coverage, shared inspection, linked numeric filters and exact-query CSV exports.
- Added shot detail/review, named comparison dates/session/config/tag overrides, overlap counts,
  cohort exports and browser-local dynamic saved views. Kept source reported total, missingness,
  real/demo/inclusion identity and reviewed calculation management. No source/history changes.
- Verified 17 affected Python tests and all 55 JavaScript tests. New presentation tests cover raw
  bucket aggregation, unavailable readings, histogram-edge partitioning, configuration/version
  pairing, native deltas and stable colors. API tests cover selection/CSV/context lineage.
- Isolated synthetic service review: five panels/two clubs, numeric AND filters (11/72 selected),
  histogram bin selection, shared capture-time inspection, Save/Load/Remove dynamic views,
  comparison date-error recovery and scope/exports. Reviewed 1366×1024, 1376×1032, 1366×900 and
  390×844, expanded/collapsed controls and internal table scrolling without outer overflow.
  Fixed a queued disclosure-state issue and histogram count axes found during review.
- Updated principles, navigation, design scope, operating guide, README, D63 and backlog. Physical
  iPad Safari/touch and LAN acceptance remain unverified. Live cutover verification follows.

### Analyze live cutover

- Gracefully restarted the normal service on 8765 after committing the workspace. Exact before/after
  active-session DTO and equipment equality: session 1b8a1f0f37334e1b94700c59ec8896e6 remains unfinished
  with 40 shots. SQLite/input 900 health is ready; real full-swing selection returns 6 attempts and
  matching pre-numeric context. No new test shots or calculation publications in production.
- Reviewed a fresh live browser tab: all three views, collapsed selections, real/source identity,
  available/missing readings, no outer overflow and no console warnings/errors. Existing user tab
  could not be controlled; it needs a normal reload to load the new JavaScript. QA screenshots and
  before/after verification remain outside Git at `%USERPROFILE%/GolfData/analyze-workspace-qa`.
