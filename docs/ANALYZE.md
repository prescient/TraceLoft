# Analyze workspace

Implemented 2026-10-10. Open **Analyze** in the main navigation (`#analyze`). Trends, Explore and
Compare share an applied selection. These are read-only analytical views; filters and inspection
never exclude, retag, delete or rescore a shot. Cleanup remains in the session's shot workspace.

## Selections and filters

Expand **Selections & filters** to choose real/demo data, practice type, session dates, bag, clubs,
swing intent, inclusion and metric basis. Sessions, equipment configuration and tags are secondary
controls. **Apply / refresh** applies the common form. Changing data/type resets dependent filters;
changing displayed metrics applies the current form as well. No selected clubs/sessions means all
matching clubs/sessions. Multiple clubs use OR; different dimensions and numerical ranges use AND.

The drawer starts collapsed. Its summary, data/basis identity, coverage, active numeric chips and
CSV remain visible. Collapse changes layout only. Applied choices, view and drawer state survive
navigation/reload within the browser tab, scoped to the selected local golfer.

**Source-reported metrics** is the default, including reported total distance. **Selected analytical
calculations** explicitly uses the selected estimates/derived features where applicable; launch and
club inputs remain source readings. Missing values stay unavailable. A predicate on a missing metric
rejects that attempt; displaying a different unavailable metric does not reject the whole attempt.
Included shots is the default. All non-removed shots includes manual exclusions; removed shots stay
out. Manual exclusion counts are not automatic outlier classifications.

## Trends

Select several metrics for aligned panels with independent units; **Grid layout** places panels side
by side on wide screens. Colors identify bag/club; configurations, swing intent and selected model
versions remain separate cohorts. Line styles supplement color. Charts show medians and type-7
middle-50% bands, with available n per metric. One reading has no estimated spread.

Session/week/month buckets use recorded session start dates, not shot capture dates. Weeks start
Monday; calendar buckets aggregate underlying readings rather than averaging session medians.
Shot resolution uses capture timestamps in UTC and explicitly counts missing timestamps.
**Inspect shared interval**, or a chart tap, highlights the same interval across panels and narrows
the displayed detail rows. Inspection is distinct from a numerical query filter: CSV still exports
every attempt matching the applied query.

## Explore

Expand the drawer to choose horizontal/vertical axes and a distribution metric. Tap a histogram bin
or enter inclusive minimum/maximum bounds to cross-filter every view, detail rows and CSV. Combine
ranges on several metrics; remove a chip or use **Clear chart filters** to widen the selection.
Histogram membership partitions bin edges precisely even though displayed labels are rounded.

Faint scatter points show the inclusion-scoped context before numerical filters. Pair coverage and
the drawn/available count are explicit; the scatter draws up to 1,500 context pairs. Missing x/y
readings affect this pair only. The histogram respects other ranges while omitting its own range,
so alternatives remain available. Its caption gives that denominator. Tap a selected dot to inspect
its readings and open the detail table; inspection does not change the query or inclusion.

## Compare

Expand the drawer to name baseline/comparison cohorts and set their session dates, optional session
sets, configuration or any-match tags. Defaults split matching session dates into first/second halves.
Cohort dates replace the common date range; blank dates are unrestricted. Empty session/config/tag
overrides inherit the shared scope. Common bag/club, intent, data mode, inclusion, basis and numerical
ranges apply to both. **Compare cohorts** applies these two forms.

Each row pairs the exact bag/club/configuration/intent and selected model version, showing median,
IQR, n and native-unit median difference. Changed equipment/versions use separate rows; unmatched
counterparts stay unavailable. Counts and overlapping attempts are explicit. Differences describe
the selected observations, not significance, causation or guaranteed improvement. Export each cohort
with its own CSV link; the common CSV retains the common query.

## Detail, saved views and versions

Expand **Shot workspace** for up to 100 displayed attempts, readings, source/calculation lineage and
**Review session** links. Session review/coverage, counting methods and calculation management are
secondary disclosures. Returning through global Analyze retains applied choices. Practice and all
global exits remain available; navigating never ends an active practice session.

**Saved views** stores up to 12 named applied query/layout definitions per golfer in this browser.
Load includes current matching data; this is not frozen cohort publication. It is not stored/shared
in SQLite or synchronized across devices. Frozen bag/wedge collections and reviewed calculation
publication remain separate workflows. Browser storage failure reports an actionable message.

Future work: drag brushing, matched distribution overlays, baseline normalization, independently
selected bag/club/intent per comparison cohort, server-shared saved views and frozen comparison
publication. See [design concepts](../designs/analyze-exploration/README.md) and [backlog](../BACKLOG.md).

Verified in an isolated synthetic-data service at 1366×1024, 1376×1032, 1366×900 and 390×844.
Physical iPad Safari/touch and LAN acceptance remain unverified.
