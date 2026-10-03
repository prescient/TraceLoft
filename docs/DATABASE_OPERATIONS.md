# Source separation update — 2026-10-03

SQLite remains authoritative at the same path. TraceLoft stores raw Open Connect packets and mapped
observations, plus session state atomically. The source app keeps its own private outbox and cannot
read/write this database. TraceLoft acknowledges only after commit. See [Relay](RELAY.md) for retry,
unit and forwarding semantics. `relay_settings.v1` and `active_session.v1` metadata preserve destination
and normal-restart session continuity. No destructive schema change or data move is required.

Older operational notes below describe legacy import evidence. Acquisition, VDD calibration and crop
backups now belong to the separate private source application.

# SQLite storage and recovery

The web Python service owns TraceLoft's authoritative shot/session database. Default location:
`%USERPROFILE%\GolfData\data\golfdata.sqlite3`. Windows redirected AppData into the packaged Codex
cache during cutover, so the user-owned folder keeps data independent of Codex and OneDrive.
The OneDrive source folder is not the live database
location and OneDrive is not syncing. To isolate another instance, set `GOLFDATA_DATABASE` before
starting its Python process. Each service holds an exclusive owner lease for its database;
two services cannot independently score drills against the same file.

## Implemented foundation

- Course import packages now live in versioned `course_import.v1.*` metadata records, with original
  source JSON, geometry, scale transform, attribution and review timestamp. Rounds freeze a copy.
  SQLite snapshots include these records; no imagery downloads or SQL schema upgrade are involved.
  The opt-in Tour demo pack uses `tour_demo_pack.v1` for idempotency and normal synthetic receipts,
  session payloads and the shared bag catalog. See [demo data](TOUR_DEMO_DATA.md) and
  [course import](COURSE_ART_AND_IMPORTS.md). CSV remains a shot export, not a course export.

- Schema version 1: raw events, source/configuration/stream identity, physical shots, observations,
  typed definitions/values, mapping lineage, sessions/attempts, session-only inclusion history,
  recoverable deletion, delivery evidence, original import files and audits.
- The 73-entry researched catalog is loaded as definition capacity. The original seven speed/launch/spin
  fields retain their v1 mapping. Expanded table rows add seven optional flight fields through the
  separately archived v2 mapping: total, carry, offline, descent, peak height, curve and hang time.
  Original observations are unchanged; numeric flight reads still need live verification. See
  the private VDD calibration documentation. Vendor adapters, series ingestion, equipment specification revisions, courses,
  cross-session cleanup and automatic outliers remain proposed. Analyze now reads saved session attempts
  with date/session/equipment/intent filters, median/IQR and CSV; repeated physical shots used in
  multiple sessions can appear once per session, explicitly labeled in the UI.
  Production definitions/mappings are versioned under `data/`; research examples remain in `docs/data/`.
- Manual multiple bags/club labels are implemented for Distance ladder and Driving range. The versioned catalog lives
  in SQLite `metadata` under `equipment_catalog.v1`; attempt payloads retain stable per-bag club IDs,
  bag/club names, catalog revision and manual-selection mode. Worker receipts freeze the selection
  at acceptance; catalog edits affect subsequent shots. Snapshots include the catalog. No new SQL
  tables/schema version. Range bulk corrections are stored as audited attempt overlays; full physical-equipment
  revisions and GSPro following remain proposed; measured `reported_club` is still the original source code, never overwritten.
- Canonical ball speed is m/s; wide export reports mph. Angles remain degrees, spin RPM. Missing and
  invalid values remain distinct from measured zero. Original field payloads survive.
- A receipt, its shot/observations, drill target/result and completion commit atomically. WAL, foreign
  keys, FULL synchronous mode and a bounded busy timeout are enabled. Worker receipts save durably
  before telemetry and are removed only after database acceptance. Restart recovery is idempotent
  and never resends a stored receipt to GSPro.
- Existing CSV/JSON originals remain preserved evidence; session operations use SQLite. Capture CSV
  remains a diagnostic journal. Do not edit old files to edit the app. Recording/practice now use the
  web studio; desktop tools retain preview, calibration and teaching. An already-open desktop window
  must use the web studio for further recording.

Session payload JSON inside SQLite preserves the frontend contract and unknown legacy fields.
Full-swing Distance ladder uses the same schema with yard-based targets/results and explicit
scored/unscored attempt state. Its selected distance, error, window and manual label export in
separate `*_yd`/availability columns; putting feet/model outcomes remain distinct. See
[distance ladder](DISTANCE_LADDER.md). No schema upgrade or rewrite of existing sessions is required.
Relational attempts and typed observations are maintained transactionally alongside it. Exclusions
affect that session only; deletion changes a recoverable flag without deleting raw shots, logs, crops
or training archives. Review does not resume an interrupted drill.

## Migration

From the repository, with web/desktop capture stopped:

```powershell
.venv\Scripts\python.exe -B database_tools.py migrate --dry-run
.venv\Scripts\python.exe -B database_tools.py migrate
```

Dry run inventories/hashes sources without creating a database. Migration requires the service owner
lease, creates a verified ZIP of CSV/JSON/trash/configuration/glyph files, and imports transactionally.
Source bytes are also embedded in database import evidence. A report and verified SQLite snapshot
are saved under the data/backups locations. First startup performs the same archive/import if no
completed migration exists. Future SQL upgrade versions need a pre-upgrade snapshot and their own
verified migration before support is added.

Explicit historical `ok` notes establish CSV acceptance, including GSPro-off shots. Other notes stay
unknown unless uniquely matching confirmed practice evidence resolves them. Distinct files with
colliding keys do not merge; identical CSV file copies do not duplicate events. Precise practice and
rounded CSV values remain separate observations of a linked shot. Unchanged reimports add no data;
changed imported originals require explicit reconciliation and are rejected. Conflicting session
copies abort the transaction. Original timestamps survive: CSV local time has no proven timezone,
while practice/worker receipt times retain their recorded offset/UTC basis.

## CSV export and local backups

Use **Capture → Data & backups → Export CSV / Back up database**. Export downloads a ZIP with
`shots.csv`, `metric_values.csv`, `session_attempts.csv` and a manifest from one committed snapshot.
Frozen metric definitions/mappings accompany the export as JSON dictionaries. Long export includes
failed/unknown observations with an empty shot ID and explicit acceptance/availability.
Wide export has one row per physical shot; long export preserves all observations and their
definitions/units/methods/variants. Attempts retain targets, success and exclusions. Excluded and
deleted-session data remains in this all-captured export with flags. Unavailable wide cells are blank;
formula-leading text receives an apostrophe for spreadsheet safety. Analytical filters/summary exports
remain follow-ups. Full-swing attempt CSV includes `bag_id`, `bag_name`, `club_id`, `club_label`,
`catalog_revision` and `selection_mode`; old untagged attempts remain blank. Putting estimates now
have explicit distance/model/Stimp/target/rung columns in `session_attempts.csv`; `putting_models.json`
preserves per-session assumptions and source identity. Derived travel remains separate from measured
metrics; historical outcomes are never recomputed on review. No SQL schema upgrade is needed for these
existing session/attempt payload fields. See [distance models](PUTTING_DISTANCE.md).

Local snapshots run after manual/automatic completion or abandonment, at service shutdown, during
migration and on request. They use SQLite's backup API, integrity/foreign-key checks, counts and a
SHA-256 manifest. Snapshots use a standalone journal format. Do not copy just the live main file:
committed data may be in its WAL. Backup failure does not undo a saved session. Retention/settings and
scheduled backups remain follow-ups; snapshots are currently retained. Protect crop/training archives
separately.

```powershell
.venv\Scripts\python.exe -B database_tools.py backup
.venv\Scripts\python.exe -B database_tools.py export --output "$env:USERPROFILE\Downloads\traceloft-export.zip"
```

Restore verifies checksum, schema, integrity, foreign keys and counts, then creates a **new**
destination; it refuses to overwrite an existing database. Test the restored copy separately:

```powershell
.venv\Scripts\python.exe -B database_tools.py restore --snapshot "C:\path\golfdata-snapshot.sqlite3" --output "C:\path\recovery\golfdata.sqlite3"
```

For recovery, stop TraceLoft, restore to a new location and set `GOLFDATA_DATABASE` to that verified
file before launching. Keep the originals for investigation. The owner lock is not a backup dependency.
Unacknowledged receipts in data/receipts are recovery evidence outside a completed snapshot; do not
discard them when recovering a failed service.

## Google Drive follow-up

Requested after migration: upload completed, verified snapshots and manifests to a chosen private
Google Drive folder. Keep live SQLite/WAL files local. Proposed steps: finish and verify the snapshot,
upload the finalized file/manifest pair, record destination/version/hash and success, retry failed
uploads without duplicate versions, and periodically download/restore into isolation. Plan training
archive/configuration protection separately.

Account/folder selection, authentication, schedule, retention and restore verification remain to be
designed and connected. No Drive upload or scheduled job is implemented; backups are **local-only**.
See [the backlog](../BACKLOG.md) and [full schema proposal](../DATABASE_PROPOSAL.md).


## Range models, cleanup and demo data

Range sessions/attempts preserve frozen target/equipment context, OpenGolfCoach inputs/version/
assumptions/results and separate correction overlays in their existing payload JSON. Cleanup commits
atomically with an audit entry and revision; its before/after history supports Undo. Raw captures and
original manual tags are never rewritten by cleanup. No schema-version migration is required.

Demo sessions carry `demo=true`; generated events/attempts carry `simulated=true`, and metric methods
use `synthetic_demo`. Full shot CSV includes `simulated`; attempt CSV includes flags, corrections and
flight payloads. Range-filtered CSV adds explicitly named model fields and both tag versions.
Exclude synthetic data from research/skill analyses. Deleting a demo/session is recoverable and does
not purge its raw observations or crop/training backups. See [range operation](DRIVING_RANGE.md).

## Collection and game payloads — 2026-10-02

Bag/matrix plans and immutable swing labels use existing session/attempt JSON payloads. The basic
2D game adds a frozen original course, settings, source readings and versioned before/after outcomes,
including penalties, concessions, aim and random draws. No SQL schema migration is required.
Session exclusions never recalculate the played game. Verified SQLite snapshots contain all payloads;
advanced relational course/event queries and outcome-specific CSV exports remain follow-ups.

Analytics development history is installed atomically by the owning service at
`POST /api/demo/analytics-pack`. The `analytics_demo_pack.v1` metadata marker makes loading
idempotent; new demo bags, receipt provenance, session flags and cleanup history remain isolated
from measured sessions. Existing sessions and the active round are preserved. This adds data to
the existing schema, not a migration. See [dataset details](ANALYTICS_RESEARCH.md).

## TraceLoft branding compatibility — 2026-10-02

The app was renamed from GolfData to TraceLoft. Database/backup paths, the
`GOLFDATA_DATABASE` override, stable IDs and owner locks retain their original names.
No schema migration or data move is involved. New user-downloaded exports use `traceloft-`
filenames; existing archives remain valid. Both old and new launcher names work.


## Course workbench drafts

`course_draft.v1.<uuid>` metadata holds version-1 import params (original source, settings and optional
local-yard corrections), updated timestamp and optimistic revision. Draft updates check revision
inside the SQLite transaction; stale writers receive a conflict without changing the server copy.
Backup/restore includes drafts. They are separate from sessions and immutable `course_import.v1.*`
packages. New publications also retain params; old packages remain readable without that field.
Exported draft JSON is portable but is not a replacement for the complete database backup.
See [course import workflow](COURSE_IMPORT_WORKFLOW.md).
