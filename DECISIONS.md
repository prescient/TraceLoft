# TraceLoft architecture decisions

## D78 — The golf laptop replaces the iPad as the primary screen (2026-10-17)

The user retired the iPad requirement: shots read from the iPad come in through TraceCapture's
table import (D65), and elsewhere the user brings a golf laptop. This opens the way to a normal
Windows app (BACKLOG: one installable app).
- Primary target: the Windows laptop, TraceLoft in its own window; layouts are checked at CSS
  1536×864, 1280×720 and 1920×1080 (DESIGN_PRINCIPLES §8). Tablets and phones are best-effort.
- The service keeps serving the UI on localhost; LAN access (`--lan`) and remote shot input (D66)
  stay as options, not requirements.
- Earlier iPad verification records in WORK_LOG, NAVIGATION and designs/ are history and stay as
  written.

## D77 — One quiet, persistent GSPro connection (2026-10-17)

In the live test, GSPro stopped answering TraceLoft-next until GSPro Connect was restarted, after
which every shot was acknowledged in 18–195 ms. GSPro Connect serves one client, and its slot can jam
when a client keeps reconnecting. TraceLoft's relay was doing exactly that: a readiness heartbeat
every 5 s, and a fresh connection whenever GSPro stayed quiet (D74). Working GSPro connectors hold
one connection and stay quiet between shots. Replaces the reconnect-once rule in D74.
- **One connection.** The relay reconnects only when the connection really closes or fails. Waits
  between attempts grow 2 → 5 → 10 → 30 s and start over once a connection gets a reply. Silence
  never closes the connection.
- **Heartbeats only on connect and when readiness changes**, not on a timer. A dead link is found
  by TCP keepalive (idle 30 s, 4 probes 5 s apart, about 50 s), which GSPro Connect never sees.
- **Silence is reported, not "fixed".** After 5 s without a reply, the connection stays open, the
  shot is marked "No reply", and the alert says to put GSPro on the range or in a round and, if it
  is, to choose Settings → System → Reset GSPro Connect (or restart GSPro Connect).
- **Reply counts.** The Relay page shows this run's simulator replies by code (`reply_codes`).
- GSPro 2026 answers a shot with "200 Club & Ball Data received" ("200 Ball Data received" without
  club data) and then "202 GSPro ready". The player's club in GSPro (Code 201) stays GSPro's own:
  Open Connect v1 gives a launch monitor no way to set it.

## D76 — Voice club selection on the PC's microphone, offline (2026-10-17)

The user asked for voice-activated club selection. The iPad reaches TraceLoft over plain http on the
LAN, where browsers refuse the microphone, so the user chose the golf PC's microphone with an
offline recognizer over HTTPS for the iPad or following GSPro's club.
- `voice.py`: Vosk (small English model, `%USERPROFILE%\GolfData\voice`) with a grammar of only the
  active bag's club phrases ("seven iron", "pitching wedge", "putter", "fifty six degree"…) plus
  `[unk]`, so other speech cannot pick a club. A phrase two clubs share is left out. Every word must be
  at least 75% confident. No audio is stored; nothing leaves the PC.
- A recognized club selects that club for the next shot, exactly like tapping it. With nothing
  running and Quick range on, it starts a Quick range with that club.
- Optional install: `vosk` and `sounddevice` are not in the lock file; without them or the model the
  Relay page says what is missing and the switch stays off. Relay → Incoming shots has the switch
  (saved as `voice.v1`), the listening state, the last phrase heard and the phrases it knows.
- The listener thread only reads a vocabulary snapshot prepared on the event loop and hands each
  recognized club back to the loop, so it never touches the session itself.

## D75 — Quick range, automatic putter tags, Relay status strip, one-tap club correction (2026-10-17)

Chosen by the user from a UI review, on branch `rela-direct`.
- **Quick range:** a live shot arriving with no drill running starts a Driving range with no target
  (`quick_range: true`, range target 0 like iPad imports), and the shot joins it unless its sender
  froze another session. With one bag, that bag is preselected (no club). It never blocks a choice:
  launching a drill or changing golfer finishes it first. Relay → Incoming shots has an on/off switch
  (on by default, saved as `quick_range.v1`). Before this, rēlā shots hit with nothing running never
  appeared in Sessions or Analyze.
- **Putts:** a shot with no measured spin (no spin value other than 0) is tagged with its bag's
  putter, for that shot only (`selection_mode: 'auto_putt'`, shown as "Putter · auto"); the chosen
  club stays selected. The bag is the shot's own or the only bag, and the putter is the club whose
  label reads as a putter (club_model). No bag or no putter means no tag. Demo, simulated and
  imported shots are left alone.
- **Relay status strip:** source · TraceLoft · simulator, each with a dot and words (connected/ready,
  recording and which session, answering/not answering/off).
- **One-tap club correction:** the club in a Range shot row or on the latest-shot card opens a picker
  of the bag's clubs; one tap applies the existing retag correction with the reason "Corrected club
  with one tap", so history, the original tag and Undo are kept.

## D74 — rēlā straight into TraceLoft: input profiles and shot confirmation (2026-10-17)

The user asked to consume rēlā directly (no TraceCapture in between), push to GSPro, and see what
was confirmed for each rēlā shot. Built on branch `rela-direct` in a separate worktree so the live
copy was untouched during a playing session.
- **Input profiles** (`source_profiles.py`, Relay → Shot source): how to read a standard Open
  Connect sender, which cannot say what it measured. `standard` stores everything as sent.
  `rela_lpi` stores only ball data plus club speed, attack angle and path as measurements. rēlā's
  face, lie, loft, closure rate, impact and carry go to `source_estimates` (D70, estimator `rela`).
  All-zero spin and exact-zero club values are "not measured". Club data without club speed is
  ignored. Senders using the TraceLoft extension (TraceCapture) classify their own values. The
  profile is recorded in the source configuration and saved in metadata (`input_profile.v1`).
- **GSPro still gets rēlā's packet as sent** (club data included): the relay already forwards the
  documented fields of the original packet.
- **Relay acknowledgement:** a reply is expected within 5 s of connecting and of each shot. On the
  first silence the relay reconnects once, then reports "isn't answering" (GSPro answers only on
  the range or in a round). *Superseded by D77: the relay no longer reconnects on silence.* The first 200 after a shot is taken as its acknowledgement, because
  GSPro replies carry no shot id.
- **Alerts:** besides the source's own (D73), TraceLoft raises "rēlā isn't connected" (profile with a
  named source and no client) and "GSPro isn't connected / answering" (TraceLoft relaying).
- **Shot confirmation** (Relay page): the last 25 shots of this run, with what was received, the
  classification of every value and why, the stored receipt (or the refusal), and the simulator
  status (acknowledged with reply and ms, no reply, rejected, not sent and why). It is kept in
  memory, not in SQLite.
- A source hanging up is logged as a disconnect, not shown as an error.
- **Input port** (user, same day): Relay → Input port sets the port TraceLoft listens on, saved as
  `input_port.v1` and applied live. The new port opens before the old one closes, so a port in use is
  refused and nothing changes. On one PC with GSPro (which holds 921), rēlā's GSPro port is set to
  TraceLoft's port, e.g. 900. `TRACELOFT_INPUT_PORT` still overrides it (test instances).

## D73 — A source's alerts under the header (2026-10-16)

Shot-path problems (rēlā not connected to TraceCapture, GSPro not answering) were visible only on
TraceCapture's page, which the golfer does not watch, and shots were lost. The user chose to show them
in TraceLoft. A source's heartbeat may carry `TraceLoft.Alerts = [{Level: error|warning, Message}]`.
TraceLoft keeps the latest heartbeat's list in `input.alerts` (at most 5, messages ≤ 300 characters,
malformed entries dropped, never refused), clears it when the source disconnects, and shows it under
the header on every page: "Not recording" (error, red) or "Attention" (warning, amber). The messages
are the source's own plain-language instructions; TraceLoft adds no source-specific logic.

## D71 — TraceLoft's estimates for every non-putt shot (2026-10-16)

Until now TraceLoft computed its own estimates only inside range-family sessions. rēlā shots arrive
with no session, so they had none. The user chose to calculate them for every shot that is not a
putt, flight and club delivery both, backfilled, stored and exported (Analyze stays session-based).
- **Per shot:** `shot_schema.shot_estimates` writes two selected results with context `shot` in
  `shot_derived_metrics`:
  - `flight`: OpenGolfCoach carry, total, offline, apex, descent, hang time and trajectory;
  - `club_delivery`: D64 face angle, face to path, dynamic loft, spin loft and the spin-axis
    cross-check (new columns, schema 7).
  Attempt results in sessions are unchanged.
- **Putt rule:** a putt is a shot tagged as a putter or with no measured spin (> 0). Ball speed
  alone does not decide it: rēlā chips at 8.5-11.5 mph spin and launch at 22-30°, and the D64
  "untagged under 25 mph" rule would call them putts. Untagged non-putts use iron weights, recorded
  as `default_non_putt`.
- **Unknowns:** no session means no golfer, club or handedness. Flight assumes right-handed (D58) and
  says so in the run parameters. Nothing is written into measurements.
- **Record first:** computed after the shot's rows, in a savepoint; a failure is logged and rolled back
  to the savepoint, never the shot. OpenGolfCoach takes about 1.5 ms per shot.
- **Schema 7** adds the club columns, rebuilds `v_shots_analysis` as one row per shot with its source
  features, `model_*` flight and `est_*` club estimates, and backfills every existing shot. The CSV
  export adds `shots_analysis.csv`. The results writer now inserts only the columns a result supplies,
  so released steps still run on older schemas.

## D70 — A source's own estimates get their own table (2026-10-16)

rēlā sends GSPro face angle, lie, loft, closure rate, impact location and carry for the Foresight
LPi, which measures none of them; rēlā's own log shows them as n/a. They are rēlā's estimates. The
user chose: never store them as TraceLoft measurements, but keep them in a table to compare with
TraceLoft's own estimates later.
- **Schema 6** adds `source_estimates`: one immutable row per observation and metric, with the
  estimator, the canonical metric key and value, and the value and unit as sent.
- **Wire:** `TraceLoft.SourceEstimates = {Estimator, Values}`, validated on intake and written in the
  shot's transaction, for accepted shots only. Allowed keys: face_angle, dynamic_lie,
  dynamic_loft, closure_rate, impact_horizontal, impact_vertical, carry (yd, stored in metres).
- `metric_values` was not reused: it allows one value per metric per observation and every row is
  read as a measurement (an estimated carry would become the reported carry).
- The three chips recorded before this change (2026-10-16 12:28) keep rēlā's face, lie and loft in
  `metric_values`; stored evidence is never rewritten.

## D69 — Simulator on another PC on the private network (2026-10-16)

GSPro runs on a separate PC on the same network (10.10.0.190), and the user asked TraceLoft to relay
shots to it. Relay → Connection details now has a **Simulator address**:
- **Allowed:** 127.0.0.1/localhost/::1 for this PC, or a private-network IP address (10.x, 172.16–31.x,
  192.168.x, IPv6 private). Host names and public addresses are refused, so the relay never resolves a
  name and never sends shots off the local network. Simulator Open Connect has no authentication.
- **Kept across destinations:** switching GSPro/Infinite Tees resets the port to that simulator's
  default but keeps the address.
- The input port only has to differ from the simulator port on this PC.
- The address reaches a delivering source in `Context.simulator` as before. TraceCapture's simulator
  link applies the same address rule (its D69). The GSPro PC must accept inbound TCP 921.

## D67 — Random distances (2026-10-15)

The user wants a range mode that asks for random distances, to practice swinging between clubs.
Their choices:
- **Its own drill** in Practice → Full swing (`random-distances`, persisted name `Random
  distances`), built on the range workspace like Bag mapping and Wedge matrix, so it has its own
  Sessions entries instead of mixing with free range practice.
- **No club hint:** only the yardage is shown; choosing the club is the practice.
- **A fixed number of targets:** the session finishes itself after that many scored shots.

Implementation choices: targets are drawn one at a time from a grid (shortest + whole steps), each
at least the minimum change from the last and never a repeat, like Random pace. Scoring is the
range's OpenGolfCoach carry within ±depth/2 (D63). A shot without carry is unscored and keeps the
target. The session's draw, not the published context, is the scoring target. Exclusion changes
the score, not the progression. See [docs/RANDOM_DISTANCES.md](docs/RANDOM_DISTANCES.md).

## D66 — Shot input from other machines (2026-10-13)

The user wants shot sources on other machines to reach TraceLoft, for example rēlā in a VM on a
laptop at another facility, over the VPN. The `--remote-input` option binds the Open Connect input to
every interface (0.0.0.0:900) instead of 127.0.0.1.
- Off by default. The LAN launchers turn it on: `Launch TraceLoft LAN.cmd` and TraceCapture's
  `launch_capture.py --lan`, which the desktop shortcut runs.
- **No authentication:** Open Connect has none, so anyone who can reach the port can send shots. The
  user accepted this, as for D62. Windows Firewall must allow inbound TCP 900. Do not port-forward 900
  to the internet; use the VPN.
- **One source at a time** still applies. While a remote source is connected, TraceCapture (or any
  other source) is refused with 503 and its receipts wait in its outbox.
- The Relay page shows "any machine", this PC's address, and the address a remote source connects
  from.
- Simulator forwarding is unchanged and stays local (until D69).

## D65 — iPad table imports (2026-10-13)

The user scrolls through the iPad app's shot table on AirPlay, and TraceCapture reads every row. The
user's choices for how those shots arrive:
- **Destination:** each import becomes its own driving range session. It is never the active drill,
  never live and never forwarded to a simulator.
- **Timestamps:** the import time.
- **Duplicates:** everything is imported. A shot matching a live capture from the last 30 days (ball
  speed, launch angles and club speed within display precision) is flagged `possible_duplicate`.
- **Club:** chosen when the import starts.

Protocol: `TraceLoft.Import = {BatchId (32 hex), Index, Count, BagId, ClubId, Label}`.
- BatchId becomes the session id, so retries and restarts find the same session.
- The session finishes once every Index from 1 to Count has arrived, in any order.
- Import shots are stored with provenance `ipad_import`, and the import's club replaces any context
  the packet carries.
- `Context.equipment_catalog` lists bags and clubs so the source can offer the choice.

## D64 — Estimated face angle, face to path, dynamic loft and spin loft (2026-10-12)

The user asked for all four, computed from the LPi's measurements with D-plane relationships
(`club_model.py`). They are estimates, stored in `club_estimates` and never written into measurements.
- Start direction ≈ k × face + (1 − k) × path; launch angle ≈ a × loft + (1 − a) × attack.
- k and a are typical per club type: driver 0.85/0.85, wood 0.80/0.82, hybrid 0.78/0.80, iron
  0.75/0.78, wedge 0.65/0.75, putter 0.90/0.90.
- Club type comes from the effective club tag (recalculated on retag); an untagged shot under 25 mph
  ball speed counts as a putt, otherwise an iron.
- Face to path is also estimated independently from the spin axis (spin loft × tan axis) as an
  off-center-strike check.
- The weights are not fitted to this player; the LPi measures no face to calibrate against.

## D63 — Range distances always from OpenGolfCoach (2026-10-12)

The user's choice: the driving range always calculates carry, total and offline with OpenGolfCoach
instead of expecting Foresight's software to report them. The iPad club table and Premier memory
report none, so range shots were recorded unscored.
- New range shots store `range_vals` and `distance_basis: opengolfcoach`. The distance window,
  statistics, club snapshot and CSV use them, labeled as estimates. Bag mapping and Wedge matrix share
  the range code and follow suit.
- Source-reported distances are the labeled fallback (`reported`) only when the model cannot run.
- Measurements in `vals` and reported columns are never filled or changed.
- Shots recorded earlier keep their reported basis and pinned outcomes.
- Range-family drills no longer ask the source for a readable carry/total column (`required_distance`).
- The model derives total spin and axis from back/side spin when only that pair is reported.
- Distance ladder and Play still use reported distances. The Play replay stays source-anchored (D54).

## D62 — Owner-allowed addresses in LAN mode (2026-10-12)

The user wants TraceLoft on a simulator screen reached through the home public IP and a Firewalla
port forward. LAN mode now also answers to the hosts listed in the local, gitignored
`allowed_hosts.txt`, one per line. Local mode is unchanged, and any name not listed is still refused
(DNS-rebinding protection). TraceLoft has no login, so anyone who can reach a listed address can view
and change data. The user accepted this risk for a personal project; authentication may come later.
A private path (VPN/Tailscale) remains the safer alternative.

## D61 — Simulator delivery by the shot source; modeled distances for memory capture (2026-10-11)

The user moved live simulator delivery into TraceCapture (its D53): TraceCapture sends each shot to
GSPro or Infinite Tees the moment ball and spin are known, without waiting for TraceLoft's database.
TraceLoft keeps the destination choice: Relay's setting is published as `Context.simulator`, and
'Off' means nothing is sent. A sender declaring `TraceLoft.SimulatorDelivery: 'source'` makes the
relay release the simulator connection and forward nothing while that sender is connected, so no shot
reaches a simulator twice; other Open Connect senders still use the relay. Putts measured without
spin (`SpinUnavailable`) are stored with null spin and play as zero spin. Foresight Premier's main
menu reports no distances, so TraceLoft models carry, total and offline with OpenGolfCoach (the
pinned `flight_model`). They are labeled estimates in the live view and never fill reported columns.
Whether drills may score on them is a separate, pending decision.

## D60 — Relational domain state and compatible DTOs (2026-10-10)

Schema 3 makes golfers, equipment/configuration/membership, contexts/tags/plans relational. Typed
path/value rows retain drill-specific settings and ordered state/corrections without editable JSON;
explicit views expose common join/filter fields. Frozen geometry/model artifacts and raw evidence
retain JSON. Reconcile every session DTO during migration. Cosmetic rename, configuration change
and physical replacement are distinct. Freeze session ownership; retain unknown inbound attribution.

## D59 — Readable source metrics and recalculable derived results (2026-10-10, stage 1 implemented)

Prefer explicit core columns for common source-reported shot metrics and a separate wide,
versioned table for TraceLoft calculations. Both reference the existing physical shot ID. Keep
multiple source reports/normalization revisions, explicit primary-source selection, immutable raw
evidence and original missingness. Provider flight calculations are source-reported, not automatically
sensor measurements. Calculations pin exact inputs, code/model/settings and relevant context;
recalculation appends a version and explicit publication selects it for analysis. Played outcomes
and scores never change through analytical recomputation. Everyday views expose units, club/bag
labels and selected methodology without long-form pivots. The user's confirmed list has 17 fields;
retain all 17 plus core reported total distance. Missing/invalid source values remain nullable;
the core total column is never filled from a model. Preserve source Smash Factor separately from
a versioned ball-speed/club-speed calculation. Supported columns do not imply available input values.
Equipment, tags and original/corrected shot intent use separate relational context/history tables.
Bag mapping and wedge matrix results are versioned multi-shot analyses with frozen member/input
revisions, not rows of per-shot derived metrics. Existing per-bag club IDs are not automatically
merged into a shared physical club; migration retains the original catalog and shot-time labels.
Add local golfer profiles and explicit ownership for equipment, shots, sessions and analysis.
Profiles do not imply authentication. Core editable/queryable data is relational; JSON remains for
original packets, model-specific snapshots and versioned artifacts. Avoid two editable authorities.
Schema 2 implements wide source/derived storage, quality/source selection, attempt pins and compatible
readers/writers/exports with verified backup and transactional backfill. Users, relational equipment/
context/plans, group analyses and full recalculation UI remain pending. See
[implemented scope](docs/SHOT_DATABASE.md) and [design/migration plan](docs/DATABASE_REDESIGN.md).

## D50 — Audited game corrections (2026-10-03)

Mulligan and Misread rewind the latest effective scored attempt, restoring its frozen pre-shot
position, aim, lie and score (including associated penalty/gimme strokes). They are separate
from analysis inclusion: a mulligan preserves the current analysis flag; a misread excludes the
reading. Original measurements and game outcomes remain immutable, with a correction overlay and
an append-only audit containing time, reason, target, previous state and restored state.

Completion is reversible: reopen the current hole, the previous hole from an untouched next tee,
or hole 18 from saved review. Corrections work newest-first; undo later shots before an earlier
shot. Remove affected completion snapshots, never earlier results, and increment the current turn
rather than reusing the historical turn. Reject stale key/turn, pending saves, abandoned/deleted
rounds and competing active session ownership. Save score, exclusion and audit atomically in
SQLite before publishing the resumed context. No schema migration or raw-shot deletion.


## D49 — Boulder Beach round package (2026-10-03)

Use the official January 2026 Blue scorecard (6,801 yards/par 72) for yardage/pars only, with
eighteen original coastal layouts and generated, registered aerials. Freeze every hole in the
SQLite session; keep per-hole result snapshots, hole-tagged attempts and a monotonic turn across
the round. Require an explicit next-tee action after intermediate completion. Paused or stale
inputs remain unscored evidence and cannot move a later hole. Preserve the existing endpoint rules,
legacy one-hole sessions and separate raw measurements from simulated outcomes.

The course is available through the existing Play/setup/session routes. Other tee sets, real-course
multi-hole imports, animated trajectories and more realistic physics remain separate backlog work.
See [delivery and operating guide](docs/PEBBLE_BOULDER.md).

## D48 — Independent application and direct Relay (2026-10-03)

TraceLoft and TraceCapture are sibling repositories with clean independent history. The combined
GolfData repository remains a private archive. TraceLoft contains no acquisition implementation.
Use GSPro Open Connect v1 on localhost:900 for input and optional direct localhost:921/999 output.
Do not require rēlā. Local persistence precedes acknowledgement, and forwarding cannot block storage
for more than its bounded write timeout. Preserve raw extensions and freeze shot-time context.

Use one auto-saving destination selector and remembered settings. No separate listening start/stop
step. Normal shutdown preserves the unfinished session and next launch restores it. Explicit session
end/abandon remains the user's action. Keep the existing SQLite path and immutable historical metrics.

## Carried-forward product decisions

- Python owns shared practice and SQLite; browser clients present/control it.
- Localhost needs no pairing. LAN mode is opt-in for trusted networks.
- White Vector surfaces, square controls, cobalt selection; circular club buttons remain.
- Robust club summaries use median/IQR, with sample counts and missing data distinct from zero.
- Original shots, source evidence and exclusions remain traceable; session deletion is recoverable.
- Models, demo shots and course artwork are explicitly distinguishable from measured outcomes.
- Full research and historical decisions remain in the private combined archive; current operation
  follows README, docs/RELAY.md and DESIGN_PRINCIPLES.md.

## D51 — Sheboygan Straits and artwork registration (2026-10-03)

Use the official Straits Blue pars/yardages (7,142 yards/par 72) with original lakeside layouts.
Generate from original geometry guides, then trace the finished art and visually review scoring
edges before shipping. Hash each asset with its registered geometry. Keep all design-only image
analysis dependencies outside the application environment. Existing endpoint lie rules, round
snapshots and corrections apply; dense sand does not imply simulated bunker depth or terrain.
See [course guide](docs/SHEBOYGAN_STRAITS.md).

## D52 — Map-first Play layout (2026-10-03)

Implement approved Option 1: consolidate hole scoring into the round scorecard strip, place the
compact club row above a full-width map, and replace the position sidebar with map readouts.
Put planning settings and secondary tools in disclosures below the map. Closing planning controls
does not change heatmap visibility. Preserve explicit exits, recording/completion warnings, frozen
review and the authoritative scoring model. Course scaling preserves aspect ratio and registration.
See [approved concept and implemented review](designs/play-map-first/README.md).

## D53 — Selected-nine rounds (2026-10-03)

Offer Full 18, Front 9 and Back 9 for the two full courses. Freeze only the selected hole packages
and their original numbers in the round, with selected totals and a `selection` key. Default to
Full 18 for new and legacy full-course sessions. Completion/review/corrections follow that saved
sequence; corrections remove result snapshots by hole ID, never by assuming index equals number.
Imported individual holes retain their existing flow. No database migration or old-session rewrite.
Retire the four starter holes from the catalog while retaining their assets/load compatibility.

## D54 — Source-anchored illustrative ball replay (2026-10-03)

Use reported carry/total when valid; otherwise retain reported total with a modeled carry ratio,
or use available modeled endpoints on Range. Preserve missing source measurements. Fit the saved
OpenGolfCoach trajectory to the chosen distance anchors and use its estimated hang time in seconds
without compressing the flight clock. Landing lateral position and roll timing remain illustrative;
missing model inputs produce an explicitly labeled endpoint-only replay. Play additionally fits
the presentation to the frozen scored endpoint and lie adjustment, never rescoring it. Putting
replays the existing estimated roll endpoint, without invented flight or gimme movement.

Save independent flight predictions on new applied full shots in Play, using the existing versioned
flight payload; do not backfill old rounds. Use presentation-only clocks, no replay writes, latest
arrival only for batches, no automatic history replay, Replay/Skip and reduced-motion support.
This is a limited presentation step; validated bounce/roll, obstacles, terrain and realistic physics
remain separate backlog work. See [verification](designs/shot-motion/README.md).

## D55 — Simple carry-landing rollout rules (2026-10-03)

At reported carry, stop immediately in sand; remove 75% of remaining rollout in rough and 100%
in OB by default, with separate setup percentages. Calculate the landing point by carry/total
interpolation along the original adjusted shot vector; lateral landing remains an estimate. Apply
the existing starting-lie reduction and direction variation first. Final position determines lies
and water/OB penalties. Missing/invalid carry skips landing rules without discarding the shot.

Version new outcomes as endpoint-golf-v2 with frozen landing-rollout-v1 evidence. Preserve raw
readings and all prior outcomes; legacy active rounds use default rollout settings for new shots.
Animation consumes saved landing/final points, preserving flight landing when rollout shortens.
This does not add bounce, continuous terrain interaction, new putting physics or adjusted heatmap
predictions. See [operation and verification](docs/PLAY_LANDING_RULES.md).

## D56 — Finished-art course registration (2026-10-03)

Audit every hole against the finished raster artwork, using registered overlays and reviewed pixel
landmarks. Publish corrected Boulder Beach and Sheboygan Straits as immutable v2 packages for new
rounds. Retain original assets/v1 packages and frozen session layouts; never change the surface or
score of a previously saved shot through a catalog update. Soft vegetation and surf transitions use
simplified vector edges, and the playable image perimeter remains an explicit game OB boundary.
Keep extraction dependencies in design tooling, outside the running app. Hash artwork/geometry and
retain fixed classification probes to detect drift. See [review](designs/course-registration/README.md).

## D57 — Fairway control-point refinements (2026-10-03)

Follow user review with Boulder v3 for fairways 6, 16 and 18. Use explicit native-art control points
and smooth perimeter sampling where mowing/lighting fragmented the color masks. Keep all other
surfaces, yard registration and artwork unchanged; retain v2 and frozen rounds. Check putting-apron
continuity and independent inside/outside landmarks in addition to structural/hash validation.
See [images and reproduction](designs/boulder-fairway-refinement/README.md).

## D58 — Judges Course map/photo adaptation (2026-10-03)

Use the supplied 18 illustrated maps and exact scorecard yardages, with four photographs as
woodland/lakeside style inspiration. Generate separate overhead aerials and trace finished art.
Use provisional middle tee pads and label Provided yardages instead of inferring a tee color.
Keep uniform approximate route scale, native image proportions, grass cutouts and split fairways.
Shared review tooling supports native dimensions and first-version packages. Preserve older
courses and frozen rounds; no acquisition or database schema changes.

## D61 — SQL analyses and frozen calibration cohorts

Analyze defaults to source columns. Bag/wedge results freeze exact report/context/derived IDs, inclusion flags and distinct physical-shot membership. Explicit per-golfer/bag/kind/data-mode publication is invalidated by cohort changes; future predictions use selected versions, historical scores remain pinned.

## D62 — Reviewed calculation publication and preserved history (2026-10-10)

Freeze exact report, shot, attempt, equipment context, inclusion flags, handedness and putting settings
for each batch. Hash the adapter and installed flight implementation. Commit outputs independently so
interrupted runs can resume without duplication; changed code requires a new batch. Require complete
ready coverage, unchanged dependencies and a freshly reviewed selection token before atomic publication.
Keep source reports and historical drill/game pins immutable. Analytical publication can change future
statistics and invalidate dependent Play profiles, but never rescore old sessions. Preserve old results,
publication history and model lineage in readable views and CSV. Analyze defaults to reported metrics,
including total distance; estimates require explicit selection and labels.

## D63 — Shared Analyze query and compact exploratory views (2026-10-10)

Use one authoritative SQL-backed attempt selection for multi-club OR filters and inclusive numeric
AND predicates, charts/detail/export and recalculation inputs. Preserve pre-numeric inclusion-scoped
context separately. Displaying a missing metric does not discard the attempt; a range on it does.
Keep medians/type-7 IQR/n, independent units, configuration/intent/version cohorts and real/demo/
source/estimate identity explicit. Date buckets use recorded session starts; shot plots use UTC.

Selections & filters collapses without changing query membership. Inspecting an interval/shot only
changes highlighting/displayed detail; range filters change the query and CSV. Compare replaces
common date bounds with named cohort dates, inherits common equipment/inclusion/numeric scope and
shows overlap. Browser-local saved views store dynamic queries/layouts per golfer, never frozen
publication. Shared views, frozen comparisons and advanced brushing/normalization remain future.
See [Analyze operation](docs/ANALYZE.md).
