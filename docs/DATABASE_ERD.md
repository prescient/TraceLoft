# TraceLoft database relationships — schema 6

These diagrams show the principal implemented relationships. Auxiliary mapping/quality/import,
typed-state and audit tables are described in [the database guide](SHOT_DATABASE.md).
Names match SQLite. Ownership is explicit through `session_owners` and `shot_owners`; unknown
inbound ownership is allowed. Local profiles are independent of authentication.

```mermaid
erDiagram
    users ||--o{ bags : owns
    users ||--o{ clubs : owns
    users ||--o{ session_owners : owns
    users ||--o{ shot_owners : owns
    sessions ||--|| session_owners : attributed_to
    shots ||--o| shot_owners : attributed_to
    bags ||--o{ bag_revisions : changes
    bag_revisions ||--o{ bag_memberships : contains
    clubs ||--o{ club_revisions : configured_as
    club_revisions ||--o{ bag_memberships : installed_as
    sessions ||--o{ session_attempts : records
    shots ||--o{ session_attempts : used_in
    session_attempts ||--o{ shot_contexts : freezes
    bag_memberships o|--o{ shot_contexts : identifies_equipment
    session_attempts ||--o| context_selection : selects_original_and_correction
    sessions ||--o{ session_plans : freezes
    session_plans ||--o{ session_plan_items : orders
    users ||--o{ tags : defines
    tags ||--o{ shot_tag_events : applied_or_removed
    shots ||--o{ shot_tag_events : tagged
    session_attempts o|--o{ shot_tag_events : optionally_scoped_to
```

```mermaid
erDiagram
    shots ||--o{ observations : observed
    observations ||--|| shot_source_metrics : normalized_report
    shots ||--o| shot_primary_source : chooses_report
    shot_source_metrics ||--o{ source_metric_quality : explains_availability
    observations ||--o{ source_estimates : source_also_estimated
    shots ||--o{ shot_derived_metrics : calculated_versions
    calculation_runs ||--o{ shot_derived_metrics : specifies_method
    shot_source_metrics ||--o{ calculation_inputs : exact_source_dependency
    shot_derived_metrics ||--o{ calculation_inputs : records_input
    shot_derived_metrics ||--o| shot_trajectories : sampled_path
    shot_derived_metrics ||--o{ derived_metric_selection : selected_for_analysis
    session_attempts ||--o{ attempt_derived_results : original_pin
    shot_derived_metrics ||--o{ attempt_derived_results : frozen_result
    users ||--o{ recalculation_batches : stages
    recalculation_batches ||--o{ recalculation_inputs : freezes_inputs
    shot_contexts o|--o{ recalculation_inputs : equipment_context
    recalculation_inputs ||--o| recalculation_outputs : produces
    shot_derived_metrics ||--o{ recalculation_outputs : result
    shot_derived_metrics ||--o{ calculation_lineage : traces_batch_input
    recalculation_inputs ||--o{ calculation_lineage : exact_context_dependency
    recalculation_batches ||--o{ calculation_publications : published
    calculation_publications ||--o{ calculation_publication_items : previous_and_selected_results
```

```mermaid
erDiagram
    users ||--o{ analysis_runs : owns
    sessions ||--o{ analysis_runs : collection_versions
    analysis_runs ||--o{ analysis_members : freezes_cohort
    session_attempts ||--o{ analysis_members : exact_attempt
    shot_source_metrics ||--o{ analysis_members : exact_report
    shot_contexts o|--o{ analysis_members : exact_equipment
    shot_derived_metrics o|--o{ analysis_members : exact_flight_version
    analysis_runs ||--o{ collection_results : club_swing_cells
    club_revisions o|--o{ collection_results : planned_configuration
    collection_results ||--o{ group_metric_results : coverage_and_quartiles
    analysis_runs ||--o{ bag_gap_results : adjacent_distance_gaps
    sessions ||--o| collection_analysis_selection : current_cohort
    analysis_runs ||--o{ collection_analysis_selection : selected
    analysis_runs ||--o{ equipment_profile_selection : published_for_play
    bags ||--o{ equipment_profile_selection : bag_reference
```

`shot_source_metrics` holds all 18 core reported columns, including total. `shot_derived_metrics`
holds calculated columns. Join each to `shots.id` through `shot_id`; multiple reports/versions are
intentional. Use the selected-source/current-attempt views for ordinary analysis, rather than a
raw many-report/many-version join that would multiply shots.

JSON is immutable evidence or a whole model/geometry/trajectory artifact. Bags, configurations,
tag associations, collection membership and numeric measurements are relational. Variable drill
state uses typed paths in `session_fields`/`attempt_fields`; compatible browser DTOs are assembled
from those rows. Scores and original model pins are never replaced by analytical publication.
