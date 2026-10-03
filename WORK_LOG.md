# TraceLoft work log

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
