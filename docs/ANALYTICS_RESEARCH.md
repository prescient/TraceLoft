# Cross-session analytics research and selected design

Reviewed 2026-10-02 using vendor documentation. These are workflow references, not integrations
or claims of mathematical equivalence.

## Primary-source findings

- Trackman's [Map My Bag](https://www.trackman.com/blog/know-your-numbers-introducing-map-my-bag-in-tps-10-1)
  describes saved club profiles with carry, total, dispersion and gaps. Adopt persistent equipment
  identity and useful distance comparisons. Our median/IQR convention is our own explicit choice.
- Trackman's [Golf Pro 4.3 release notes](https://support.trackmangolf.com/hc/en-us/articles/43183132290459-Golf-Pro-App-New-Features-in-Golf-Pro-App-4-3)
  describe grouped comparisons and alternate dispersion/trajectory/club views. Adopt drill-down from
  summary to session evidence, with equipment and intent filters rather than one mixed average.
- Trackman's [Performance Center](https://www.trackman.com/blog/performance-center-better-practice-and-feedback)
  emphasizes situational practice and benchmarked strokes gained. Defer such claims here until saved
  course outcomes and a documented benchmark exist; launch readings alone cannot supply shot cost.
- FlightScope's [FS Golf listing](https://apps.apple.com/us/app/fs-golf/id1492232632), published by
  FlightScope, describes configurable data presentations and min/max Data Margins. Adopt selectable
  focus metrics and clear units; our existing drill windows handle target feedback.
- FlightScope's [Trajectory Optimizer](https://flightscope.com/blogs/blogs/how-to-use-flightscope-s-trajectory-optimizer)
  contrasts selected-shot conditions with modeled alternatives. Preserve the distinction between
  source values and flight estimates. Do not call our OpenGolfCoach estimates an optimized swing.
- FlightScope's [Swing Training announcement](https://flightscope.eu/blogs/news/flightscope-adds-new-swing-training-feature-and-range-ball-setting-to-its-mevo-product)
  motivates historical benchmarking and progress review. Compare like equipment/intents and retain
  sample sizes and exclusion denominators; changed sampling/cleanup is not proof of improvement.

## Implemented first release

Analyze filters saved, non-deleted sessions by real/demo, practice type, recorded session start date,
session selection, bag, club and swing intent. Apply/refresh reads saved payloads; this is read-only
analysis, not a new writer. Default data is real and analysis scope is included.
Show median and type-7 IQR with per-metric counts, all non-removed comparison, manual exclusion
numerator/denominator, per-session median/IQR charts, reported distance/offline distribution,
equipment/swing comparison, session review links and filtered source-value CSV.

Date filters use recorded session dates; legacy timezone uncertainty is not silently repaired. Counts
are session attempts because exclusion scope belongs to a session; reused physical shots can appear
once per session. Removed attempts and deleted sessions are omitted. All scope deliberately includes
excluded attempts, but does not restore removed ones. No automatic outlier classification is claimed.
Real and synthetic sessions cannot be pooled. Wedge swing labels form separate comparison groups.
Existing untagged sessions remain untagged. Missing measurements are omitted per metric, never zero.

Trends show up to 24 recent sessions; scatter shows up to 500 available pairs, with displayed counts.
Statistics/export use the full filtered cohort. Source offline endpoint semantics are unverified,
so the scatter is explicitly not a validated landing map. Mixed-club/intent trends have an on-screen
warning; environmental normalization, uncertainty intervals and causal improvement claims are absent.

## Follow-ups

Automatic outlier review and policy-versioned rates; unique physical-shot analytical cohorts; saved
report definitions; environment/source capability filters; historical swing-tag correction; richer
course/benchmark analysis. Physical iPad/Safari and measurement accuracy still require live acceptance.

## Analytics development dataset — implemented 2026-10-02

A separate, idempotent `analytics_demo_pack.v1` supplies 624 explicitly synthetic shots in 20 saved
sessions over eight weekly dates ending yesterday. Two new bags, **Analytics lab A · DEMO** and
**Analytics lab B · DEMO**, each contain Driver, 5/7/9 iron, PW and SW. Sixteen range sessions
provide longitudinal comparisons; four wedge matrices separate Half, Three-quarter and Full.

Every value/trend is invented, not a Tour statistic or a player measurement. Inputs include
retained mishits, missing offline/descent/apex readings, 24 excluded simulated reading errors,
six recoverably removed warm-ups, and 16 audited forgotten-club corrections. This yields 594
included attempts / 618 non-removed attempts. Normal cleanup history supports Undo.

In Analyze, choose **Data → Demo sessions only**, then either Analytics lab bag. Start with
**7 iron / Carry** for eight session medians and spread, **9 iron** for excluded-data comparisons,
or **PW/SW + a swing intent** for wedge comparisons. Date filters, missing-value counts, CSV and
session review use the existing production paths. Other demo bags remain independently filterable.

Development loader: send a POST request to `http://localhost:8765/api/demo/analytics-pack`
with the service running. It commits atomically through the owning service, leaves active
selection/capture and old sessions intact, and returns saved IDs/counts. Repeating the request
does not duplicate or silently restore deleted demo sessions. Generated receipts have
simulated=true and synthetic_demo provenance; the pack marker and bag/session IDs live in
SQLite metadata and are included in normal backups. Delete demo sessions through normal
recoverable session deletion when no longer needed. No purge or database reset is performed
by the loader. Flight fields retain separate OpenGolfCoach estimates.
