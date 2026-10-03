# TraceLoft / fs_bridge backlog

## Approved Vector refresh · 2026-10-02

Status: **design direction approved; implementation pending**. User approved the pure-white hybrid
mockup set in [design references and prompts](designs/future-language/README.md).

- Preserve the current app's functional layouts, all controls, data context and navigation guards.
- Use pure-white backgrounds, square panel/control edges, thin straight dividers, near-black text
  and restrained cobalt accents. Remove grey page backgrounds, shadows and rounded-card styling;
  retain circular club selectors and labeled semantic recording/warning/error colors.
- Use a consistent practical type scale across headings, controls, metrics and units; avoid the
  oversized/inconsistent editorial typography of the initial Vector concepts.
- Approved studies cover Range, Practice, Analysis, Wedge Matrix, Distance Ladder, Putting Ladder,
  bag mapping/gapping and Play. Extend shared styling to remaining screens without dropping features.
- Pending: implement shared tokens/components; correct mockup tab/corner/copy drift; verify complete
  above/below-fold functionality, live/stopped/ended/review states, exits, filters, exports, exclusions
  and bag/club controls. Check primary iPad landscape sizes, desktop, smaller tablet and phone.

The current dark studio remains implemented. Generated mockups are visual targets, not functional
or responsive acceptance evidence. Original Orbit/Aura and grey hybrid studies remain exploration history.

Started 2026-09-30. Current setup: iPad Pro → AirPlay receiver on the 3840 × 2160 VDD display →
web studio capture/SQLite. VDD uses independent calibration; the earlier half-screen AirPlay and
HDMI profiles remain preserved. See [VDD operation](docs/VDD_CAPTURE.md).

Validated 2026-09-30 (putting, AirPlay): shots 27-101 in one session, 75 of 75 sent once and read
correctly (checked against the live table and saved crops). No drop-outs; no shot # needed inferring,
including the 99 → 100 crossover.

## Shot detection review issues (2026-09-30)

### VDD follow-up (2026-10-01) — High: temporary spin dashes consume putts

- Resolved in code: readiness now requires a complete confident spin pair before advancing the detector.
  Optional flight dashes remain unavailable; zero spin remains measured zero. Estimated repair effort:
  30–60 minutes, including evidence checks and recovery verification.
- Reproduced in live receipts for Foresight shots 32, 34, 40 and 41: the detector consumed temporary
  spin placeholders, validation failed, and settled zeros became an unscored late-update log.
- Restored all four from their complete saved readings as new audited observations. Original receipts,
  measurements, attempt results and completion state remain preserved; no GSPro replay. The fixed-target
  session now retains all 14 actual putts against its original 10-putt goal.
- Verification: 114 tests pass, including delayed-spin acceptance once, either usable spin pair and
  ambiguous/missing-spin rejection. Recovery passed first on an isolated database copy, then integrity,
  immutability, chronology and idempotency checks on the repaired database. Live review shows 14 attempts;
  VDD capture restarted at the existing row without replay. A fresh post-fix putt remains to be observed.

Implementation update (2026-10-01): all seven items have code changes and automated regression
coverage. Live AirPlay and GSPro validation remains open. Estimates below are the original review
estimates, not time spent. Items 1–4
were reproduced with isolated, in-memory scenarios; items 5–6 were identified by code review, and
item 7's parser behavior was reproduced. Live capture and GSPro were not exercised in this review.
The documented 75/75 AirPlay putt result covers normal operation, not these recovery cases.

Verification: `python -B -m unittest discover -s tests -v` passes 21 tests, including local TCP
connection loss/reconnection and no replay. The stricter parser accepts all nonempty raw reads in the
existing 167-row `shots.csv`. Tests run without live capture or changes to logs/glyphs.

Implemented behavior:
- Issues 1–2: timeouts preserve the confirmed row. Forward jumps reanchor without sending only when
  row 2 is confidently parsed as n - 1 and its measurements differ from row 1. Identical or unreadable
  recovery rows still need stronger evidence; they remain logged until a suitable row appears.
- Issues 3–4: unknown shot numbers may validate; a confirmed 01 / empty-row-2 resets the session even
  when its measurements match the preceding session.
- Issue 5: connection/reconnection runs in the background; sends have a 0.1 s socket timeout.
  Offline or uncertain sends are logged as failed, never queued or replayed. Successful socket sends
  still mean transport success, not a GSPro application acknowledgment.
- Issue 6: unavailable/repeated capture frames and the first returning frame pause both visibility timers.
- Issue 7: full-cell numeric parsing rejects extra characters/precision, with supported thousands
  separators, degree signs and L/R suffixes retained. Confidence also requires successful parsing.

### 1. High — Timeout recovery can accept stale values · 4–8 hours
- After a timeout, `ShotTracker.tick()` marks the baseline unverified. `ShotTracker.update()` then
  bypasses the row-2 match through `not known`; a subsequent row with different measurements can be
  accepted even when row 2 is unrelated to the last accepted row.
- Restore evidence that the table has shifted before accepting a shot after a timeout. Check recovery
  with stale values, unrelated row 2, and a genuine next shot.
- Reference: `fs_bridge.py`, `ShotTracker.update()` / `ShotTracker.tick()`.

### 2. High — A missed shot can block every following shot · 4–8 hours
- With shot 10 accepted, observing shot 12 logs a jump but leaves the baseline at 10. Shots 13, 14,
  etc. continue to be rejected until the old sequence is restored, a new session starts successfully,
  or the bridge restarts.
- Add a recovery path for missed shots that can establish a new baseline without treating scrolling
  or club switching as a new shot. Check both a single missed shot and several missed shots.
- Reference: `fs_bridge.py`, `ShotTracker.update()` jump handling.

### 3. High — Unknown shot numbers prevent sending · 1–2 hours
- The tracker accepts an unnumbered shot, but `validate()` rejects it as `missing fs_shot` because
  `FIELDS` still marks that field required. This contradicts the documented behavior that unknown
  shot numbers stay blank while shots continue to go out.
- Separate the requirement to calibrate the shot-number region from the requirement to know its
  numeric value. Check a valid unnumbered shot and subsequent recovery to a readable number.
- Reference: `fs_bridge.py`, `FIELDS`, `validate()`, and `run()`.

### 4. High — Identical first shot can prevent a new session from starting · 2–4 hours
- Shot 01 with an empty second row bypasses the sequence check, but still requires changed measurements
  or a later row-2 change. If its measurements match the previous session's last shot, it times out
  without resetting the old baseline; subsequent shots hit the jump rejection.
- Handle a confirmed first shot of a new session independently of the previous session's measurements.
  Check identical measurements across the reset and normal detection of shot 02 afterward.
- Reference: `fs_bridge.py`, `ShotTracker.update()` first-of-session handling.

### 5. Medium — GSPro reconnection blocks detection indefinitely · 1–2 days
- A heartbeat or shot send can enter `connect()`'s unlimited retry loop on the main capture thread.
  Shots occurring during the outage are unobserved, and recovery can trigger issue 2.
- Keep capture and detection running during reconnection; define delivery and failure reporting for
  shots detected while disconnected. Check a prolonged outage and recovery.
- Reference: `fs_bridge.py`, `GSPro.connect()`, `GSPro.send()`, and `run()`.

### 6. Medium — Missing frames count toward visible-time timeouts · 2–4 hours
- When the source returns `None`, `run()` skips timer maintenance. On resumption, elapsed outage time
  can expire a pending-shot or unreadable-row timer although the table was unavailable.
- Pause visible-time timers while frames are unavailable. Check an outage longer than both timeout
  limits and verify that processing resumes without immediately giving up.
- Reference: `fs_bridge.py`, `run()` capture loop and timer handling.

### 7. Medium — Malformed numeric reads can be accepted as valid numbers · 2–4 hours
- `parse()` searches for a matching substring: decimal text `12.34` becomes `12.3`, and integer text
  `12.3` becomes `12`. Glyph confidence does not establish that the entire cell has a valid numeric
  format, and range checks may accept the resulting wrong value.
- Validate the complete cell format while retaining supported thousands separators, degree signs,
  and L/R suffixes. Check malformed strings alongside legitimate table formats.
- Reference: `fs_bridge.py`, `parse()` and `read_values()`.

Priority: address issue 1, then issue 2, then issues 3–4. The referenced 25 tracker scenario tests are
not present in this folder; move them into the project as listed under "Next up" and add these cases.

## Requested

### 1. Stacked viewer (validation panel beside the AirPlay window)
Implementation started 2026-10-01: `fs_ui.py` provides a stacked live strip, actual glyph match distances,
parsed values/cell crops, next expected shot, capture rate/signal losses, and colour-coded history with
latency. Double-click a history row for saved crops. Frames refresh at 10 Hz; reads/history update on events.
The UI moves beside the receiver and stops capture if its main window overlaps it. Live-session QA pending.

A tall, narrow viewer meant for the right half of the screen, next to the receiver, to confirm what's being
captured and decided in real time.
- Layout, top to bottom:
  - live capture strip (header + rows 1-2) with the boxes drawn
  - current state: waiting / new top row / sent / not readable / pop-up / no signal, plus the shot # it expects next
  - the last read, cell by cell: crop, parsed value, and confidence (match distance), flagging anything near the cutoff
  - history of the last N shots, colour coded (sent / logged / red), with latency
- Must never overlap the captured window (screen capture grabs anything on top of it). Place it at a
  fixed position right of the receiver. Today's viewer opens minimized when the bridge's console starts
  minimized.
- Cheap to draw. The current viewer costs ~6-10 fps of capture rate (44 vs ~50 fps without it).
  Refresh the live strip at ~10-15 Hz and the rest only when something changes.
- Nice to have: click a history row to see its saved crops (`crops/<session>/<seq>_*.png`) full size.

### 2. Control UI
Implementation started 2026-10-01: launch `Launch TraceLoft.cmd` or `python fs_ui.py`. Includes Start/Stop,
preview, GSPro on/off/address/port/status/errors, source/device/title, paired calibration profiles,
debug logging and file/folder shortcuts. Calibration and teaching open their existing interactive
windows and terminal prompts. Settings lock while a worker runs; GSPro sending starts off each launch.
Capture runs in a separate process with cooperative shutdown and a six-second fallback for blocked drivers.
Live AirPlay/HDMI and GSPro validation pending; automatic calibration and in-window teaching remain open.

One place to run the bridge without editing code or copying config files.
- GSPro: on/off (`--no-gspro` today), GSPro address/port, connection status and last error.
- Source: HDMI capture card (device index) or window capture (window title), with a live preview
  (`fs_bridge.py preview` today).
- Calibration profiles per source/device (config + glyphs pairs), so switching doesn't mean renaming files.
- Start/stop the bridge, debug logging on/off, open the log / `shots.csv` / crops folder.
- Calibrate and teach from the UI: box drawing plus row typing, or the automatic path used today
  (measured boxes + transcribed rows, see "Calibration tooling" below).
- Status: frames/s, drop-outs, last shot, latency.
- Probably combined with the stacked viewer in one app. tkinter is built in; a small local web page is
  the alternative.

### 3. Shot analysis tools (requested 2026-10-01)
Add tools to review and compare captured shots from the saved log and crops. Scope to refine with the user:
- Filter by session, club, time, and sent/validated/failed status; distinguish measurements from failed reads.
- Session/club summaries and consistency measures for ball speed, launch angles/direction, and spin.
- Trends and distributions, plus comparisons between sessions or clubs.
- Inspect outliers alongside their saved crops and confidence/validation evidence.
- Support range/simulator shot labels and scoped manual inclusion decisions, explainable automatic
  outlier flags and optional filtering of a named calibration view. Preserve genuine mishits for
  inconsistency analysis and every counted round stroke/penalty. See database proposal item 10.
- Analyze short/long/left/right misses, destination lies/hazards and costly-shot frequency. Add modeled
  strokes impact only when start/end state, penalty evidence and a suitable benchmark are available.
- Add Data cleanup: per-club outlier/distribution review; select rows/ranges/all matching filters;
  preview and apply bulk physical-club/bag/intent corrections or scoped analysis exclusions. Preserve
  original labels/readings, audit each batch, support Undo and refresh dependent analyses.
- Keep capture saving immediately; approve a reviewed analytical cohort or bag/wedge profile after
  cleanup. Show detected-outlier, confirmed-mishit and data-quality rates over time with denominators,
  review/assessment coverage and stable policy/baseline versions; separate range and sim contexts.
- Export selected shots and analysis summaries.
Analytics test data added 2026-10-02: 20 historical demo sessions / 624 shots across two dedicated
bags and eight weeks, including wedge intents, missing values and reversible cleanup examples.
[Dataset and repeatable loader](docs/ANALYTICS_RESEARCH.md).

Implemented 2026-10-02: Analyze filters by dates, sessions, bag, club, swing intent and practice type;
median/IQR trends, equipment comparisons, reported dispersion and filtered CSV. Real/demo stay separate.
Manual exclusions have denominators; automatic outlier/mishit classification, crop evidence, global
cleanup and benchmarked strokes impact remain pending. See [research and scope](docs/ANALYTICS_RESEARCH.md).

**Pending — Analyze club multi-select (requested 2026-10-02; backlog only):** the current
single-club selector limits targeted Equipment and swing comparisons. Allow selecting several
clubs together, with distinct, consistent colors and a labeled legend across comparison charts
and distributions. Keep bag/club identities and wedge swing intents separate; retain per-group
median/IQR and sample counts. Apply the selected club set consistently to summaries, session
comparisons and CSV, while respecting date, inclusion and real/demo filters. Provide clear
selected-club controls suitable for iPad touch. Do not implement until prioritized by the user.

### 4. Web-based GSPro remote (requested 2026-10-01)
Phone/tablet-friendly controls served by a local background companion on the GSPro PC. The companion
should remain available while GSPro runs, independently of whether screen scraping or shot logging is active.
- Common controls: aim left/right with fine/coarse adjustments, reset aim, select clubs, reposition
  the ball/shot where supported, mulligan/replay, camera views/flyover, green grid and putting controls.
- Intended integration: translate remote actions into GSPro keyboard commands. Verify actual key
  bindings and which actions need menus or other interaction before promising those controls.
- Test whether GSPro accepts input while unfocused. The companion can run in the background even if
  GSPro must be brought to the foreground for a command; these are separate requirements.
- Identify the GSPro window/process and confirm the input target before sending keys. Do not send
  commands into another application. Serialize commands and release held keys on disconnect/shutdown.
- Configurable bindings, connection/application status, and clear feedback when an action cannot run.
- Start/stop or tray controls for the companion; optional launch with GSPro. Phone/tablet access on
  the local network with device pairing/access control.
- Keep simulator control, scraped-shot forwarding and practice logging independently enabled.
Open: validate keyboard control on the installed GSPro version, choose initial actions, and test focus
behavior. Open Connect's documented shot/player interface does not provide these remote-control commands.

### 5. Club selector, bag mapping and multiple bags (requested 2026-10-01)

Bag mapping implemented 2026-10-02: planned clubs/sample goals, carry/total median/IQR map, gaps/overlap,
CSV, live/demo collection and shared cleanup/review. See [operation](docs/BAG_MAPPING.md). Cross-session
comparisons are available in Analyze; equipment specification revisions and GSPro following remain pending.
- Create, name, edit, duplicate and select multiple bags (e.g. gamer bag, practice bag, alternate setup).
- Define each physical club with a stable identity, display name, club type, loft and optional equipment
  notes. Map it to the corresponding GSPro club selection/code; allow several clubs of the same type.
- Select the active bag and club from the desktop app or web remote. Optionally follow GSPro's reported
  club, with a manual override and explicit selection when several physical clubs match the same code.
- Independently enable "Log practice shots" and "Send to GSPro"; allow club-labelled logging when GSPro
  is off. Keep operational/error logging separate from optional practice-shot collection.
- Capture bag/club identity at shot detection, including a name/specification snapshot so later bag
  edits do not relabel historical shots. Store whether selection was manual or followed GSPro.
- Correct labels afterward; flag warm-ups, mishits and suspect reads without deleting the original record.
- **Bag mapping session:** collect a configurable sample per club and build a distance/gapping chart
  with typical carry/total distance, dispersion and consistency. Compare clubs and bags over time.
- Filter/export analysis by bag, physical club and session. Display overlapping distances and gaps.
Open: expanded VDD now captures reported carry/total, pending numeric full-swing verification.
Implemented first step: full-swing ladder setup/live selectors, editable My bag with common clubs,
multiple named bags, per-shot name/ID/revision snapshots, shared selection and attempt CSV export.
UI follow-up implemented: three vertical quick bag tabs on the left, directly tappable smaller club
circles on the right, More bags for the complete list and Add bag in empty slots. See
`designs/club-tap-ladder-bag-column-concept.png` and actual `designs/club-tap-ladder-web.png`.
Healthy capture uses the header; only actionable recording warnings appear above tagging, and the
red Session over banner remains. Desktop, tablet and phone layout checks use isolated synthetic data.
Preserve variable club counts, names and existing shot tags; three quick bag choices are not a cap.
Switching bags clears club; earlier tags remain intact. Physical specification revisions/shared
clubs across bags, GSPro club following, historical corrections, bag mapping and landing dispersion
workflows remain proposed; captured
launch/spin/flight values alone do not establish played sim outcomes.

### 6. Wedge matrix (requested 2026-10-01)

Implemented 2026-10-02: configurable wedge/swing cells, frozen per-shot labels, robust summaries,
sample coverage, target suggestions, matrix/shot CSV and print styling. See [operation](docs/WEDGE_MATRIX.md).
Cross-session comparison is available in Analyze; historical swing-label correction remains a follow-up.
- Build a matrix of wedges from the selected bag against configurable swing lengths/feels (e.g.
  quarter, half, three-quarter, full, or clock positions). Do not assume a fixed distance for a label.
- Guide collection of several shots per cell, with the selected wedge and swing label attached to
  every shot. Mark warm-ups/mishits and retain sample counts and quality indicators.
- Summarize typical carry, variation, launch and spin for each cell; show missing or undersampled cells.
- Compare matrices across bags/sessions; retain historical club/loft details when equipment changes.
- Use the matrix to suggest club/swing combinations for a target distance, with the observed variation.
- Export/print a compact reference chart and use matrix targets in wedge ladder/random-distance drills.
Open: expanded VDD provides reported carry, pending live full-swing verification. Matrix collection,
equipment assignment and swing labels are implemented; distinguish source results from estimates
and do not invent carry from speed/launch/spin.

### 7. Practice drills and games (requested 2026-10-01)
Configurable targets, repetitions, tolerances and scoring; save results against the selected bag/club.
- **Putting ladder:** estimated-distance ascending/descending targets, tolerance zones and rounds implemented 2026-10-01. Streak/pressure scoring and actual stopping-distance collection remain follow-ups.
- **Random-distance putting / lag zones:** vary targets; track short/long bias and proximity.
- **Start-line challenge:** score measured launch direction within an angular window; show L/R bias.
- **Pace consistency:** repeat a target and score variation in measured ball speed.
- **Pressure ladder:** advance on success, lose a life or step back on a miss; optional timed rounds.
- **Putting combine:** repeatable mix of start line, short putts and distance control for progress tracking.
- **Wedge/iron distance ladder / random approaches:** use target distances and optionally the wedge matrix.
  Full-swing setup/live concepts approved and implemented 2026-10-01; references in `designs/distance-ladder-*-concept.png`:
  reported carry or total in yards, customizable rungs, shots per rung, rounds, distance window and
  ascending/descending order, persistent targets/results and yard-based CSV outcomes. Carry/total
  full-swing numeric capture still needs live verification. Manual bag/club selection and editing are
  implemented; bag mapping/matrix integration and random approaches remain proposed. This is distinct
  from the implemented estimated-distance putting ladder.
  See `docs/DISTANCE_LADDER.md` and WORK_LOG.md for actual verification.
- **Target rings:** proximity-based points for solo or multiplayer practice.
- **Beat your baseline:** compare accuracy/consistency or a drill score with a previous session.
- Putting analysis: ball-speed/launch-direction distributions, bias, trends and session comparisons;
  optionally calibrate an estimated roll-distance model for specified green speed and conditions.
Implement measured-speed/start-line activities first if outcome data is unavailable. Carry, roll distance,
proximity and holed-putt scoring require additional measured results or manual entry. Label estimates
explicitly. These are proposed activities, not implemented features; prioritize the initial set with the user.

### 8. Modern interface refresh (requested 2026-10-01)
Follow-up (2026-10-01): closer native studio layout with header navigation, separate metric/progress
cards, latest-direction gauge, rounded controls and latest-first log. Capture replaces Live dashboard.
Web migration first release (2026-10-01): FastAPI service with a responsive HTML/CSS/JavaScript studio,
modular putting setup/runner, large SVG charts, session review/exclusion and shared live state.
Local and opt-in LAN launchers open directly without pairing (user preference). Capture stays in the Python subprocess and
uses a shared Windows worker lock. Calibration/teaching remain desktop tools. 65 tests pass and browser
workflows were checked at desktop/phone widths with isolated test data. Physical putting, receiver
placement, real phone networking and GSPro end-to-end checks remain open. GSPro keyboard remote,
clubs/bags, cross-session comparisons and calibrated/pressure/random-distance drills remain follow-ups. CSV export and the provisional putting ladder are implemented.
First pass implemented 2026-10-01: dark desktop palette, modular Practice chooser/setup/session flow,
large latest-putt/progress panel, responsive pace/direction charts and a secondary log. Three design
concepts are saved in `designs/`, including a dark version of the original bright layout. The concepts
are visual targets, not a claim that every illustrated control exists. Live layout/putting QA remains open.
- Refresh the desktop interface with clearer navigation, consistent spacing/typography, modern
  controls and prominent practice feedback. Keep capture status/errors visible and preserve safe
  placement beside the receiver. Design for the current putting workflow first.
- Review the layout at the calibrated half-screen size, including scrolling and readable feedback.
- Track implementation milestones, checks and outstanding work in `WORK_LOG.md`.

Session management follow-up (2026-10-01): web runner supports abandoning a drill while preserving
its recorded putts with an Abandoned label. Sessions and review support confirmed deletion, Undo,
Recently deleted and restoration. Active sessions must be finished/abandoned before deletion;
other connected devices refresh session state. 73 regression tests pass and browser lifecycle/phone
confirmation checks pass with isolated test data.

### 9. Basic 2D golf simulator (idea requested 2026-10-01)

**Course visuals implemented 2026-10-02:** AI terrain textures inside existing Meadow One shapes,
scoring-boundary overlay, simple rendering option, map/coordinate aiming plus Aim at pin.
**Proposed real-course importer:** combine OSM geometry, georeferenced aerial imagery and course
scorecards; propose missing boundaries, review them, then AI-restyle through fixed masks. Start with
one real hole/tee set; preserve source/license metadata and immutable course versions. Multi-surface
polygons are implemented; multiple tee sets and holes require simulator extensions. [Research and pipeline](docs/COURSE_ART_AND_IMPORTS.md).
Jackson Park is the bundled, incomplete test source; no verified complete real course is published.

**Club preview implemented 2026-10-02:** selected bag/club overlays included mapping endpoints
along the current aim, with Density / Outline / Off, reported/synthetic Total and paired
OpenGolfCoach Carry / Total. Wedge swing profiles remain separate. Median/middle 50%, sample/date
provenance and cleanup counts are visible. Unadjusted spread; no future-shot probability or hazard
strategy. Five-point display minimum, small-sample warning under twenty.
[Design and verification](designs/GAME_CLUB_PREVIEW.md). Lie-adjusted clouds and frozen historical
planning replay remain future refinements. Visibility refinement: all course heatmaps now use
one bright blue with a bold, solid outline and stronger density shading.

**Score/aim refinement implemented 2026-10-02:** explicit par, played/penalty/gimme breakdown,
next stroke and ball-to-aim / aim-to-pin measurements. Confirmed 3 + 1 + 1 = 5; no scoring-rule change.

**Implemented prototype 2026-10-02:** Meadow One, one original 350-yard par four, demo/live modes,
map aiming, equipment tagging, setup sliders, endpoint lies/penalties, putting pace, round history and
bag/matrix suggestions. See [current behavior](docs/2D_GAME.md). Live geometry remains unverified;
multiple holes, obstacle strategy, calibration, detailed replay and strokes impact remain pending.

Design: a browser-based top-down course simulator under Play, using the shared
setup/runner/review lifecycle. Open Golf Sim and its FUSE engine are ruled out as too immature
for our purposes, superseding the initial FUSE selection on 2026-10-01. Use simplified gameplay
and tunable lie effects. Foresight reported carry/total/offline is now the selected full-shot source;
see [the slider and shot-flow plan](docs/2D_GAME_PLAN.md). Start with an original test hole
or a course with verified reuse permission.

Research update: [Fuse evaluation](docs/FUSE_EVALUATION.md) inspects OpenGolfSim's course metadata,
top-down map, SVG/GLB workflow, surface parameters and Stimp-based physics at a pinned source revision.
This is historical research, not a selected integration plan. Retain a touch-aimed 2D map with explicit
lie feedback and course/asset coordinate provenance. Apply configurable gameplay adjustments to
Foresight reported outcomes; simulator accuracy is not a product requirement. No external engine or third-party course data was added; the prototype uses original geometry.

- Show tee, fairway, rough, bunkers, nature/tree areas, green and hole. Display ball position, distance
  remaining, lie, aim and score; use simple map geometry rather than detailed 3D graphics. Show full-shot
  distances in yards and putting distances in feet with explicit units.
- Advance the ball once from each confirmed new shot. Do not add random dispersion to measured
  shots by default. Keep optional synthetic-shot randomness separately identified. Add explicit lie
  effects such as reduced effective travel from sand, rough and nature areas. Define penalty/recovery
  rules explicitly; preserve the underlying measured shot and label gameplay adjustments separately.
- Use captured Foresight reported carry, total and signed offline as the full-shot baseline. Verify
  total/offline geometry and live full-swing reads before endpoint placement; missing required values
  leave the ball in place. Label reported distances as modeled and adjustments as gameplay estimates.
- Add setup sliders for rough/sand travel reduction and optional extra direction variation in degrees.
  Rough 7% is the user's starting proposal; other defaults remain to be chosen. Freeze settings and
  any random draw per shot. Flat-green Stimp and a gimme radius complete the proposed controls.
- Putting: show distance to the hole and a required pace target; estimate travel from captured launch
  speed using the previously researched putting models plus surface/Stimp calibration. Label estimated
  travel and simulated holed outcomes. Define a finish/gimme window and overshoot handling. Keep a
  configurable simple flat-green model for the first release; validate it locally before relying on it.
- Recommend clubs from the selected bag's carry distributions and the wedge matrix, adjusted for lie
  and obstacles. Let the player override recommendations. Use manual club/yardage presets until bag
  mapping and wedge data exist; multiple bags remain part of the prerequisite analysis work.
- Save course/hole state, strokes, selected clubs, original measurements, simulated endpoints and
  random adjustments so a round can be reviewed. Reuse abandon/delete controls for game sessions.
- The built-in sim is the intended round-outcome source for inconsistency analysis. Emit ordered
  shot-linked before/after position/lie, targets, penalties and replay/model/randomness provenance;
  preserve original played outcomes through analytical club corrections. An external GSPro outcome
  feed is not a prerequisite. Prototype shot-linked before/after game outcomes are now saved.

Revised milestones: (1) verify Foresight full-shot result semantics/readiness; (2) one permitted course/hole
with touch aiming, explicit lies, scoring and flat-green putting; (3) measured capture integration,
saved outcomes and estimated strokes gained; (4) multiple holes, bag/wedge recommendations and replay.
The one-hole endpoint prototype and simple total-distance bag/wedge suggestions are implemented.
Physical geometry validation, extra courses and benchmarked strokes impact remain open.

2026-10-02 visual refinement complete: new Meadow One v2 uses one continuous AI aerial image,
organic water/sand/green polygons, registered scale and scoring-boundary inspection. No repeating
tiles; saved v1 rounds remain intact. Tour demo profiles are implemented: an opt-in, idempotent
Play loader adds separate synthetic bag/matrix sessions anchored to the published 2023 Tour
averages. Dispersion/rollout and partial wedges are explicitly invented. Assisted one-hole geometry
import is now implemented: OSM download/file fallback, GeoJSON polygons, scale checks, preview,
review acknowledgement, immutable library versions and round selection. Remaining: official OB/
penalty rule types, OSM relations without GeoJSON conversion, multiple tee-set selection,
imagery acquisition, boundary-constrained AI restyling, and a verified complete real course.

**Course workbench completed 2026-10-02:** draw/edit/remove surface polygons and interior cutouts,
replace the game boundary, place tee/pin, Undo and keyboard coordinates. Save/reopen revision-checked
SQLite drafts and export/import draft JSON. Incomplete geometry remains draft-only; structural and
placement checks gate publication. Original source/transform and played round versions stay intact.
[Operating process](docs/COURSE_IMPORT_WORKFLOW.md). Remaining editor refinements: zoom/pan, snapping,
per-feature provenance and revision history. Aerial registration/AI assets and verified real-hole
accuracy remain open; the Jackson Park demo is explicitly incomplete.

**Optional source candidate, noted 2026-10-02:** evaluate Golfbert for mapped course polygons,
tees and scorecards. [Research notes](docs/GOLFBERT_EVALUATION.md) include pricing and the free
Riverbend sample. Resolve local caching, historical-round/backup retention, distribution and
AI-artwork permissions before adopting it. No integration or subscription selected; existing
importer work and priorities are unchanged.

**Subsequent direction, 2026-10-02:** prioritize original fictional holes instead of sourcing real
courses. Generate aerial concepts for 155/365/525-yard holes, then register scale and trace matching
terrain/scoring overlays. [Artwork and implementation](designs/fictional-holes/README.md).
**Completed:** all three are selectable single-hole rounds with registered artwork, traced scoring
surfaces, bag/club heatmaps, aiming, demo/live setup, penalties, putting and saved reviews. Verified
with isolated API/browser checks. Multi-hole progression/combined scorecards and actual-device
live validation remain follow-ups.
Real-course sources/import enhancements remain optional deferred work.

### 10. SQLite storage, extensible metrics and analytical export (proposed 2026-10-01)

Status: core SQLite import/capture/practice persistence, typed registry, CSV export and verified local
backup/restore implemented; cutover and verification are tracked in WORK_LOG.md.
See [database operations](docs/DATABASE_OPERATIONS.md). Advanced analytics/equipment/cleanup/source
adapters remain open. OneDrive is not syncing; local snapshots are not off-device protection.

- Recommend SQLite owned by the Python service outside the OneDrive workspace, with structured
  shots/sessions/physical clubs/bag revisions and a versioned typed metric catalog.
- Preserve raw receipts, ambiguous/failed capture evidence, units/frames, metric definitions,
  measurement versus calculation provenance, source capabilities, profiles and model lineage.
- Create verified versioned mappings per actual export/API/capture format; research aliases do not
  establish accessible vendor integrations. Proposal examples are under `docs/data/`.
- Safely import CSV/JSON/trash without inventing measurements or losing per-shot targets, exclusions,
  original timestamps, delivery evidence or historical results. Require idempotency and reconciliation.
- Include wide shot CSV, long metric CSV and session-attempt CSV in the first storage release; add
  cross-session/date/club/bag filters and summary exports with sample counts and inclusion policies.
- Add consistent backup/restore, a configurable external destination, schema-migration protection and
  isolated crash/disk-full/concurrent-read verification. Keep crop/training lifecycle separate.
- Add versioned inclusion policies, metric/shot/session-scoped decisions and outlier runs/flags with
  review/override history. Default to flagging; opt-in filtering never erases measured shots or changes
  round scores. Compare typical calibration results with all-valid inconsistency results.
- Preserve ordered round/hole events, aims, start/end position and lie, penalties, recoveries and
  mulligans from the planned built-in sim. Miss maps use its event state; estimated strokes cost also
  needs benchmark lineage. Keep simulated outcomes separate from captured launch measurements.
- Add immutable course revisions, holes/waypoints, semantic surface geometry and asset/import
  provenance. Pin rounds to played layouts; layout edits must not move historical shot endpoints.
  See [the Fuse evaluation](docs/FUSE_EVALUATION.md) for the proposed course contract and import checks.
- Add atomic versioned cleanup batches/items and draft/approved analytical cohort revisions for
  per-club outlier review, bulk reassignment/exclusion and Undo. Preserve original assignments and
  invalidate affected summaries/detector baselines without rewriting played simulator outcomes.
- Persist/export rates with unique-shot numerators, eligible assessed/reviewed denominators, coverage,
  reason breakdowns and fixed/adaptive baseline identity. A cleanup-induced rate drop is not evidence
  of golfing improvement; allow comparable historical recomputation under one versioned policy.
- Implement the storage/import/export foundation before advanced analytics; additional source adapters,
  equipment analysis and putting models remain staged follow-ups. The user authorized migration on
  2026-10-01; preserve original source files and verify restoration/reconciliation before cutover.

### 11. Google Drive database backups (requested after migration, 2026-10-01)

Status: follow-up design; no Drive connection/upload or scheduled job yet.

- Upload completed, verified SQLite snapshots and SHA-256 manifests to a chosen private Drive folder.
  Keep the live database/WAL local; cloud sync is not the database writer or replication mechanism.
- Select account/folder, authentication, schedule and retention; retry uploads idempotently and report
  local-only, pending, failed or remotely verified backup status distinctly.
- Download and restore a remote snapshot into isolation before claiming off-device recovery works.
  Plan training archives/configuration protection separately. See database operations for the proposal.

### 12. Driving range in Practice (implemented foundation 2026-10-01)

- Implemented open-ended range, optional carry target/window, compact bags/direct club buttons,
  latest-shot feedback, carry/total scatter, linked model side flight and shot-shape/club statistics.
- OpenGolfCoach 0.3.0 estimates are versioned and independent of reported Foresight outcomes;
  missing inputs/model failures preserve recorded shots. Carry and total plot semantics are explicit.
- Implemented session-scoped filters, selection, bulk retag/exclude/include/remove/restore,
  reasons/audit/Undo, original-tag preservation and filtered CSV with provenance.
- Added dedicated Demo ranges with one/ten-shot generation, visible synthetic labels and session
  filtering. Recoverable deletion removes demo sessions from the normal list; no permanent purge.
- See [operation](docs/DRIVING_RANGE.md), [implementation checklist](docs/RANGE_IMPLEMENTATION.md)
  and [broader feature research](docs/DRIVING_RANGE_PLAN.md).
- Pending acceptance: physical full-swing OCR, offline coordinate definitions and paired model vs
  Foresight comparison. Synthetic verification does not establish accuracy or live source readiness.
- Club-colored scatter dots, plotted-club/count legend and Side/Top flight profile implemented
  2026-10-02. Top view uses stored airborne trajectories and labels independent axis scaling.
- Club snapshot now sits above Shot workspace and shows median/IQR plus per-metric counts for
  reported carry, total, absolute offline, vertical launch and descent (2026-10-02). Missing readings
  stay unavailable; filtered included cohorts and corrected club assignments drive summaries.
- Latest/inspected shot bar includes reported total spin, vertical launch and descent (2026-10-02).
  Primary design target is 13-inch / 12.9-inch iPad Pro landscape. Viewport checks passed at
  1366 × 1024 and 1376 × 1032; physical iPad Safari/touch/LAN validation remains pending.
- Additional model metric recommendations (not implemented): landing speed, explicit carry/total
  lateral values, runout and source/model comparison; see [metric review](docs/OPEN_GOLF_COACH_METRICS.md).
- Implemented per-bag/club 80% median-centered dispersion circles (2026-10-02), minimum five included
  positions, source/Carry/Total aware. Excluded dots remain visible by default with lighter club
  colors and dashed edges; excluded/removed shots never affect circles. Covariance ellipses remain
  a possible future alternative, not the current coverage definition.
- Compact dispersion legend (2026-10-02): bag/club names only; coverage, source and exclusion
  explanations moved to a hover/focus/tap info button beside the title. Dispersion plot now fills
  spare vertical card space beside the flight/shape panels, with compact stacked layouts retained.
- Follow-ons: automatic outlier review, richer normalized club trends,
  gapping/wedge matrices, random targets/challenges, environment scenarios and animated/multi-shot tracers.

### 13. Offline session history scraper (requested 2026-10-02)

Status: planned; not implemented. Import a session recorded on the iPad at the range without
TraceLoft live capture running. Open the saved Foresight session later, scroll through its shots,
and recover the full available history into TraceLoft for review, cleanup and analysis.
Ownership clarification: historical scraping is a special mode of the private Capture app in the
eventual split (item 14). Capture acquires and reconstructs the history; TraceLoft receives the imported
session for storage, review and analysis. The distributed TraceLoft app will not include the scraper.

- Start with guided scrolling through the mirrored iPad history; evaluate automatic scrolling only
  after confirming what the source app exposes. Include horizontal scrolling if metrics span columns.
- Read every available shot and metric, retain source shot order/number, units and available original
  session/date/club metadata. Keep unavailable values blank; do not assign import time as shot time.
- Stitch overlapping views without duplicating shots or merging distinct shots with identical readings.
  Detect gaps and uncertain OCR; show progress, captured count and incomplete-history warnings.
- Preview the recovered session before committing; allow bag/club assignment and bulk corrections,
  with uncertain readings flagged for review. Preserve source evidence and imported provenance.
- Make interrupted imports resumable and repeated imports idempotent using source/session identity;
  resolve ambiguous identity explicitly rather than silently merging sessions.
- Save through the existing SQLite metric mappings and retain CSV export and analysis eligibility.
  Historical imports must never forward shots to GSPro or advance an active live drill.
- Acceptance: compare a known saved session against all imported shots/metrics, including overlapping
  screens, identical consecutive shots, missing cells, partial scrolling, interruption and re-import.

Open: inspect the saved-session UI and scrolling options, available session IDs/timestamps/club tags,
and required calibration. This is historical import after an offline outing; on-iPad OCR without the
PC is not yet a selected implementation approach.

### 14. Separate Capture and TraceLoft applications (requested 2026-10-02)

Status: deferred until the final distribution-preparation phase, after the app's planned functionality
is built. Keep the current integrated setup for now; do not start separation work as a prerequisite
for other features. Eventually distribute TraceLoft independently of Foresight scraping. Capture
remains a private tool and will not be offered as part of the distributed product.

- Proposed live-shot path: **Capture app → TraceLoft → optional GSPro forwarding**. Support GSPro
  Open Connect as a compatibility input adapter, with a richer versioned TraceLoft shot contract
  internally and for our Capture app. Confirm protocol/version compatibility during design.
- Capture owns source-specific screen capture, OCR, calibration, glyph training, diagnostics and
  historical session scraping/import preparation (item 13).
  TraceLoft owns ingestion, SQLite storage, bags/clubs, practice, games, analysis and its web interface.
  TraceLoft should work with compatible shot producers without requiring capture/OCR dependencies.
- TraceLoft can act as an optional repeater to GSPro. Recording/analysis and forwarding are independent;
  make source connection, local acceptance and downstream delivery status distinct. Keep forwarding
  explicitly enabled and prevent loops, duplicate delivery and stale-shot replay after reconnects.
  GSPro disconnection must not block local recording/analysis; acknowledge local persistence separately
  from downstream receipt and never automatically replay accumulated shots into a round.
- Define acknowledgments, responses, connection ownership, port configuration, retries and source/shot
  identity across both hops. Preserve the original payload, units and provenance in metric mappings.
  Preserve total distance, offline, descent, apex, curve, hang time and equipment/session metadata
  through the richer contract rather than restricting storage to the Open Connect field set.
  Handle readiness, heartbeats and returning player/club/handedness messages explicitly; define
  precedence between GSPro club context and manual TraceLoft bag/club selection.
- Keep one repository initially, with shared contracts and compatibility tests. Separate application
  packages do not require separate repositories. TraceLoft distribution must omit Capture's OCR,
  calibration and scraping dependencies/assets; retain a convenient combined launcher for private use.
  Plan migration of the current integrated worker, settings and capture controls without losing sessions,
  source profiles or training backups. Preserve the current working architecture until that migration.
- Capture submits historical sessions through an explicit import path into TraceLoft's shared metric
  and storage pipeline, never through live-drill progression or GSPro forwarding. Keep simulated test
  shots distinct as well. Validate with an isolated producer/receiver harness, including restart,
  duplicate and disconnection cases, before live GSPro acceptance testing.
- When this deferred phase begins, first establish the versioned shot contract and ingestion boundary
  within the working app, then extract Capture and verify independent packaging. Preserve existing
  SQLite data, shot provenance and all supported measurements throughout.

Open: protocol capability review, ingestion contract, packaging/distribution targets and staged migration
plan. Public distribution is TraceLoft only. This item records the intended direction; it does not change
today's service ownership or launchers.

### 15. Collapsible practice categories (requested 2026-10-02)

Status: implemented 2026-10-02. Organize the Practice selector into logical expandable sections
such as **Full swing, Irons, Wedges and Putting**, keeping the growing drill list easy to scan.

- Clicking/tapping a category expands its drills/games; clicking again collapses it. Start compact
  and preserve the user's expanded category when returning from setup or review.
- Use Full swing for general range/bag work, Irons and Wedges for relevant drill presets, and Putting
  for putting activities. Iron/wedge links preserve their presets across refresh; shared drills
  reuse one implementation with category-appropriate presets rather than create duplicate modules.
- Keep Return to active session and recording/completion warnings visible outside collapsed content.
  Category expansion must not start/end sessions or discard existing setup parameters.
- Retain category → drill → parameters → launch, explicit exits and stable drill/session links.
  Update the navigation map when implemented. Use accessible expand/collapse buttons, visible focus,
  expanded-state announcements and touch targets suitable for iPad Pro landscape and phones.
- Verify expanding/collapsing, selecting a drill, cancel/back, returning to the selector, active-session
  access and responsive layouts. Keep future unimplemented activities clearly distinguished.

## Putting analysis and drills — first development priority (2026-10-01)

User now has the putting setup available. Prioritize this work ahead of the web remote, bag mapping,
wedge matrix and full-swing games. This refines Requested items 3 and 7.

Implementation update (2026-10-01): first version of steps 1–2 is implemented in the Putting practice
tab: persistent sessions, configurable pace/start-line/combined drills, measured feedback, per-shot
exclusion, summaries and reopening saved results. Follow-up: modular Practice chooser, parameter setup,
session view, dark styling and large responsive graphs. Random pace chooses a nonrepeating next speed
within a configurable range; historical targets and per-putt errors are retained. The web studio now
provides the same core putting workflow and shared browser state; all 65 automated tests pass. Live setup validation,
cross-session comparisons and further steps 3–5 remain open. SQLite CSV export is implemented. Distance follow-up: provisional constant-braking baseline and Fuse comparison, saved model/Stimp/outcomes, fixed distance scoring and a configurable ladder are implemented. Actual outcomes and GSPro/mat calibration remain open. See `WORK_LOG.md` for milestones.

Practice UI direction: choose drill/game → configure its parameters → launch a dedicated runner →
review saved results. Keep shared capture/session storage separate from each drill's targets/scoring.
The current chooser exposes implemented putting drills only; add new game/drill modules as they become
available rather than growing one universal settings form.

Work in this order:
1. **Putting practice sessions and analysis:** start/end a session, attach drill/target metadata to
   validated new shots, and review ball speed, horizontal launch direction and vertical launch angle.
   Show sample count, mean, spread, L/R bias and shot history. Exclude failed reads from scoring;
   retain their diagnostics. Allow warm-up/mishit flags and compare sessions. Work with GSPro off.
2. **Pace consistency and start-line drills:** configurable repetitions, target speed and speed/angular
   tolerances; immediate shot feedback and a saved session summary. Score measured speed and HLA,
   without claiming that an angular-window success means the putt was holed.
3. **Putting ladder and random-distance/lag drills:** targets, short/long bias, tolerance zones and
   optional pressure/streak scoring. Provisional estimated-distance ladder and fixed distance targets are implemented (2026-10-01), explicitly labeled as uncalibrated. Random-distance, pressure/streak, actual-distance entry and verified outcome scoring remain open. Keep measured results and estimates distinct.
4. **Distance calibration:** collect flat-green stopping distances over relevant putting speeds and
   Stimp settings. Record GSPro version, assistance settings, launch/spin inputs and conditions. Validate
   a speed-to-distance lookup/interpolation against held-out observations before using estimates in
   calibrated drills. Uncalibrated model comparison is explicitly labeled in the current release. Use a surface-specific calibration for physical practice; initial launch speed and established
   rolling speed are different quantities. Do not assume a universal square-law coefficient matches GSPro.
   Requested GSPro workflow (2026-10-01): capture repeated putts at several speeds/Stimp settings and record actual simulated stopping distances. Use flat greens, preserve version/assistance settings, flag holed outcomes as censored, fit monotonic curves and validate on held-out putts. Compare errors against both theory models; save immutable calibration identity/coverage. GSPro calibration does not validate physical mat travel. See [distance/calibration notes](docs/PUTTING_DISTANCE.md).
5. **Progress tracking and putting combine:** repeatable pace/start-line/distance rounds, baseline
   comparisons and export. Add slope/break analysis only when the necessary conditions are recorded.

First live acceptance check: run a putting session on the current setup, confirm each validated putt
is assigned once to the active drill, verify speed/direction feedback against the source display, and
reopen the saved results. Current scraped data supplies launch measurements, not final roll distance,
proximity, skid length or holed outcomes; do not invent unavailable measurements.

### Research and GSPro calibration references

Research reviewed 2026-10-01. No official published GSPro putting equation was found in the materials
searched; this is a research finding, not proof that none exists. Sources below are starting points,
not a validated implementation specification.

- [SimGolf GSPro Putting Chart (2025)](https://simgolf.club/pages/resources/gspputtingchart/GSPro_Putting_Chart_2025.pdf):
  community ball-speed/distance tables for Stimp 8–13. Useful provisional calibration data; testing
  method, simulator version and settings are not documented in the chart. Validate locally.
- [Official GSPro changelog](https://gsprogolf.com/change-log.html): documents physics and putting
  assistance changes, but does not supply the equation. Version/settings belong in calibration records.
- [Penner (2002), The physics of putting](https://www.raypenner.com/golf-putting.pdf), Canadian Journal
  of Physics: theoretical rolling motion, slopes and hole capture. Foundation for a real-green model;
  not an empirical launch-monitor study or documentation of GSPro.
- [Pope et al. (2014), The effect of skid distance on distance control in golf putting](https://shura.shu.ac.uk/8354/),
  Procedia Engineering: mechanical putting machine/high-speed camera, artificial and natural greens,
  measured skid and actual final ball position. Inform launch/skid assumptions and distance validation.
- [Richardson et al. (2018), The effect of movement variability on putting proficiency during the golf putting stroke](https://journals.sagepub.com/doi/10.1177/1747954118768234),
  International Journal of Sports Science & Coaching: eight golfers, 3.2 m putts, Quintic Ball Roll
  launch/rotation measurements. Useful measurement protocol; not a general distance equation.
- [Lee et al. (2025), Exploring putting launch monitor data using the fsQCA method: A straight twelve-foot putt](https://www.quinticballroll.com/research-papers/Exploring-putting-launch-monitor-data-using-the-fsqca-method.pdf),
  International Journal of Sports Science & Coaching: Quintic data from 52 golfers. Finishing position
  was predicted rather than physically recorded; do not use it as stopping-distance validation.
- [Hurrion et al. (2016), Speed Changes Everything](https://www.quinticballroll.com/research-papers/Quintic-Speed-Changes-Everything.pdf):
  conference paper, not a journal article; Quintic measurements of launch, spin, skid and early speed
  changes. Small sample limits generalization. Useful for distinguishing launch speed from rolling speed.

## Next up
- **2026-10-02 requested order completed:** practice categories → bag mapping/gapping → wedge matrix
  → researched cross-session analytics → basic 2D game. Next priorities should follow user review.
  Physical full-swing geometry, actual iPad Safari/touch and calibration remain verification follow-ups.
- **GSPro end to end**: install GSPro, turn on Open Connect, run without `--no-gspro`, and confirm shots,
  heartbeats, units (yards), and L/R sign conventions (HLA, spin axis, side spin) against known shots.
- **Full swings / spin**: the first sessions with real 4-5 digit spin values will put new digits in new
  positions. Check the first shots against the iPad and add training rows if any cell sits "not
  confident". Watch the spin cross-check in `validate()` (hypot(back, side) vs total, derived axis vs axis).
- **Move tests into the project**: `trackertest.py` (25 ShotTracker scenarios) and the leave-one-row-out
  reader check live in the session scratchpad. Move them to `tests/` so they survive and run with one command.

## Calibration tooling
- **Training crop backup / validation retention** (implemented 2026-10-01): existing 1,764 crop images,
  matching logs/configs/glyphs saved to a SHA-256-verified ZIP under `backups/`. Working crops retain the
  newest 25 logged-read capture sets across sessions/restarts. "Keep crop sets" is adjustable in the UI;
  0 stops new saves. CSV history stays complete. Failed/logged reads count toward the limit. Archives
  are excluded from pruning and Git. Live-session verification of ongoing retention remains pending.
- Turn the automatic calibration used today (measure text edges → boxes, transcribed rows, pooled
  frames, leave-one-row-out report) into `fs_bridge.py calibrate --auto`, instead of scratchpad scripts.
- Teaching from several frames: `teach` only takes one frame. Pooling frames/sessions was needed for
  the 10 px HDMI text.
- Save the ShotTracker state (last accepted shot # + its row image) so a restart mid-session starts
  knowing the shot #.

## Performance (small wins; most of the ~0.8 s delay is Foresight's row animation)
- Skip reading row 2 during normal running (only needed at startup). Saves ~40 ms per decision.
- Settle on 2 steady frames instead of 3 (~20 ms at 44 fps).
- Faster window capture (DXGI Desktop Duplication, e.g. `dxcam`) if 44-50 fps isn't enough. Each GDI
  grab waits for a display refresh (16.7 ms).
- Foresight's row delay grows with table size on the iPad Pro too (AirPlay run 2026-09-30, shot # → sent:
  ~0.7 s at 47 rows, 0.85 s at 64, 1.15 s at 77, 1.35 s at 90-101; it seems to level off near 100).
  The bridge's own share stays ~0.17 s. For now: start a new Foresight session every 40-50 shots.
- **Latency warning**: the bridge flags (viewer / control UI) when shot # → sent passes a set limit, e.g.
  1.0 s, and suggests a new session.

## Hardware / environment
- HDMI path (if it's ever used again): frequent drop-outs (up to 1 every 2 min, 1-55 s), worse over
  hours; the card stayed connected. Suspects: cable, USB-C adapter, heat. Swap the cable, then the adapter.
- AirPlay: no drop-outs seen yet. Keep an eye on Wi-Fi stalls; a frozen stream just looks like "no change".
- Foresight: report the table-size slowdown (old iPad: ~80-100 ms per row) with our measurements.

## Known limitations
- Window/VDD capture copies the screen, so nothing may cover the receiver (notifications included),
  and it must stay at its profile's calibrated size. VDD uses the dedicated secondary display.
- Intended behavior: a shot # that has never been readable is logged blank until one is, while shots
  still go out. Implemented by review issue 3; live validation remains pending.
- A putt identical to the last two in a row, whose update the table never shows, is logged after 10 s,
  not sent.
## VDD source and expanded Foresight table · 2026-10-01

**Implemented:** separate VDD profile, explicit secondary-display selection/guard, independent boxes
and trained glyphs at 3840 × 2077, main-display controls, Preview, calibration/teaching launchers,
optional unavailable-cell support, seven expanded flight fields in SQLite and CSV through immutable
mapping v2, and a local training-frame/transcription/config/glyph backup. Existing data is preserved.
Current calibration and isolated replay passed; see [VDD operation](docs/VDD_CAPTURE.md).

**Remaining:** verify a newly struck putt through live capture → SQLite → active drill; test numeric
flight fields with actual full swings (including nonzero L/R offline/curve, spin, unit settings and
larger numbers); verify GSPro delivery separately. Confirm provider endpoint/elevation/curve meanings
before using these fields as virtual golf outcomes or comparing providers. Exercise actual display
disconnect/move/minimize recovery; those guards have isolated tests, without disrupting the user's VDD.
## Navigation sections · 2026-10-01, updated 2026-10-02

**Implemented:** Capture → Practice → Play → Analyze → Sessions. Practice uses collapsible categories;
Play has the Meadow One prototype; Analyze has cross-session comparisons and export. Stable routes,
selected-tab identity, active-session guards and explicit exits are documented in NAVIGATION.md.

## TraceLoft rename · completed 2026-10-02

Web/desktop branding, favicon, visible messages, export filenames and named launchers now use
TraceLoft. Old launchers forward to the new names. Storage paths and internal identities stay
compatible; no data migration or capture/application separation is part of this feature.

## rēlā Other connector · 2026-10-02

**Implemented; live putting verified end to end:** optional connector DLL for the published Other API,
receiving existing ball-only Open Connect output on 127.0.0.1:922. Compilation and isolated stream,
status, rejection, duplicate and reconnect checks pass. Installed DLL beside C:\rela\rela.exe;
the existing running build initially reported Other plugin missing. After reopening it, three
no-shot heartbeats were acknowledged and live captured measurements dispatched. TraceLoft capture
now sends to 922, and rēlā reports Infinite Tees connected on 999. Existing sessions were preserved.
[Setup, probe and limits](integrations/rela/README.md).

Infinite Tees displayed 4.4 mph / -0.90° HLA / 0° VLA matching captured shot 19, with 8.54 ft simulated
total roll. Putting dispatch is verified after Force Putting; interpolation and HLA clamp are off.

**Remaining:** verify a genuine full swing and sparse spin/carry handling downstream. The host's
non-nullable ball contract cannot represent missing spin/carry
separately from zero. Future work: simulator acknowledgements, return club/mode context, configurable
input port, richer unit/club support and cross-reconnect identity if the sender gains retries.
This adapter does not begin the deferred Capture/TraceLoft application separation.
