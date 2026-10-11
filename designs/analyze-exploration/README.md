# Analyze exploration concepts

Proposed and approved 2026-10-10; core Trends / Explore / Compare and the collapsible selections
drawer are now implemented. The original conversation preview uses deterministic synthetic data.
The [Analyze guide](../../docs/ANALYZE.md) distinguishes shipped behavior from remaining concepts.

## Recommended composition

One Analyze workspace with shared scope and three complementary views: Trends, Explore and Compare.
Retain the Vector language, global navigation, compact golfer identity and explicit review paths.
Put the charts first; keep detailed shot rows and calculation management secondary. Primary target
is iPad Pro landscape, with stacked phone charts and internally scrolling wide tables.

User refinement: put selection/filter controls in an expandable **Selections & filters** drawer,
collapsed by default. Keep a compact active-scope summary visible: bag/clubs, dates, chosen metrics
or chart axes and any numeric constraints. Keep real/demo and source/estimate identity visible too.
Collapsing never clears or reapplies filters. Preserve choices and expanded state when switching
views/returning; charts, legends, coverage and Clear selection stay usable while the drawer is closed.

### Trends

- Select multiple metrics; initially Carry, Absolute offline and Launch angle. Add Total, Spin,
  Descent, Apex, club delivery and putting metrics from grouped metric choices.
- Use vertically aligned time charts with independent units, shared dates and a shared inspection
  cursor. Offer a grid layout when several charts need equal prominence. Avoid a collection of
  unrelated units on multiple overlaid axes. A later standardized-change view can be optional and
  must label its baseline and transformation.
- Compare several bag/club/configuration/swing cohorts using stable bag/club colors and additional
  line styles for configurations. Separate cohorts rather than pooling unlike clubs into a trend.
- Choose shot, session, week or month resolution. Session points use the recorded session date;
  shot views use capture time. Calendar buckets aggregate underlying readings, not averages of
  session medians. Show median, type-7 IQR and metric-specific available n; gaps remain missing.
- Select a time interval to inspect the same interval across every panel and the detail table.
  Configuration and calculation-version changes should be visible when they affect interpretation.

### Explore

- Choose any compatible horizontal/vertical metric pair, with units. Put a distribution or second
  relationship alongside it. Examples: Launch × Carry, Spin × Descent, Carry × Signed offline.
- Select histogram bins or numeric ranges to narrow all linked charts and the shot table. Retain
  faint background points as optional context, with an explicit selected/eligible count and removable
  filter chips. Provide touch/keyboard range controls alongside any drag brushing.
- Combine different dimensions with AND; multi-selected values within a dimension use OR. Explain
  histogram denominators when that dimension omits its own filter to display alternatives.
- Distinguish highlighting one shot from filtering a cohort. A selection is a temporary analytical
  predicate, never an exclusion, deletion, club correction or model publication.
- Missing chart pairs are omitted only from that pair; show pair coverage and per-metric n rather
  than silently dropping the entire shot from every view.

### Compare

- Create named cohorts from periods, sessions, bag/club/configurations, swing intent or tags.
  Compare baseline/recent practice or old/new equipment configurations using the same metric list.
- Show each metric's median, IQR, available n and difference in its native unit. Include matched
  distribution plots where they clarify a difference. Do not imply a positive delta is improvement
  for every metric, or that an observational comparison establishes causation/significance.
- Keep original labels/configurations and selected analytical versions visible. Multi-club comparison
  uses separate rows/series and does not average incompatible equipment into one performance score.

## Shared safeguards and implementation order

1. Start with metric multi-select, club multi-select and aligned Trends, retaining SQL authoritative
   filtering and the existing source-versus-selected-calculation distinction.
2. Add numerical predicates and linked Explore, with one shared query/filter model for charts,
   summaries, detail rows and CSV. Make current selection, coverage and Clear selection obvious.
3. Add named Compare cohorts and saved views. A saved view saves query/layout intent; a published
   collection or frozen comparison additionally saves exact membership/version lineage. Reopening
   a dynamic view may reflect new shots and must not masquerade as a frozen historical result.

Real/demo data remain separate; local golfer ownership applies everywhere. Inclusion policy and
excluded/removed counts remain visible. Manual exclusion rates are not automatic outlier rates.
Source-reported total remains a core metric. Estimates are explicitly labeled, missing values stay
unavailable, historical scores keep their original pins and filters never rewrite source data.
Implemented decisions: session-start date buckets, UTC shot timestamps, exact configuration/intent/
selected-version cohort pairing, independent native units and browser-local dynamic saved queries.
No new top-level route. Baseline normalization, drag brushing, distribution overlays, independent
equipment/intent choices per comparison cohort, shared saved views and frozen comparisons remain
future work. Published bag/wedge cohorts and calculation management retain their existing authority.

## Concept verification

Interactive preview checked multiple selected trend metrics, shared session inspection, club toggles,
axis changes, cross-filtered shot rows and period boundaries. Selecting the 10–15 yd offline bin
selected 26 of 216 synthetic shots. Browser review at 1366×1024 and 390×844 showed no outer horizontal
overflow or console warnings/errors. The preview iframe's inner widths were 1319/343 px. Physical
iPad Safari and production query performance were not verified. Live app and database are unchanged.

## Implementation verification

The implemented app was reviewed against this concept in an isolated service: five metric panels,
two colored clubs, week/month/shot/session resolution, linked range/bin filters, detail inspection,
named comparisons/error recovery, matching exports, saved-query restore and review return. Checked
expanded/collapsed controls at 1366×1024, 1376×1032, 1366×900 and 390×844 without outer horizontal
overflow; wide tables scroll internally. Physical iPad Safari remains unverified. See WORK_LOG for
live cutover evidence; the concept-only verification above describes the earlier preview.
