# TraceLoft work log

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
