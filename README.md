# TraceLoft

A local golf practice, play and analysis app with a source-neutral shot relay. The Python service
records shots and sessions in SQLite and serves the pure-white Vector web interface.

This repository contains no OCR, screen capture, calibration, training glyphs or private adapter
implementation. TraceCapture is a separate private application; TraceLoft does not import or launch
it. Any compatible local Open Connect producer can supply shots. The original combined repository
is retained privately, not imported into this repository's Git history.

## Start

On this PC, double-click **Launch TraceLoft.cmd**. Open **http://localhost:8765**.
TraceLoft automatically listens for GSPro Open Connect v1 JSON on **127.0.0.1:900**.
On Relay, choose **Off**, **GSPro** (921), or **Infinite Tees** (999). The choice saves immediately
and reconnects automatically. No rēlā adapter is needed. All three choices record incoming shots.
Use **Launch TraceLoft LAN.cmd** for browser access on your trusted local network. It also accepts
shots from other machines on port 900 (`--remote-input`, D66), such as rēlā in a VM or over a VPN.
This has no password: allow inbound TCP 900 in Windows Firewall, and never port-forward it to the
internet. The plain launcher keeps input local.
Closing the browser leaves the service running; **Stop TraceLoft.cmd** stops it. A normal restart
restores the unfinished session without adding or ending any shots.

Fresh Windows installation: install Python 3.12, run **Setup TraceLoft.cmd**, then launch.
Command-line alternative: `python -m venv .venv`, install `requirements-lock.txt` in it, then run
`python web_app.py`. `requirements-web.txt` lists the direct dependencies; the lock file pins the
verified transitive set. Development checks additionally use `requirements-dev.txt` (ruff). The
application modules also support ordinary Python/uvicorn on other hosts; Windows launch scripts
are the verified distribution path.

## Responsibilities

- **Relay**: accept a launch monitor or external adapter, preserve raw payloads, record first, and
  optionally forward documented Open Connect fields directly to a simulator.
- **Practice**: range, distance/putting ladders, bag mapping, wedge matrix and putting drills.
- **Play**: lightweight 2D golf, registered course artwork, terrain and historical dispersion preview.
- **Analyze**: multi-metric Trends, linked Explore filters and named Compare cohorts, with
  collapsible selections, multi-club colors, robust coverage and matching CSV exports.
- **Sessions**: review, end/abandon, recoverable deletion and restoration.

Use the header golfer button to select or create a local golfer, **Manage bags →
Specifications/Replace** for equipment, and Range's bulk **Tags** control for shot tags.

See the [Analyze guide](docs/ANALYZE.md) for chart selection, browser-saved dynamic views, source
versus calculation basis, cohort dates and inspection/export semantics.

## Play

Play uses a [map-first iPad layout](designs/play-map-first/README.md): a compact scorecard and
club row above the full-width course, with distance/lie/putting pace on the map. Expand Club
dispersion below the map for preview settings; its heatmap remains visible while collapsed.

The built-in library contains three original 18-hole courses:

- **Boulder Beach**: coastal, using the January 2026 Pebble Beach Blue tee yardages, **6,801
  yards, par 72**. See the [course guide](docs/PEBBLE_BOULDER.md) for controls, source details
  and current game limits.
- **Sheboygan Straits**: lakeside links with dense bunker complexes, Blue tees at **7,142 yards /
  par 72**, and original aerial artwork. See the [Sheboygan Straits guide](docs/SHEBOYGAN_STRAITS.md)
  for hole details and scoring rules.
- **Judges Course**: the supplied 18-hole yardages (6,163 yd/par 72), with generated
  wooded-parkland aerials inspired by the supplied maps and lakeside photographs. Map scale is
  approximate. See the [Judges Course guide](docs/JUDGES_COURSE.md).

New rounds use Boulder Beach **v3** and Sheboygan Straits **v2**. All 36 holes were checked against
their visible terrain; subsequent review refined Boulder fairways 6, 16 and 18. Existing rounds
retain their original boundaries. See the [full visual review](designs/course-registration/README.md).
The four earlier standalone holes are retired from new-round choices; saved rounds and imported
courses remain available.

Choose Play → a course → Set up round. All three courses offer **Full 18**, **Front 9 (1–9)** and
**Back 9 (10–18)**. Setup shows each option's par and yardage; the round ends at the final selected
hole. Existing rounds keep their selection. Complete each hole, then tap Next hole. The round saves
automatically in SQLite; its scorecard and individual holes are available in Sessions. End round
saves a partial round. **Mulligan** and **Misread** replay the latest scored shot, even after a
hole or round ends. Both are tracked; misreads are excluded from analysis, while mulligans retain
their analysis selection.

Play checks the carry landing surface: sand stops rollout, rough removes **75%** of remaining
rollout and out of bounds removes **100%** by default. Both percentages are adjustable in setup.
Final water/OB positions still incur the normal penalty. See [landing rules](docs/PLAY_LANDING_RULES.md).

Range's Flight profile and Play's map animate newly received shots. Source carry/total anchor
the replay when available; OpenGolfCoach supplies estimated flight shape and hang time. Roll
timing and the fitted path are illustrative. **Replay ball** and **Skip** never change scores or
shots. Reduced-motion preferences disable animation; opening/reloading a session does not replay
history. Play saves flight estimates for new full shots; older rounds keep their original data.

## Storage and contracts

The database is SQLite **schema 5**. It holds:

- 18 named source metrics, including reported total distance;
- immutable, versioned TraceLoft results (wide derived metrics);
- relational golfers, equipment/configurations, shot context, tags, collection plans and session state;
- SQL-backed Analyze;
- immutable bag/wedge cohorts;
- staged recalculation with explicit publication.

Existing IDs, raw evidence, sessions and game scores are preserved, and historical outcomes stay
pinned. Each upgrade creates a verified pre-upgrade backup; the frozen, numbered upgrade steps
and their SQL live in `migrations/`. Start with the
[readable shot database guide](docs/SHOT_DATABASE.md) and its ERD for SQL, exports and recovery.
The [redesign plan](docs/DATABASE_REDESIGN.md) records the design rationale and remaining proposals.

The existing database remains `%USERPROFILE%\GolfData\data\golfdata.sqlite3`, outside OneDrive.
`GOLFDATA_DATABASE` selects an isolated database; `TRACELOFT_INPUT_PORT` overrides 900.
The compatibility path preserves existing user data. SQLite snapshots and CSV export are available
on Relay. Google Drive backup remains planned.

See [Open Connect contract](docs/RELAY.md), [database operations](docs/DATABASE_OPERATIONS.md),
[design principles](DESIGN_PRINCIPLES.md), [navigation](NAVIGATION.md), [backlog](BACKLOG.md),
[decisions](DECISIONS.md), [work log](WORK_LOG.md) and the
[architecture plan](docs/ARCHITECTURE_IMPROVEMENTS.md). Development guidance for coding agents is in
[AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md).

The [approved ball-physics research plan](docs/BALL_PHYSICS_RESEARCH_PLAN.md) and
[research log](docs/BALL_PHYSICS_RESEARCH.md) cover flight, bounce, ground travel, lies and simulator
approaches for future browser simulation. Research findings are distinct from implemented physics.

## Verification and limits

Run `python verify.py`. It selects the project venv, runs the Python and JavaScript suites plus
ruff lint when installed, and writes logs plus a commit-linked JSON report outside the repository
(override with `--output-dir`). Node is found from `--node`, `TRACELOFT_NODE`, PATH or the standard
install folder. It exits nonzero when a suite fails or a required suite could not run. The suites
can also be run directly: `.venv\Scripts\python -m unittest discover -s tests` and
`node --test tests/*.mjs`. Browser/device journey checks are still separate; helper tests alone do
not verify the interface in a real browser. Use a separate database and input/HTTP ports for
state-changing checks.

Live browsers use `/ws?protocol=2` revision notifications and fetch `/api/state` on changes/recovery.
Idle connections send no repeated snapshots. Older clients/servers remain compatible during an
upgrade. Same-session repaints retain unfinished edits/focus; source data and scoring stay server-owned.
Revision checks, reports, exports, backups and session listings do not wait for the database writer
lock, so they cannot stall shot intake. State fetches still include full history; bounded/delta
detail reads are planned in the [architecture improvement plan](docs/ARCHITECTURE_IMPROVEMENTS.md).

The initial input profile accepts Yards/mph; unsupported units are rejected. Unknown vendor fields
are preserved as raw evidence rather than guessed into canonical metrics. A successful local save
is distinct from simulator delivery. Direct Infinite Tees heartbeat acknowledgement has been tested;
real putt/full-swing results through the new direct path still need verification.

OpenGolfCoach is a separately installed dependency; its notices/license remain under
`third_party/opengolfcoach`. Public publishing and final distribution/license review remain
separate work.
