# TraceLoft / fs_bridge decision log

Decisions made on 2026-09-30 while getting `fs_bridge.py` (Foresight Table view → GSPro Open Connect)
running for the first time. This was a proof of concept: putting indoors, no GSPro installed yet. Times
are approximate, local. Each entry says whether it still stands; later entries supersede earlier ones.
Design details are in the notes at the top of `fs_bridge.py` (letters in brackets); open work is in
`BACKLOG.md`.

**Where it ended up:** iPad Pro → AirPlay → "AirPlay - Screen Mirroring Receiver" on the left half of the
4K monitor → `fs_bridge.py run --no-gspro --viewer --debug`. 75 of 75 putts (shots 27–101) were sent once
each and read correctly. The bridge's own latency is ~0.17 s; Foresight's table animation adds 0.5–1.2 s,
growing with table size.

---

## Setup

### D1. Python 3.12 per-user via winget, with tesserocr 2.10.0 (Tesseract 5.5.2) · 08:05 · active
- **Context:** the PC had no Python (only the Microsoft Store stub). The script needs OpenCV, NumPy,
  Pillow and Tesseract.
- **Decision:** install Python 3.12 per-user with winget. Use the prebuilt tesserocr wheel from
  simonflueckiger/tesserocr-windows_build (cp312, Tesseract 5.5.2), and put `eng.traineddata`
  (tessdata_fast) in the project's `tessdata/` folder. `TESSDATA_PATH` points there.
- **Why:** 3.12 has wheels for everything. The tesserocr wheel ships without language data, so OCR would
  have failed at first use.
- **Note:** `python` on PATH is still the Store stub. Run
  `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.

### D2. Capture card is device 0; warn on a blank frame · 08:10 · active (for HDMI)
- **Context:** the UGREEN 15389 is the only camera on the PC. At first it showed its "UGREEN" no-signal
  logo (720x480) or pure black (1080p).
- **Decision:** keep `DEVICE_INDEX = 0`. When the first frame is flat, print a "no HDMI signal?" warning.
- **Why:** a blank frame otherwise looks like a working source, and calibration would silently run on black.

### D3. Match `FIELDS` to the table; allow 1 mph ball speed · 08:18 · active
- **Context:** Foresight's table columns are Shot, Ball Speed, Launch Ang., Launch Dir., Side Spin,
  Back Spin, Total Spin, Spin Axis (no Carry or Descent). Teaching types values in `FIELDS` order.
  Putts run 3–6 mph, and the minimum was 5.
- **Decision:** reorder `FIELDS` to match the table, and lower the ball-speed minimum to 1 mph.
- **Why:** with the old order, both boxing and typing would go in the wrong sequence, and most putts
  would fail validation.

### D4. `--no-gspro` mode · 08:30 · active
- **Context:** GSPro isn't installed yet (the sim is still being built). `run` blocks until GSPro connects.
- **Decision:** add a stub client that accepts every payload. Shots are still detected, validated and
  logged (`sent=False`, note "ok (no GSPro)").
- **Why:** it lets the whole pipeline be tested without GSPro. Dropping the flag restores normal behavior.

### D5. Calibrate automatically instead of by hand · 08:28 · active (manual `calibrate` still works)
- **Context:** the box-drawing windows were confusing: the prompts only appeared in the terminal, and
  closing a window just reopened it. Its fix (a prompt banner, and closing a window quits) is still in.
- **Decision:** calibrate by measuring the text edges on a captured frame and transcribing the visible rows.
  Train the reader through the script's own `teach()`, then check it with a leave-one-row-out test.
- **Why:** faster, repeatable, and it produces an accuracy figure before anything goes live.
- **Follow-up:** backlog item `calibrate --auto`.

## Detecting a shot

### D6. Use the SHOT # column (user's suggestion) · 08:40 · superseded by D9, then D18
- **Decision:** read the newest row's shot #. A shot = shot # up by exactly one, plus a change in the
  "N Shots" pill (for scroll protection).
- **Why:** the shot # changes even when a putt's values are identical to the last one's.

### D7. Record the iPad before designing the rule · 08:37 · finding
- **Context:** the first live run logged 12 rows for 3 putts, with ~10 s "late" values.
- **Finding** (2-minute recording): the ball-position pop-up dims the table. After the putt the row blanks,
  then the shot # and the pill move to the new number **while every row still shows the old values**, and
  about 2.5 s later the values arrive.
- **Consequence:** reading when the shot # moves would send the previous shot's numbers.

### D8. Change threshold 6.0 → 0.5 · 08:53 · active
- **Context:** shot 30's values arrived but were never noticed.
- **Evidence:** a still HDMI frame is pixel-identical (0.000 over 302 frames). A one-digit change on dim
  10 px text moves a thumbnail by only 2.15–4.65, under the old 6.0 threshold.
- **Decision:** set `CHANGE_THRESHOLD` to 0.5.

### D9. The shot rule: confident, moved, incremented (user's proposal) · 08:49 · extended by D12, reworked by D18
- **Decision:** a shot requires (1) every cell of the newest row read confidently, (2) the values changed,
  and (3) the shot # is last accepted + 1. Comparisons are against the last **accepted** shot, not the last
  frame seen, which also makes scrolling back up harmless. Frames dimmed by the pop-up are skipped. If the
  values never arrive, the shot is given up after 10 s and logged, not sent.
- **Why:** it directly addresses D7's stale-values state. Identical putts are handled by also watching row 2.

### D10. Turn off Foresight's ball-position pop-up; timeout counts only visible time · 09:03 · active
- **Context:** shot 36's values arrived under the pop-up, which stayed up 19 s while the next ball was
  positioned. The 10 s timeout expired while the bridge couldn't see the table.
- **Decision:** the user turned the pop-up off in Foresight. The timeout now only counts time the table is
  visible.

### D11. Foresight slows down as the table grows; start new sessions · 09:10 · active
- **Evidence (old iPad):** shot # → values took 2.3 s at 25–35 rows and 3.9 s at 45, but 0.06–0.3 s in a
  fresh session. The bridge itself took ~90 ms.
- **Decision:** start a new Foresight session regularly. Tiles view was considered and rejected: its numbers
  roll up, so they can't be read mid-animation.

### D12. Also require row 2 to hold the previous shot · 09:14 · active (by image since D17)
- **Context:** once the delay was short, reading a half-redrawn row became the main risk.
- **Decision:** a shot also needs row 2 to show the last accepted shot, proving the table has fully moved
  down. Skipped after a timeout (the previous values were never confirmed) and for a session's first shot.

## Hardware

### D13. HDMI drop-outs are the link, not power · 09:30 · finding
- **Evidence:** pure black frames with the card still enumerated (no USB events in Windows). The old iPad
  was losing charge on pass-through, so the charger was unplugged: the drop-outs continued (3 in 6 min).
- **Conclusion:** the cable, the adapter or the card's HDMI input. Drop-outs are labelled
  `NO HDMI SIGNAL` in `--debug` and the viewer. (Later on the iPad Pro they worsened to ~1 every 2 min,
  lasting 1–55 s.)

### D14. Switch to an iPad Pro, mirrored · 09:44 · active
- **Why:** the old iPad was slow (table delay ~80–100 ms per row) and dropped HDMI.
- **Setup:** Stage Manager / windowed apps off, so HDMI mirrors instead of extending. Foresight can't run on
  an extended display, and it ignores Larger Text / Display Zoom.
- **Result:** the table delay was mostly flat, but the mirrored 1080p output shrank the digits to ~10 px.
- **Rejected:** the card's 2560x1440 mode. The iPad only sends 1080p, so 1440p is just an upscale (it
  looked worse).
- **Calibration kept** as `config_old-ipad.json` / `glyphs_old-ipad.npz`.

## Reading 10 px digits

### D15. Grid segmentation, ambiguity margin, pooled training · 10:17 · active
- **Context:** on the iPad Pro's 10 px digits, the leave-one-row-out check scored 69/80. Digits shed 1 px
  slivers (read as extra "." or digits) and faint decimal points vanished.
- **Decision:**
  - **Grid segmentation:** split each cell on the monospaced font's grid (pitch refined to 0.01 px); an
    empty slot between two digits is a decimal point.
  - **Ambiguity margin:** the best match must beat the best *other* character by 0.03 (`MATCH_MIN_MARGIN`),
    because 3 vs 8 differ by a few pixels.
  - **Pooled training:** train from several frames (49 rows).
  - **Tighter cutoff:** `MATCH_MAX_DIST` 0.20 → 0.12 (correct reads ≤ 0.07; wrong-glyph matches ≥ 0.114).
- **Evidence:** 391/392 right and 0 wrong-but-confident. The old iPad was unchanged (112/112).
- **Rejected:** a Gaussian blur (it shrank the 3/8 margin), bigger glyph features (no gain), and wider
  training shifts (no effect).

### D16. Infer the shot # from table order, learn it, and log stuck rows · 10:47 · active
- **Context:** shot 40 was lost silently. The first 4 in the tens position had never been seen, and at
  10 px each position renders differently.
- **Decision:**
  - **Infer and learn:** when only the shot # is unclear and row 2 is the last accepted shot, row 1 must be
    n + 1. The shot is sent and the number learned into `glyphs.npz` (original backed up once).
  - **Stuck alert:** a newest row unreadable for 5 s of visible time is logged red.

### D17. Compare row 2 as an image, not a read · 11:08 · active
- **Context:** shots 42 and 50–53 were lost. Row 2 sits at a different sub-pixel height, so the same text
  read differently there, and the checks from D12 and D16 failed.
- **Decision:** save the image of each accepted row. "Row 2 is the last accepted shot" is an image match:
  the column ink profile plus a 2D compare aligned to ¼ px.
- **Evidence:** 9 of 9 saved rows matched only themselves, 3–12 rows lower (same ≤ 0.77, others ≥ 1.37,
  with 1.0 as the cutoff).

### D18. Image-first rule; the shot # becomes optional · 11:08 · active
- **Decision:** a shot = row 1 reads confidently, row 1 is **not** the last accepted row, row 2 **is** that
  row (by image), and the values moved. A readable shot # must be n + 1, otherwise it's logged as a jump. An
  unreadable one is inferred and learned. An unknown one is logged blank, and shots still go out.
- **Why:** it no longer depends on reading every digit in every position. Scrolling, club switching and
  identical putts are all still handled.

### D19. Never take the shot # from the "N Shots" counter · 11:05 · active
- **Context:** as a startup fallback, Tesseract read the pill's "53" as "3". The next putt would have been
  learned as "04", corrupting the reader. The bridge was stopped before anything was learned.
- **Decision:** the counter only feeds the log's count column. When the shot # can't be read at startup,
  it stays unknown instead of being guessed.

### D20. A blank newest row at startup isn't a starting point · 12:07 · active
- **Context:** right after the HDMI signal returned, a frame without the table drawn would have been taken
  as an empty table ("next is 01").
- **Decision:** the first readable row becomes the starting point. The exception is a new session's
  first shot (01 with row 2 empty), which is sent.

## AirPlay

### D21. Switch from HDMI to AirPlay window capture (user) · 12:17 · active
- **Context:** HDMI drop-outs were getting worse (30 in an hour, up to 55 s), and the 10 px digits were
  fragile.
- **Decision:** mirror the iPad over AirPlay to "AirPlay - Screen Mirroring Receiver", snapped to the
  **left half** of the 3840x2160 monitor (client area 1918x2111). Set `CAPTURE_SOURCE = "window"`.
- **Why the half-screen snap** (user's choice): it's a repeatable size, which the calibration depends on,
  and it leaves the right half free (window capture copies whatever is on screen).
- **Evidence:**
  - digits ~15 px and sharp
  - a still picture is identical frame to frame
  - the reader scored 104/104 in the leave-one-row-out check from only 13 rows
  - the row-image match gap widened (0.59 vs ≥ 1.92)
  - no drop-outs
- **HDMI calibration kept** as `config_ipadpro_hdmi.json` / `glyphs_ipadpro_hdmi.npz`.

### D22. Grab one cropped rectangle from the window · 12:35 · active
- **Context:** grabbing the whole window ran at ~17 fps. Each GDI screen grab waits for a display refresh
  (16.7 ms): a small grab took 16.7 ms and the full window 37.7 ms.
- **Decision:** grab one rectangle covering the header, rows 1–2 and the counter, and paste it into a
  full-size frame so `config.json` coordinates don't change. The viewer shows just that strip.
- **Result:** ~44 fps with the viewer (~50 without). The bridge's share of latency went from 0.28 s to 0.17 s.
- **Rejected:** two separate grabs (table + pill) cost two refreshes and only reached ~30 fps. DXGI
  capture (`dxcam`) is in the backlog if more speed is needed.

### D23. Validated to 100 shots · 13:14 · finding
- **Result:** shots 27–101 in one session: 75/75 sent once and correct (checked against the live table and
  the saved crops). No shot # needed inferring, including 99 → 100. No drop-outs.
- **Latency:** shot # → sent grew with the table, from ~0.7 s at 47 rows to ~1.35 s at 90–101, seemingly
  levelling off. The bridge's share stays ~0.17 s.
- **Recommendation:** start a new Foresight session every 40–50 shots. Backlog: a latency warning.

## Process

### D24. Backlog, then a stacked viewer and a control UI · 13:00 · planned
- **Decision:** keep the work list in `BACKLOG.md`. Requested next:
  - **Stacked viewer:** to sit beside the AirPlay window and validate captures.
  - **Control UI:** GSPro on/off, source selection, calibration profiles, start/stop.

### D25. Document the code and the decisions · 13:20 · done
- **Decision:** every function and class in `fs_bridge.py` has a docstring. The file header was rewritten
  as v5 (current source, usage, operating notes, and design notes P–S). Outdated comments were fixed, and
  so was one misleading calibration warning (the counter no longer protects against scrolling).
- **Behavior is unchanged:** the 25 ShotTracker scenario tests pass, and the AirPlay frames read the same.


### D26. Review fixes and conservative recovery · 2026-10-01 · implemented, live validation pending
- Timeouts retain the last confirmed row image instead of accepting an unverified baseline (updates D12).
- A confidently read forward jump can establish a new baseline when row 2 shows n - 1 and the two
  measurement rows differ. The ambiguous jump itself is logged, never sent. Identical or unreadable
  recovery rows remain logged until stronger evidence is available.
- Unknown shot numbers no longer fail measurement validation (implements D18), and a confirmed first
  shot 01 with empty row 2 resets a session even when measurements match the previous session.
- Missing/repeated capture frames pause visible-time timers through the first returning frame.
- Numeric parsing now checks the entire cell; malformed suffixes or extra precision are rejected.
- GSPro connection and reconnection run in a background thread. Offline/uncertain sends are logged
  as failures and never replayed, avoiding delayed shots after reconnecting. Socket writes are bounded
  by a 0.1 s timeout; a successful write still does not establish GSPro application acceptance.
- Verification: 21 regression tests pass, including a local TCP disconnect/reconnect/no-replay test.
  All nonempty raw reads in the existing 167-row log parse with the new rules. AirPlay capture and a
  real GSPro install still need live validation. The older scratchpad tests were not available here.

### D27. Desktop control interface and stacked viewer · 2026-10-01 · first version
- Use tkinter for the desktop controls (`fs_ui.py`), launched by `Launch GolfData.cmd`. Capture/OCR and
  sending live in an isolated subprocess (`fs_ui_worker.py`) so the UI remains responsive and restartable.
- Publish live frames at 10 Hz and send read/record updates when they occur. Match distances come from
  the actual OCR decision; the UI does not reread cells to estimate confidence.
- Select paired config/glyph paths directly. Preview does not log or send shots; GSPro sending starts off.
- Cooperative Stop lets pending crop writes finish; a six-second fallback terminates blocked drivers
  or interactive calibration input. Calibration/teaching retain their existing windows/terminal prompts.
- The control window places itself beside the receiver, stops capture on overlap, and rejects a capture
  size that differs from calibration. Live-session QA remains pending.
- Verification: all 31 regression checks pass, including Tk rendering/control state, profile validation,
  worker errors, telemetry and the existing detection/network checks. Layout inspected with saved captures.
- Shot analysis tools requested separately; scope and first workflow are tracked in `BACKLOG.md`.

### D28. Preserve training crops, retain 25 validation capture sets · 2026-10-01 · implemented
- User selected a rolling limit of 25. Count complete logged-read crop sets, including failed/logged
  reads, across sessions and restarts. The CSV continues to record all shots/decisions.
- Before reducing the working collection, archived 1,764 crop PNGs and 12 matching log/config/glyph
  files under `backups/`, with per-file SHA-256 verification and source-stability checks.
- "Keep crop sets" in the desktop controls defaults to 25; 0 stops new saves. Prune only recognized
  older crop PNG groups, after every field in the new record saves successfully. Backups are never pruned.
- Failed crop writes are reported instead of silently continuing to prune. History explains when a
  crop is no longer retained. Diagnostics has a shortcut to the backups folder.
- Verification: 45 tests cover archive integrity, tampering, source changes, retention across sessions,
  complete async writes, disabling saves, invalid limits, and failed writes, plus existing regressions.
  Live-session verification of the new retention setting remains pending; OneDrive sync is unverified.

### D29. Local web studio, Python capture owner · 2026-10-01 · first release
- Serve responsive HTML/CSS/JavaScript with SVG charts from FastAPI; use WebSocket snapshots for shared
  practice/capture state. Keep existing Python capture, scoring and on-disk JSON/CSV formats.
- Run one background service. Localhost is default; trusted-LAN access is an explicit launcher option
  without pairing, per the user’s preference. Connected browsers control the same drill and capture. GSPro keyboard remote
  commands are future work and will execute on the Windows host.
- Prevent competing UI workers with a Windows named object and detect older desktop workers before
  starting web capture. Keep calibration/teaching in existing desktop tools during migration.
- Initially no inferred putting distance was displayed; D31 adds explicitly labeled distance models. Random pace stores and scores each shot's own target.
  Sessions are reviewed after restart; launching another drill requires finishing the active session.
- Source checkpoint `4990247` uses an anonymous commit identity without saved author configuration.
  No Git remote exists yet; runtime data requires separate backups.

### D30. SQLite authority and snapshot backups · 2026-10-01 · implemented foundation
- User authorized migration after the schema/monitor research. Store live data outside OneDrive at
  `%USERPROFILE%\GolfData\data\golfdata.sqlite3`; Windows redirects AppData into the packaged host's
  cache, so use a user-owned location. The web Python service is the sole scoring owner.
- Preserve raw imports and source/configuration/mapping lineage, typed metrics, historical targets,
  session-only exclusions and recoverable deletion. Original CSV/JSON/configuration/glyph files stay
  intact and are backed up before cutover; CSV capture continues as a diagnostic journal.
- Commit receipt/shot/observations/practice outcome together; durable receipts precede telemetry and
  survive retries/crashes. Storage recovery never triggers GSPro replay. Keep native measurements
  separate from modeled outcomes and unresolved legacy acceptance separate from confirmed shots.
- Freeze production catalog/mapping versions under `data/`; activate seven current calibrated fields.
  Broad equipment/course/analytics/cleanup/vendor capabilities remain proposed, not schema-v1 features.
- Use SQLite backup API snapshots with manifests/integrity/count/checksum verification and restore
  to a new destination. Google Drive upload is the requested next design; protection is local-only.
- Route recording/practice through the web studio after cutover to avoid competing legacy JSON writers;
  desktop preview/calibration/teaching remain available. Operational details are in
  [DATABASE_OPERATIONS.md](docs/DATABASE_OPERATIONS.md); actual verification is in WORK_LOG.md.

### D31. Putting estimates and ladder with selectable models · 2026-10-01
- User requested distance metrics/setup based on OpenGolfSim and a distance ladder, then asked whether
  academic models are more accurate. Use constant-deceleration Stimp physics as a transparent default
  baseline; retain an independent integration of Fuse's pinned speed-dependent braking as an optional
  comparison. Neither is validated against GSPro or the physical mat.
- Save measured launch values unchanged, with per-attempt estimate/target/error, entered Stimp and
  immutable model assumptions/source identity. Historical sessions without Stimp/model stay unavailable;
  review never recomputes outcomes. Export derived outcomes separately from measured metrics.
- One confirmed putt advances each ladder rung, including misses; chosen ascending/descending distance
  sequence repeats for configured rounds. Exclusions do not rewind progression; duplicates do not advance.
- Next calibration: collect repeated flat GSPro stopping outcomes across speeds/Stimp, record version and
  assistance, validate fitted curves on held-out samples. Holed putts are censored stop outcomes. A GSPro
  fit describes the game, not real mat travel. See [model notes](docs/PUTTING_DISTANCE.md).
### D32. Dedicated VDD source and expanded table · 2026-10-01
- User added a virtual display and expanded the Foresight table for future virtual golf. Bind VDD to
  an explicitly selected secondary Windows display, preserve independent config/glyph files, clip
  maximized borders and stop on minimization, display loss or movement off the selected display.
- Capture remains visible-screen copying; keep VDD unobstructed. Main-display controls do not need
  room beside a full-screen receiver. Current physical resolution is 3840 × 2160, receiver 3840 × 2077.
- Missing optional cells are unavailable, not zero. Required/core, spin, confidence and row-shift
  validation stay active. New source units are yards, peak height feet, angles degrees and time seconds.
- Archive mapping v2 for expanded fields without editing v1 observations/definitions. Preserve
  Foresight semantic variants; reported flight values are distinct from built-in sim outcomes and
  putting estimates. Numeric flight columns/full-swing direction conventions need live verification.
- Training/held-out frames and transcriptions have a local checksum backup outside rolling crops.
  Calibration/replay evidence and remaining live checks are recorded in WORK_LOG.md.
### D33. Five-section navigation · 2026-10-01
- Use the user-requested order Capture, Practice, Play, Analyze, Sessions. Reserve stable `#play`
  and `#analyze` locations with explicit Coming soon pages and exits to Practice/any active drill.
- Placeholder visits do not create/end sessions or change capture. Gameplay and analytical tools
  remain backlog features; future implementations will replace these placeholders.

### D35. FUSE selected for the 2D simulator · 2026-10-01 (superseded)
- Later on 2026-10-01, user ruled out Open Golf Sim as too immature for our purposes. Remove its
  desktop API and FUSE engine from the 2D-game shortlist. The current direction is simplified 2D
  gameplay with tunable lie effects; the subsequent Foresight outcome selection is recorded below.
  Existing independent putting comparison behavior is unchanged. The earlier decision follows for history.
- User selected FUSE as the initial physics engine and prefers reusing compatible existing courses.
  Retain terrain/surface geometry beneath touch-aimed top-down presentation, explicit lie feedback
  and flat-green putting. Course assets require their own established reuse permission and provenance.
- Keep Python authoritative for rounds, scoring and accepted outcomes; use a designated engine owner,
  frozen shot inputs and idempotent result submission. Preserve raw measurements; no added random
  dispersion for measured shots by default. Strokes-gained analysis evaluates saved modeled outcomes.
- Retain upstream license/required notices with reused code. Engine integration, course selection
  and physics calibration remain unimplemented/unverified. See [selected plan](docs/FUSE_EVALUATION.md).

### Foresight outcome source and gameplay sliders · 2026-10-01
- User pivoted back to Foresight as the shot-outcome source, with slider settings. Use reported
  carry/total/offline for full shots and simple adjustable lie penalties/optional direction variation.
  Keep flat-green putting estimates. No external physics engine or interpolation dataset is required.
- Preserve raw inputs and reported outcomes separately from gameplay adjustments; Python owns
  rounds and accepts each shot once. Freeze aim/settings/random draws per shot. Verify full-swing
  capture and total/offline semantics before endpoint placement. See [game plan](docs/2D_GAME_PLAN.md).
- This is a design decision, not implemented gameplay. Rough 7% is a proposed starting value;
  remaining slider defaults and cup/gimme rules are open.

### D34. Full-swing distance ladder · 2026-10-01
- User clarified ladders should include wedges/irons, approved the setup/live concepts, and requested
  implementation. Keep this module separate from Putting ladder; score selected reported carry/total
  in yards without estimating flight from speed. Retain targets, metric and scoring availability.
- Wedges/Irons are editable range presets. Support custom range/step, shots per target, rounds,
  ascending/descending order and an inclusive ± yd window. Misses advance; missing distance does not.
  Session-only exclusions change analysis without rewinding progression. No pressure/retry rules yet.
- The active service publishes its required distance column to capture; wait for a confident reading
  before consuming the newest row. Incompatible profile guards explain the needed column. A missing
  accepted record from another path remains an unscored attempt; do not substitute carry/total.
- Session label remains manual context; D35 adds per-shot manual bag/club tags. Matrix linkage remains proposed.
  Reuse shared exits, abandonment, review, recoverable deletion, SQLite and CSV export. Full-swing
  numeric OCR still needs live verification; isolated results are not live acceptance evidence.

### D35. Manual bags and per-shot full-swing club tags · 2026-10-01
- User requested an easy in-session club control plus multiple editable bags, starting with My bag
  and common clubs. Add selectors in full-swing setup/runner and a bag-manager dialog, keeping feedback
  prominent. Changing bag clears club; choosing no club records untagged rather than inferring one.
- The Python service owns a versioned manual catalog in SQLite metadata, with stable bag/club IDs,
  validated membership and optimistic catalog-edit conflicts. No SQL schema migration is required.
  Club identities are local to each bag for this first step; shared physical-club/specification
  revisions, GSPro following, bag mapping and wedge matrices remain proposed.
- Freeze selection names/IDs/revision in durable worker receipts at accepted-row time and copy them
  onto each attempt. Catalog edits and switches affect future shots; prior measurements/tags and
  targets stay intact. Preserve queued receipts through retries and export tags in attempt CSV.
- Finished/review sessions show saved tags and no next-shot controls. Historical bulk correction
  remains separate backlog work. No club commands are sent to GSPro.

### D36. Compact bag taps and header capture status · 2026-10-01
- User approved the refined left-column bag concept: three quick bag choices with smaller direct
  club circles to the right. Render actual catalog clubs, wrap at smaller widths and preserve 44 px
  touch targets. More bags reaches the full catalog; empty slots open creation through Manage bags.
- Healthy capture is already indicated in the header, so omit the duplicate listening bar in both
  putting and full-swing runners. Keep actionable recording warnings above tagging and retain the
  independent red Session over banner even while global capture runs.
- Selection still saves through the authoritative service before the next shot; switches and catalog
  edits never rewrite recorded tags. Shared catalog refresh preserves unrelated setup parameter drafts.


### D37. Open-ended range, independent flight model and synthetic harness · 2026-10-01

- Practice owns the range; Python owns shared state and immutable shot acceptance. Reuse compact
  bags/clubs, header capture status, lifecycle controls and recoverable session deletion.
- Foresight-reported distances remain scoring/statistical inputs. OpenGolfCoach 0.3.0 is a separate
  launch-only estimate with saved inputs, assumptions, model version, trajectory and endpoints.
  Total lateral position follows the native rollout heading/radius reconstruction; reported offline
  is not assumed to be carry offline. No inferred club delivery is presented as a measurement.
- Session-only cleanup records corrected tags/inclusion/removal as audited overlays with reasons,
  exact selected keys, stale-revision guards and Undo. Original shots/tags remain unchanged.
- A dedicated Demo range generates one/ten synthetic shots without hardware/GSPro delivery. Demo
  and live sessions reject each other's event types. SQLite/CSV labels and session filters preserve
  that distinction. Deletion is recoverable; raw synthetic evidence is retained.
- Range target changes apply prospectively. Width is visual; the carry depth defines the scored
  distance window. Cross-session analytics/outlier policies and physical model validation are pending.


### D38. Robust per-club range summaries · 2026-10-02

- Club snapshot uses median and IQR (Q3 minus Q1) for carry, total, absolute offline, vertical launch
  and descent. Quartiles interpolate sorted readings at (n-1)p, the inclusive/type-7 convention.
- Compute absolute offline before quantiles. Count available finite numeric readings separately per
  metric; zeros are valid, missing data stays unavailable, and IQR requires at least two readings.
- Match workspace filters and include only analysis-eligible shots grouped by effective bag/club.
  Use source values, never estimated descent as a replacement. Support the legacy descent key only
  for synthetic attempts; new demo generation uses canonical descent_ang. No stored shots are rewritten.
- Place the snapshot immediately above Shot workspace in live and review screens. The separate
  scatter summary continues to show its existing mean/population spread.


### App naming preference: TraceLoft · 2026-10-02

- User likes TraceLoft and requested that the preference be logged. Use this capitalization as the
  preferred future app name. This records a naming preference, not authorization for a UI/package rename.
- Preliminary web screening found no clear golf-app match; domain and trademark availability remain
  unverified. Keep existing GolfData paths, launchers and runtime identity until branding is implemented.

### D39. Empirical per-equipment dispersion circles · 2026-10-02

- Use a radial 80% empirical envelope around coordinate medians to complement robust Club snapshot
  metrics. Nearest-rank radius (ceil(0.8n)) requires five included positions; no covariance/normality
  assumption or automatic outlier removal. Zero spread remains zero, and untagged shots have no circle.
- Reuse effective bag/club color identities across dots, rings and legend. Follow the selected source,
  carry/total coordinates and filters. Excluded/removed/missing positions never enter the calculation.
- Default Included table remains included-only; the scatter also displays matching excluded shots
  with a white-tinted club fill and dashed edge. Other state filters apply to both surfaces. Keep
  removed shots hidden by default. All matching comparisons retain their existing semantics.
- Yard-space circles render as ellipses under independent plot axis scales; label this explicitly.
  Include full ring bounds in chart scaling. Following the compact-legend refinement, show only
  bag/club names in the legend; keep radius/count in accessible SVG labels and explain coverage and
  minimum samples in the hover/focus/tap info button next to Shot dispersion.

### D40. First playable 2D game · 2026-10-02

One original hole, endpoint placement and explicit rules establish the full live/demo/review lifecycle.
Default to demo while Foresight geometry is unverified; experimental live mode selects radial versus
downrange interpretation and acknowledges the limitation. Do not substitute HLA for final offline.
Use existing constant-Stimp putting, no external engine. Save course/settings/aim/randomness/outcomes
with source readings intact; exclusions cannot refund strokes. Suggestions use ≥5 included total
readings per bag/club/swing group from matching real/demo collections. Rich physics/benchmarks wait.

### D41. Course geometry owns the artwork · 2026-10-02

Render AI-generated material textures through the saved course shapes; retain simple colors and
a diagnostic boundary overlay. This protects existing scoring and historical rounds from image
generation drift. First delivery is cosmetic terrain on Meadow One, not imported real-course data.
Future imports should combine georeferenced aerial imagery, available mapped geometry and official
tee/yardage metadata, followed by boundary review and masked visual restyling. Details and primary
sources: [course artwork/imports](docs/COURSE_ART_AND_IMPORTS.md).

### D42. Historical club preview · 2026-10-02

Read current included mapping attempts for the selected bag/club and real/demo mode; separate bag
mapping from named wedge swings. Reported Total follows saved round geometry; Carry requires saved
OpenGolfCoach paired endpoints. Rotate/translate in yard coordinates without stretching to the aim.
Use compact kernel density and an empirical 80% radial outline; five-point minimum and small-sample
warning under twenty refine the concept's proposed twenty-point density gate. No prediction confidence
or hazard probability. Initial release is unadjusted for lie effects, hidden on greens/in review,
and read-only with respect to scoring. Details: designs/GAME_CLUB_PREVIEW.md.

D42 visibility refinement: the user prefers the same bright blue for every on-course heatmap.
Use solid, non-scaling outlines with dark contrast backing. This supersedes the initial catalog-color
choice for Play; range scatter keeps its separate bag/club palette.

### D43. TraceLoft branding implemented · 2026-10-02

The user has authorized the rename, superseding the earlier naming-preference-only note.
Use TraceLoft in visible web/desktop branding, errors, exports and new launchers. Keep old
launchers as forwarding wrappers and recognize both health identities during the transition.
Keep database locations, environment variables, capture mutex/protocol, model/mapping IDs and
historical evidence unchanged; branding is not a storage or source-ingestion migration.


### D44. Durable course workbench and reviewed publication · 2026-10-02

Keep original WGS84 source and apply validated corrections in its original projected yard frame.
Moving tee/pin must not reproject other geometry. Editable drafts use revision-checked SQLite
metadata (`course_draft.v1.*`); published course packages stay immutable and retain import params.
Incomplete but valid shapes can be drafted; publishing requires valid green/tee/pin/boundary
placement plus explicit human review. The UI saves the draft before publishing. A published
version is copied into each new round; later edits never rewrite played geometry. Registered
imagery, segmentation and mask-constrained AI visuals are subsequent independent stages.

### D45. Fictional course artwork before further real-course sourcing · 2026-10-02

The user prefers generating realistic fictional holes from target yardages, then adding overlays.
Start with a par 3, par 4 and par 5. For new concepts, register a uniform image-to-yard transform
and trace/review scoring surfaces before publication; generated pixels do not establish precise
yardage or rules. Separate dynamic markers and historical heatmaps from artwork. Preserve all
existing played versions and keep real-course import/provider work available but deferred.
See [starter concepts and overlay workflow](designs/fictional-holes/README.md).


D45 implementation: the three fictional version-1 holes are now bundled as separate single-hole
rounds. Keep an explicit course-ID allowlist; load fresh package copies and freeze each in its
session. Artwork stays unrotated with one uniform pixel-to-yard scale based on the authored route.
Map aim/pin distances are straight line and may differ from listed dogleg yardage. Use the existing
endpoint game and heatmap pipeline; no new physics or real-course claims are introduced.

### D46. Optional rēlā input adapter · 2026-10-02

rēlā's Other API is an in-process DLL contract, not an included GSPro TCP listener. Implement an
independent adapter using the public compile-time contract, listening only on 127.0.0.1:922 and
emitting one final OnShotEnded event per accepted measurement. Preserve the existing capture/service
and database pipeline; keep output ports separate (GSPro 921, Infinite Tees 999 in installed settings).
Do not report local socket/connector acceptance as simulator receipt. No historical replay or automatic
retry of shots. Initial scope is existing yards/mph ball packets, with explicit limitations for missing
values in the host's non-nullable fields. See [connector operation](integrations/rela/README.md).
