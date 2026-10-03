# Tour reference demo pack

Play → **Load Tour demo bag** adds a dedicated editable bag and two completed demo sessions,
once per database: 180 bag-mapping shots and 144 wedge-matrix shots (12 per club/cell).
Select that bag in a **demo** round to use the existing distance suggestions. Real sessions
never use demo profiles. Loading does not alter active capture, session state or equipment selection.
Sessions use ordinary recoverable deletion and cleanup. Loading again does not resurrect deleted
sessions or reset exclusions; restore the originals through Sessions if needed.

The reference is Trackman's [Tour Averages](https://www.trackman.com/blog/introducing-updated-tour-averages),
published May 2, 2024, describing the 2023 season, primarily PGA TOUR with DP World Tour data.
The linked primary chart covers Driver, 3W, 5W, generic Hybrid, 3–9 iron and PW. Values are transcribed
in `data/tour_averages.v1.json`, retaining source/season/units. This is not a 2026 dataset.

Only the published full-swing averages are sourced facts. The test harness invents variation,
offline spread and rollout. It adds illustrative GW/SW/LW anchors (125/108/92 yd), with half and
three-quarter carry factors .55/.78. These are test fixtures, **not Tour wedge benchmarks or a
general distance law**. No putter mapping is invented. The reference bag has more than 14 clubs
so every published category can be inspected; this is a reference catalog, not a tournament bag.

Each wedge intent is an independent profile. Full wedges in bag mapping and Full matrix cells
remain distinct collection groups; recommendation labels show the matrix intent. Measured
personal data should replace demo assumptions through actual collection, never by relabeling
these samples as real. Excluded/removed shots remain out of suggestions. Sparse profiles need
at least five available total readings under the existing rule.

OpenGolfCoach flight/shape predictions are computed separately from generated reference distances;
they need not agree. The source values remain synthetic, and raw receipts retain generator/source
metadata. SQLite stores both sessions, the bag catalog and an idempotency receipt atomically;
local backups include them. A failed load rolls back all pack records. No GSPro delivery occurs.
