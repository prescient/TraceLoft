# TraceLoft

A local golf practice, play and analysis app with a source-neutral shot relay. The Python service
records shots and sessions in SQLite and serves the pure-white Vector web interface.

## Start

On this PC, double-click **Launch TraceLoft.cmd**. Open **http://localhost:8765**.
TraceLoft automatically listens for GSPro Open Connect v1 JSON on **127.0.0.1:900**.
On Relay, choose **Off**, **GSPro** (921), or **Infinite Tees** (999). The choice saves immediately
and reconnects automatically. No rēlā adapter is needed. All three choices record incoming shots.
Use **Launch TraceLoft LAN.cmd** for browser access on your trusted local network. Input stays local.
Closing the browser leaves the service running; **Stop TraceLoft.cmd** stops it. A normal restart
restores the unfinished session without adding or ending any shots.

Fresh Windows installation: install Python 3.12, run **Setup TraceLoft.cmd**, then launch.
Command-line alternative: `python -m venv .venv`, install `requirements-web.txt` in it, then run
`python web_app.py`. The application modules also support ordinary Python/uvicorn on other hosts;
Windows launch scripts are the verified distribution path.

## Responsibilities

- **Relay**: accept a launch monitor or external adapter, preserve raw payloads, record first, and
  optionally forward documented Open Connect fields directly to a simulator.
- **Practice**: range, distance/putting ladders, bag mapping, wedge matrix and putting drills.
- **Play**: lightweight 2D golf, registered course artwork, terrain and historical dispersion preview.
- **Analyze**: session/date/equipment filters, robust summaries, trends and CSV export.
- **Sessions**: review, end/abandon, recoverable deletion and restoration.

Play uses a [map-first iPad layout](designs/play-map-first/README.md): a compact scorecard and
club row above the full-width course, with distance/lie/putting pace on the map. Expand Club
dispersion below the map for preview settings; its heatmap remains visible while collapsed.

Range's Flight profile and Play's map animate newly received shots. Source carry/total anchor
the replay when available; OpenGolfCoach supplies estimated flight shape and hang time. Roll
timing and the fitted path are illustrative. **Replay ball** and **Skip** never change scores or
shots. Reduced-motion preferences disable animation; opening/reloading a session does not replay
history. Play saves flight estimates for new full shots; older rounds keep their original data.

Play checks the carry landing surface: sand stops rollout, rough removes **75%** of remaining
rollout and out of bounds removes **100%** by default. Both percentages are adjustable in setup.
Final water/OB positions still incur the normal penalty. See [landing rules](docs/PLAY_LANDING_RULES.md).

Play also includes **Sheboygan Straits**, an 18-hole lakeside links course with dense bunker
complexes, Blue tees at **7,142 yards / par 72**, and original aerial artwork. Select it in Play.
See the [Sheboygan Straits guide](docs/SHEBOYGAN_STRAITS.md) for hole details and scoring rules.

The built-in library contains Sheboygan Straits, Boulder Beach and **Judges Course**.
Judges Course uses the supplied 18-hole yardages (6,163 yd/par 72), with generated wooded-parkland
aerials inspired by the supplied maps and lakeside photographs. Map scale is approximate.
See the [Judges Course guide](docs/JUDGES_COURSE.md). The four earlier standalone
holes are retired from new-round choices; saved rounds and imported courses remain available.

Boulder Beach now uses **v3** and Sheboygan Straits **v2** for new rounds. All 36 holes were checked
against their visible terrain; subsequent review refined Boulder fairways 6, 16 and 18.
Existing rounds retain their original boundaries. See the [full visual review](designs/course-registration/README.md).

Play includes **Boulder Beach**, an original 18-hole coastal course using the January 2026 Pebble
Beach Blue tee yardages: **6,801 yards, par 72**. Choose Play → Boulder Beach → Set up round.
All three courses offer **Full 18**, **Front 9 (1–9)** and **Back 9 (10–18)**. Setup shows each option's
par and yardage; the round ends at the final selected hole. Existing rounds keep their selection.
Complete each hole, then tap Next hole. The round saves automatically in SQLite; its scorecard and
individual holes are available in Sessions. End round saves a partial round. **Mulligan** and
**Misread** replay the latest scored shot, even after a hole or round ends. Both are tracked;
misreads are excluded from analysis, while mulligans retain their analysis selection. See the
[course guide](docs/PEBBLE_BOULDER.md) for controls, source details and current game limits.

This repository contains no OCR, screen capture, calibration, training glyphs or private adapter
implementation. TraceCapture is a separate private application; TraceLoft does not import or launch
it. Any compatible local Open Connect producer can supply shots. The original combined repository
is retained privately, not imported into this repository's Git history.

## Storage and contracts

The existing database remains `%USERPROFILE%\GolfData\data\golfdata.sqlite3`, outside OneDrive.
`GOLFDATA_DATABASE` selects an isolated database; `TRACELOFT_INPUT_PORT` overrides 900.
The compatibility path preserves existing user data. SQLite snapshots and CSV export are available
on Relay. Google Drive backup remains planned.

Schema 2 separates 18 named source metrics (including reported total distance) from immutable,
versioned TraceLoft results. Existing IDs, raw evidence, sessions and game scores are preserved;
upgrade creates a verified pre-upgrade backup. See [readable shot database](docs/SHOT_DATABASE.md)
for SQL, exports and recovery. The broader [redesign plan](docs/DATABASE_REDESIGN.md) still tracks
users, relational equipment/context/plans, group results and the recalculation interface.

See [Open Connect contract](docs/RELAY.md), [database operations](docs/DATABASE_OPERATIONS.md),
[design principles](DESIGN_PRINCIPLES.md), [navigation](NAVIGATION.md), [backlog](BACKLOG.md),
[decisions](DECISIONS.md) and [work log](WORK_LOG.md).

The [approved ball-physics research plan](docs/BALL_PHYSICS_RESEARCH_PLAN.md) and
[research log](docs/BALL_PHYSICS_RESEARCH.md) cover flight, bounce, ground travel, lies and simulator
approaches for future browser simulation. Research findings are distinct from implemented physics.

## Verification and limits

Run `.venv\Scripts\python -m unittest discover -s tests` and `node --test tests/*.mjs`.
Use a separate database and input/HTTP ports for state-changing checks.
The initial input profile accepts Yards/mph; unsupported units are rejected. Unknown vendor fields
are preserved as raw evidence rather than guessed into canonical metrics. A successful local save
is distinct from simulator delivery. Direct Infinite Tees heartbeat acknowledgement has been tested;
real putt/full-swing results through the new direct path still need verification.

OpenGolfCoach is a separately installed dependency; its notices/license remain under
`third_party/opengolfcoach`. Public publishing and final distribution/license review are separate
from this local repository split. This change does not push or publish either repository.
