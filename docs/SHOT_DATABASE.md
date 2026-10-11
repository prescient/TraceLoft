# Readable shot database — schema 3

Schema 3 adds local golfers, relational equipment revisions/membership, immutable shot contexts,
audited many-to-many tags, frozen collection plans and typed session/attempt state. The browser
receives compatible JSON DTOs assembled from relational rows. Legacy payloads are immutable evidence.

Use the header golfer button to create/select profiles; end/abandon active sessions before switching.
Each golfer has independent bags/history. Existing single-player sessions and linked shots belong to
My golfer; unassigned inbound history remains unassigned. Profiles do not add authentication.

Manage bags → Specifications appends configurations; cosmetic rename keeps physical identity and
configuration. Replace creates a new physical club. Old labels/configuration links and plans stay
frozen. Unknown historical configuration lineage remains null. Range → select shots → Tags supports
audited add/remove, physical-shot/attempt scope and Undo; tags never change analytical inclusion.

Readable context views: `v_session_equipment`, `v_session_state`, `v_attempt_outcomes`, `v_shot_tags`.
`session_fields`/`attempt_fields` retain variable drill settings, scalar outcomes and ordered
correction history as typed leaves with readable paths, including empty/null/list distinctions.
Frozen course geometry/model artifacts retain JSON; legacy payloads are not editable fallbacks.

The v2 → v3 upgrade creates a verified snapshot, then backfills and compares every reconstructed
session DTO and original evidence hashes transactionally. Failure rolls back; `schema_migration.v3`
records the result. Restore accepts versions 1–3. CSV ZIP includes the new entity/context/plan/state/
tag tables and equipment view. The schema-2 numerical design below remains in place.

The first stage of the [database redesign](DATABASE_REDESIGN.md) is implemented. SQLite retains
the same file, shot IDs, raw packets, observations, original typed metrics and saved game/drill
outcomes. Named source columns and separately versioned calculations now support direct SQL and
CSV without pivoting the metric registry. This is not the completed users/equipment/session migration.

## Source reports

`shot_source_metrics` contains one report per observation, linked by `shot_id` and `observation_id`.
It has all 18 core columns, including **reported total distance**. Source total is used directly;
modeled total is separate. No report silently supplies another report's missing values.

| Column | Unit |
| --- | --- |
| `club_head_speed_mph` | mph |
| `smash_factor` | ratio supplied by source |
| `club_path_deg` | degrees |
| `angle_of_attack_deg` | degrees |
| `carry_distance_yd` | yards |
| `total_distance_yd` | yards |
| `ball_speed_mph` | mph |
| `total_spin_rpm` | rpm |
| `vertical_launch_angle_deg` | degrees |
| `horizontal_launch_angle_deg` | degrees |
| `spin_tilt_axis_deg` | degrees |
| `back_spin_rpm` | rpm |
| `side_spin_rpm` | rpm |
| `ball_apex_ft` | feet |
| `ball_descent_angle_deg` | degrees |
| `ball_offline_yd` | signed yards |
| `ball_curve_yd` | signed yards |
| `hang_time_s` | seconds |

These columns always exist. A numerical cell is nullable solely to preserve missing/invalid source
evidence, including old putting records and ordinary Open Connect packets that do not report distance.
Their absence never becomes zero or an estimated source value. Total distance is a first-class metric,
not an optional schema extension. Source quality has explicit `available`, `unavailable`, `invalid`
and `not_supplied` rows, with source field/unit/method/semantic variant.

`shot_primary_source` selects a complete report for everyday physical-shot queries. Its v1 policy
prefers the exact accepted receipt except legacy CSV, then live/practice/legacy-practice/legacy-CSV
evidence. Equally ranked conflicting reports remain unselected. Stable ordering is used only for
compatible ties. Manual policies can be introduced later without automatic replacement. All other
reports remain queryable. Current production history has both receipt and practice observations;
the migration does not turn them into additional physical shots.

```sql
SELECT shot_id, occurred_at, ball_speed_mph,
       carry_distance_yd, total_distance_yd, ball_offline_yd
FROM v_shots_source
ORDER BY occurred_at;

SELECT column_name, availability, source_unit
FROM source_metric_quality
WHERE report_id = :report_id;
```

Normalized mapping v2 adds source `smash_factor`; prior mapping files/definitions remain immutable.
The durable envelope's internal mapping label stays stable for old receipt retries, while new
observations reference the archived v2 specification. Use `TraceLoft.Metrics.smash_factor` for a
supplied value; TraceLoft does not infer this source cell from speeds. Neither the columns nor mapping
produce club readings absent from the source app.

## Derived results and saved outcomes

- `calculation_runs`: model family/version, output revision, parameters, provenance and optional
  genuine code hash. Each stage-1 specification groups its per-shot results; there is no batch
  recalculation scheduler/publication UI yet.
- `shot_derived_metrics`: immutable wide scalar results linked to shot, run, input fingerprint and
  non-null context identity. Flight includes carry/total endpoints, apex, descent, hang time and shape.
  Putting includes estimated distance, target/error and Stimp. Source features include absolute
  offline, calculated Smash Factor and the signed reported-total-minus-carry difference.
- `calculation_inputs`: the exact source report used by the result; composite keys reject another
  shot's report. Dependency graphs between calculation families remain a later migration stage.
- `shot_trajectories`: immutable complete sampled paths, outside the scalar metric table.
- `derived_metric_selection`: the explicitly selected analytical result per shot/family/context.
- `attempt_derived_results`: pinned flight/putting result for each original practice/game attempt.
  Analytical version selection does not replace these pins or rescore the round.

Historical saved estimates are extracted without rerunning their models. Their provenance is
`legacy_saved_outcome_incomplete_lineage`, with no invented code hash or computation timestamp:
`created_at` records extraction, not an unknown original calculation time. Newly saved attempt
artifacts are labeled `saved_attempt_snapshot`; the existing model ID/inputs/assumptions remain
available, and complete code/dependency lineage is still follow-up work. Complete immutable result
artifacts remain evidence/compatibility documents; scalar columns drive numerical reads.

`Store.write_derived_result(...)` appends or idempotently retries a result. `select=True` explicitly
publishes that individual analytical result. Old versions remain available. Multi-shot staging,
coverage review, interrupted-run recovery and atomic group-profile publication are not implemented
by this initial API. Current drills continue to save their live outcomes under their existing rules.

```sql
SELECT shot_id, model_family, context_id, model_version,
       calculated_smash_factor, absolute_offline_yd,
       total_distance_yd, model_total_distance_yd
FROM v_shots_analysis
WHERE model_family = 'source_features' AND context_id = 'shot';

SELECT session_id, ordinal, shot_id, excluded,
       total_distance_yd, model_total_distance_yd,
       estimated_distance_ft, putting_result_id
FROM v_session_shots
WHERE session_id = :session_id
ORDER BY ordinal;
```

`v_shots_source` has one row per physical shot. `v_session_shots` has one per session attempt,
including excluded/deleted history; filter intentionally for an analysis. `v_shots_analysis` has one
row per selected shot/family/context (or one null-result row). Always filter family/context before
aggregating so different calculations do not multiply shots. It exposes no automatic source/model
coalescing. Bag/club names/tags and user ownership await the relational context migration; use current
app exports for those labels meanwhile.

## Upgrade, export and recovery

Stop the owning service before offline upgrade. Startup also performs the upgrade while holding its
normal owner lease. A verified schema-1 snapshot/manifest is created first; all DDL/backfill and the
schema marker commit together. An interruption rolls back to schema 1. Typed-row SHA-256 manifests
reconcile original evidence, sessions, attempts and game outcomes exactly, in addition to counts and
foreign keys. The migration report lives in `metadata.schema_migration.v2` and records the backup.

```powershell
.venv\Scripts\python.exe -B database_tools.py upgrade --dry-run
.venv\Scripts\python.exe -B database_tools.py upgrade
```

CSV ZIP export retains its earlier files and adds source reports/quality/selection, derived results,
calculation runs/inputs/selection, attempt pins and paths. The existing `shots.csv` distance row now
uses one explicitly selected report rather than choosing individual fields from different reports.
Wide report exports retain all 18 columns and every competing report. Missing cells are blank.
`shots_source.csv` is the simple 18-metric export with one selected report per physical shot;
`session_shots_wide.csv` has one row per attempt with pinned outcomes. The manifest documents row
shapes so all-report/all-version exports are not mistaken for extra physical shots.

CLI backup/export/upgrade require the owner lease; stop the running service or use Relay's existing
in-app backup/export actions. Restoring accepts verified schema-1 or schema-2 snapshots into a new
destination. Opening a restored v1 snapshot in this version upgrades it with another verified backup.
To roll back software, use the pre-upgrade schema-1 snapshot with matching schema-1 code. Do not open
schema 2 with the older app. Backups remain local; Google Drive is still planned.

## Remaining migration work

Versioned bag-map/matrix cohorts/profile selection, SQL-backed Analyze filtering and full calculation
lineage/recalculation UI remain tracked in [the backlog](../BACKLOG.md). Core equipment, context and
session authority are relational in schema 3; numerical storage retains the schema-2 layout.

## Schema 4 analytical collections

Analyze joins source/selected derived columns, golfer ownership and effective equipment context directly in SQL. Tags use EXISTS (any/all), configurations have a separate filter, and source-reported values remain the default. Collection results live in `analysis_runs`, `analysis_members`, `collection_results`, `group_metric_results` and `bag_gap_results`; `v_bag_map_results` and `v_wedge_matrix_results` are readable views. Each cell counts distinct physical shots matching its frozen planned configuration. Removing/excluding/retagging creates a new immutable cohort.

Use **Use this collection in Play** on a sampled map/matrix to select that bag’s reference for that data mode. Changed cohorts require review and republication; incompatible equipment configurations do not pool. Original historical configurations that cannot be established stay unknown. Future predictions use selected analytical flight outputs; saved rounds/reviews retain their original pins. Recommendations use the same ownership/configuration/profile policy.
