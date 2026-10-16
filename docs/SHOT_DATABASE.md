# Readable shot database — schema 6

SQLite is authoritative at `%USERPROFILE%\GolfData\data\golfdata.sqlite3`, outside OneDrive.
The additive migration retains existing shot IDs, raw packets, reports, original units, sessions,
scores, inclusion decisions and correction history. [ERD](DATABASE_ERD.md) shows the main relationships.

## Start with these views

| View | Row meaning |
| --- | --- |
| `v_shots_source` | One physical shot and its explicitly selected source report |
| `v_session_current_metrics` | One attempt, golfer/equipment context, all source columns and selected analytical outputs |
| `v_session_shots` | One attempt with its original pinned flight/putting results for historical review |
| `v_session_equipment` | Original or corrected effective club/bag identity and configuration |
| `v_shot_tags` | Currently applied physical-shot or session-attempt tag associations |
| `v_bag_map_results` | One immutable per-club bag-map result with distance coverage/quartiles |
| `v_wedge_matrix_results` | One immutable club/swing cell with distance, launch and spin coverage |
| `v_calculation_history` | All derived versions, methodology, publication selection and recorded lineage |

Deleted sessions remain queryable for recovery. Everyday app analysis omits them and scopes by golfer.
Physical shots can appear in several sessions: Analyze counts attempts; calibration cohorts count
 distinct physical shots. Each metric has its own available count; missing readings are not zeros.

## Source columns

`shot_source_metrics` has one immutable normalized report per observation, linked by `shot_id`.
All 18 columns are first-class, including reported **total distance**. The producer should supply total;
legacy/other-source missing or invalid values remain null with quality evidence, never a modeled fallback.
No competing reports are blended. `shot_primary_source` explicitly selects a physical-shot report;
raw packets and all observations remain available. Reported Smash Factor stays separate from calculated.

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

## Source estimates (schema 6, D70)

`source_estimates` holds values a source estimated itself rather than measured, for example rēlā's
face angle, dynamic lie and loft, closure rate, impact location and carry for a Foresight LPi, which
measures none of them. One immutable row per observation and metric: `estimator` (e.g. `rela`),
`metric_key` and `real_value` in the canonical unit (`canonical_unit`), and the value as sent
(`source_field`, `source_value`, `source_unit`). They never enter `metric_values` or
`shot_source_metrics`, so analysis cannot mistake them for measurements. Compare them with
TraceLoft's own estimates (D64 `club_estimates`, D63 `range_vals`) by `shot_id`:

```sql
SELECT e.shot_id, e.metric_key, e.real_value AS rela_estimate, e.canonical_unit
FROM source_estimates e WHERE e.estimator = 'rela' ORDER BY e.shot_id, e.metric_key;
```


## Golfers, equipment and tags

The header golfer button creates/selects local profiles; finish or abandon an active session first.
Each profile owns its bags, sessions and analyses. Existing single-player sessions and linked shots
belong to My golfer; unassigned inbound history stays unassigned. Profiles do not add authentication.

`bags` and `clubs` identify physical equipment. `club_revisions` stores make/model/loft/shaft/settings;
`bag_revisions` and `bag_memberships` record membership and labels. Manage bags → Specifications
appends a configuration; renaming keeps physical identity/configuration; Replace makes a new physical
club. Immutable `shot_contexts` and frozen `session_plans` preserve historical selection/configuration.
Historical configurations that cannot be established remain unknown. Specified new configurations
cannot borrow unknown historical readings for calibration.

`tags` is the reusable vocabulary; `shot_tag_events` is an audited add/remove ledger, one association
per tag and scope. A shot may have many tags. Range → select shots → Tags supports attempt or physical
shot scope, add/remove and Undo. Tags never silently change inclusion. Analyze supports any/all tag matching.

Core state is relational. `session_fields`/`attempt_fields` use typed paths for varying drill settings,
ordered corrections and scalar outcomes. Browser JSON is reconstructed from these rows. Immutable JSON
is retained for original evidence, whole frozen course geometry, model parameters and trajectories;
legacy session payloads are not editable state or an analytical fallback.

## Collection results and Play

`analysis_runs` freezes a collection specification; `analysis_members` records exact physical shot,
report, equipment context, flight version and inclusion decisions. `collection_results`,
`group_metric_results` and `bag_gap_results` store median/type-7 quartiles and per-metric coverage.
Each cell uses the planned configuration and deduplicates physical shots. Cleanup creates a new
immutable cohort. The UI reads persisted cells instead of treating browser summaries as the authority.

On a sampled bag map/matrix choose **Use this collection in Play**. `equipment_profile_selection`
selects a cohort per golfer/bag/kind/data mode. Changes require review and republication; incompatible
configurations never pool. Recommendations and density previews share the same policy. Without explicit
publication, compatible historical collections remain available as before. Future previews use selected
analytical flight versions; completed rounds and original flight animations retain their saved pins.

## Recalculation and publication

Analyze → **Calculation methods and version history** → choose family → **Preview recalculation**.
The applied Analyze filters define the scope. Flight uses pinned OpenGolfCoach; putting can retain its
saved method or compare constant-Stimp/Fuse flat braking using frozen Stimp/target; source comparisons
calculate smash, absolute offline and signed reported-total-minus-carry rollout.

`calculation_runs` identifies an immutable model specification, not a lifecycle batch.
`recalculation_batches` records lifecycle; `recalculation_inputs` freezes exact report/attempt/equipment
context, inclusion, handedness, Stimp and target. `shot_derived_metrics` holds named outputs;
`calculation_inputs`/`calculation_lineage` record dependencies. The current implementations consume
source reports directly; they do not depend on earlier derived outputs. Saved legacy runs honestly
retain incomplete lineage and null historical code hashes. New batches hash actual adapter and installed
flight implementation code. Resume refuses to mix changed code into an old specification.

Preview shows ready/unavailable/error/pending coverage and scalar changes. Publication requires a
nonempty batch with every output ready, unchanged source/context/inclusion and a fresh selection token.
Errors, missing inputs and interrupted batches cannot replace selected results. Interrupted batches
resume their missing outputs idempotently. Old batches can be reviewed/refreshed and republished while
their inputs remain valid. Publication appends an audit with prior/result IDs; it never rewrites source,
historical attempt pins or scores. Selected calibration cohorts become stale if their flight versions change.

Use **Metric versions, configurations and tags → Metric values → Selected analytical calculations**
to analyze selected outputs. Source values remain the default. Choosing a calculated focus metric sets
that basis before Apply. Derived estimates and supplied launch/club inputs are labeled separately.

## Export and recovery

Analyze filtered CSV includes basis, shot/report/configuration/context IDs and selected model/result
IDs. Calculation history CSV contains all versions for the current golfer, including stale versions.
The full CSV ZIP includes entity/state/tag/cohort/batch/publication tables and the readable wide/history
views. ZIP is an all-database administrative export, including deleted/excluded shots and all golfers.
Spreadsheet text is escaped; genuine numeric values retain their signs.

Each existing-database schema upgrade makes a verified snapshot before its transaction. Schemas 2→3
reconcile every session DTO and evidence hash; later steps verify original evidence and foreign keys.
`schema_migration.v2` through `.v5` record the steps. An interrupted upgrade rolls back and can retry.
Restore accepts verified schemas 1–5 and creates a separate destination; older snapshots need the
matching older app or an upgrade. Keep snapshots before replacing the live file. See
[operations](DATABASE_OPERATIONS.md). Google Drive/off-device backup and remote authentication remain future work.
