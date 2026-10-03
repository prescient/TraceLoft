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

This repository contains no OCR, screen capture, calibration, training glyphs or private adapter
implementation. TraceCapture is a separate private application; TraceLoft does not import or launch
it. Any compatible local Open Connect producer can supply shots. The original combined repository
is retained privately, not imported into this repository's Git history.

## Storage and contracts

The existing database remains `%USERPROFILE%\GolfData\data\golfdata.sqlite3`, outside OneDrive.
`GOLFDATA_DATABASE` selects an isolated database; `TRACELOFT_INPUT_PORT` overrides 900.
The compatibility path preserves existing user data. SQLite snapshots and CSV export are available
on Relay. Google Drive backup remains planned.

See [Open Connect contract](docs/RELAY.md), [database operations](docs/DATABASE_OPERATIONS.md),
[design principles](DESIGN_PRINCIPLES.md), [navigation](NAVIGATION.md), [backlog](BACKLOG.md),
[decisions](DECISIONS.md) and [work log](WORK_LOG.md).

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
