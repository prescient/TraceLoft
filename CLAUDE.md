# CLAUDE.md

Guidance for Claude Code in this repository. [AGENTS.md](AGENTS.md) holds the project's working
rules and is imported below. [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md) holds the product and
interface rules; this file condenses them. If either source changes, update this file to match.

@AGENTS.md

## What TraceLoft is

A local golf practice, play and analysis app. One background Python service (FastAPI + SQLite)
receives shots over GSPro Open Connect v1 (TCP 127.0.0.1:900), records them, owns all shared
practice/game state and serves the vanilla-JS "Vector" web UI on http://localhost:8765.
Screen capture/OCR lives in the separate private TraceCapture app and never belongs here.

| Area | Modules |
| --- | --- |
| HTTP/WebSocket API, request models | `web_app.py` |
| Service authority: active session, mutations, live revision | `web_service.py` (`GolfService`) |
| Shot input and simulator relay | `shot_input.py`, `open_connect.py` |
| SQLite store, transactions, backup, export, legacy import | `storage.py`, `database_tools.py` |
| Schema layers (migrations 1→5) | `shot_schema.py`, `domain_schema.py`, `analysis_schema.py`, `recalculation.py` |
| Drill/game scorers | `putting.py`, `distance_ladder.py`, `driving_range.py`, `collection.py`, `golf_sim.py` |
| Models and estimates | `putting_distance.py`, `flight_model.py` (OpenGolfCoach), `club_preview.py` |
| Analysis | `analysis.py`, `analysis_schema.py`, `analytics_demo.py`, `tour_demo.py` |
| Courses | `course_import.py`, `course_workbench.py`, `course_geometry.py`, `bundled_courses.py`, `courses/` |
| Web UI (ES modules, no build step) | `web/app.js` (router/shell), one module per feature, `web/studio.css` |

Key documents: [README](README.md), [NAVIGATION](NAVIGATION.md), [DECISIONS](DECISIONS.md),
[BACKLOG](BACKLOG.md), [WORK_LOG](WORK_LOG.md), [shot database](docs/SHOT_DATABASE.md),
[database operations](docs/DATABASE_OPERATIONS.md), [relay contract](docs/RELAY.md),
[architecture plan](docs/ARCHITECTURE_IMPROVEMENTS.md), [Analyze](docs/ANALYZE.md).

## Commands

```bash
python verify.py
```
Runs both suites plus ruff lint and writes logs plus a report outside the repo. If `node` is not on
PATH, pass `--node <path>` or set `TRACELOFT_NODE`; a required suite that cannot run fails the
verification. Install the lint tool with `.venv\Scripts\python -m pip install -r requirements-dev.txt`.
You can also run the suites separately:

```bash
.venv\Scripts\python -m unittest discover -s tests
```

```bash
node --test tests/*.mjs
```

```bash
.venv\Scripts\python -m ruff check .
```

On a fresh machine, `Setup TraceLoft.cmd` creates `.venv` from `requirements-lock.txt`
(Python 3.12). `requirements-web.txt` lists direct dependencies; update the lock only after a
verified upgrade. Helper tests do not verify the interface in a real browser.

## Protect the user's live data

- The user's real service usually runs on port 8765 / input 900 with an unfinished session.
  Do not stop, restart or send shots to it unless the user asks. A restart preserves the active
  session, but it still interrupts live capture.
- The real database is `%USERPROFILE%\GolfData\data\golfdata.sqlite3`. Never open it for writing
  or run migrations against it during development.
- For state-changing checks, use an isolated instance:
  `GOLFDATA_DATABASE=<temp>\golfdata.sqlite3`, `TRACELOFT_INPUT_PORT=<free port>` and
  `python web_app.py --port <free port>`. Tests construct `GolfService(<tempdir>)`, which
  isolates the database and binds input to an ephemeral port.
- Runtime files (`web_runtime.json`, `web_service.log`, `practice_sessions/`, receipts, backups,
  `*.sqlite3`) are gitignored. Keep them out of commits.

## Architectural invariants

- **Python is authoritative.** Scoring, session lifecycle, ownership and recording state live in
  the service. Browsers render state and send intents; they never compute an outcome that
  gets persisted.
- **Record first.** A shot is committed to SQLite before it is acknowledged or forwarded. Forwarding
  to GSPro/Infinite Tees is optional, defaults to Off, and the user's saved Relay choice is restored
  on restart (D48). Forwarding never blocks storage beyond its bounded write timeout and never
  replays stored shots.
- **One input owner.** Only one Open Connect producer may connect at a time. Localhost needs no
  pairing; LAN mode is an explicit launcher option.
- **Evidence is immutable.** Raw packets, `metric_values` and source reports never change.
  Recalculation appends versioned derived results, and analysis uses them only after explicit
  publication. Played and drill outcomes stay pinned and are never rescored.
- **Missing is not zero.** Unavailable measurements stay null throughout storage, the API, CSV and the UI.
  Reported carry/total are source metrics, so never fill them from a model.
- **Mutations are atomic.** Service mutations snapshot `practice.data`, run inside
  `store.transaction()`, and restore the snapshot on failure. Follow the existing pattern in
  `web_service.py`. `ValueError` messages become HTTP 409 text shown to the golfer, so write them
  as user-facing guidance.
- **Schema changes are migrations.** Bump `SCHEMA_VERSION`, take a verified backup, run inside
  `BEGIN IMMEDIATE`, and reconcile evidence counts/manifests before `COMMIT` (see `storage.py`).
  Never edit an earlier upgrade step.
- **Deletion is recoverable.** Sessions are soft-deleted with Restore and Undo. Finish, abandon,
  exclusion and deletion are distinct. Backups, crops and training data sit outside the session
  lifecycle.
- **Versions are immutable.** Courses, holes and calculation versions get new IDs. A saved
  round keeps the geometry it was played on.
- **Live updates stay cheap.** `/ws?protocol=2` sends revision notices only, and clients fetch
  `/api/state`. Idle connections must not receive repeated full history. Repaints must preserve
  drafts, focus, expansion, selection and scroll within the same session.

## Interface rules (condensed from DESIGN_PRINCIPLES.md)

1. **Latest shot first.** The latest measurement, target, outcome and progress get the strongest
   hierarchy and must be readable from several feet away, with units and direction visible.
   Logs and statistics go below or in secondary views.
2. **Modular practice.** Every drill follows Practice selector → setup → active session →
   results/review. Reuse shared capture, storage, navigation and components. Unimplemented ideas
   stay in the backlog, never as working-looking controls.
3. **No dead ends.** Main navigation is Relay → Practice → Play → Analyze → Sessions. Navigating
   never ends a session; End, Abandon and confirmed Exit are explicit. Review needs exits to
   Sessions and to Practice, above and below long logs. Old links identify their original session.
   Back, Forward and refresh work. Update NAVIGATION.md whenever a route, exit or guard changes.
4. **Unmistakable recording state.** Input health and an active drill are separate states.
   Healthy recording shows only in the header. A disconnected or unready source shows an
   actionable warning. A finished session shows a sticky solid-red "Session over" banner. A review
   never looks like a live drill. Pair every status colour with text or an icon.
5. **Graphs explain.** Use labeled axes, units, targets and tolerance zones. Highlight the latest
   shot. Show excluded points distinctly without erasing them, and show sample counts. Use
   median/IQR with per-metric n. Scale changes must not exaggerate improvement.
6. **Measurements, estimates and outcomes stay separate.** Label modeled values, simulator
   outcomes and recommendations as estimates. "In window" does not mean holed. Keep demo and
   real data visibly separate everywhere.
7. **Vector visual language.** Use pure-white surfaces, square panels and controls, thin dividers
   and no shadows. Club buttons and status dots stay circular. Use the tokens in `web/studio.css`:
   navy text, cobalt primary/selection, green success, amber warning, red error/destructive. Type
   scale: page headings 32 px (28 px on phones), panel headings 20, body 14, secondary 13, latest
   metrics 36. Wrap rather than shrink.
8. **Device targets.** The primary target is iPad Pro 13"/12.9" landscape. Check CSS viewports
   1376×1032, 1366×1024 and 1366×900, plus a smaller tablet and a ~390 px phone. Touch targets are
   at least 44 px, and nothing essential may depend on hover. Wide tables scroll inside their own
   container. Record emulated viewports separately from real iPad Safari checks.
9. **Responsive service, recoverable data.** UI work and requests must never block shot intake.
   Report failed saves visibly, ignore stale responses, and reconnect from an authoritative snapshot.
10. **Verify the whole journey.** Enter, act, cancel, leave and return. Cover live, completed,
    abandoned, review-only, empty and error states, at the top of the screen and after scrolling.
    Record what was actually verified, and what was not, in WORK_LOG.md.

Play, Range, Analyze, course artwork and replay have more detailed rules in the later sections of
DESIGN_PRINCIPLES.md. Read the relevant section before changing those features.

## Code conventions

- Python is formatted with `ruff format` (line length 100, quote style preserved) and web
  JS/CSS/test modules with prettier 3.6.2 using `.prettierrc.json`. Run the formatters on files you
  change. Keep formatting-only changes in their own commit and add its hash to
  `.git-blame-ignore-revs`. Prettier leaves HTML template literals as written, so keep new
  templates readable by hand.
- UI is built from template strings assigned to `innerHTML`. Escape every interpolated value
  with `esc()`/`escape()` from `web/charts.js`, or use `textContent`. Golfer, bag, club, tag and
  course names are user input.
- Request bodies are Pydantic models with `extra="forbid"` and explicit bounds. New endpoints follow
  the same pattern and the same-origin and local-host middleware in `web_app.py`.
- Blocking SQLite or CPU work called from an endpoint runs in `asyncio.to_thread` and takes
  `store.lock`/`store.transaction()`. Remember the event loop also takes that lock, so keep
  lock-held work short.
- Adding a drill currently touches `DRILLS`, `PracticeParams` and `create_practice` (web_service/
  web_app), the field-set constants, `restore_model` (distance_ladder.py), `publish_context`,
  the web router and practice categories, plus NAVIGATION.md. A feature registry is planned
  (architecture plan, stage 4).
- New behavior needs tests: `tests/test_*.py` (unittest, temp-dir `GolfService`) for the service
  and storage, and `tests/test_*.mjs` (`node --test`) for browser helpers and controllers.

## Finishing a change

Follow "Finishing work" in AGENTS.md: verify journeys and layouts, run the suites, update
NAVIGATION/WORK_LOG/BACKLOG and the affected docs, then make one focused commit per feature and
report its hash. Separate implemented behavior from proposed or unverified behavior in every
document.
