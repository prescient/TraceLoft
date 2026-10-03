# TraceLoft work log

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
