# TraceLoft architecture decisions

## D61 — Simulator delivery by the shot source; modeled distances for memory capture (2026-10-11)

The user moved live simulator delivery into TraceCapture (its D53): TraceCapture sends each shot to
GSPro or Infinite Tees the moment ball and spin are known, without waiting for TraceLoft's database.
TraceLoft keeps the destination choice: Relay's setting is published as `Context.simulator`, and
'Off' means nothing is sent. A sender declaring `TraceLoft.SimulatorDelivery: 'source'` makes the
relay release the simulator connection and forward nothing while that sender is connected, so no shot
reaches a simulator twice; other Open Connect senders still use the relay. Putts measured without
spin (`SpinUnavailable`) are stored with null spin and play as zero spin. Foresight Premier's main
menu reports no distances, so TraceLoft models carry, total and offline with OpenGolfCoach (the
pinned `flight_model`). They are labeled estimates in the live view and never fill reported columns.
Whether drills may score on them is a separate, pending decision.

## D60 — Relational domain state and compatible DTOs (2026-10-10)

Schema 3 makes golfers, equipment/configuration/membership, contexts/tags/plans relational. Typed
path/value rows retain drill-specific settings and ordered state/corrections without editable JSON;
explicit views expose common join/filter fields. Frozen geometry/model artifacts and raw evidence
retain JSON. Reconcile every session DTO during migration. Cosmetic rename, configuration change
and physical replacement are distinct. Freeze session ownership; retain unknown inbound attribution.

## D59 — Readable source metrics and recalculable derived results (2026-10-10, stage 1 implemented)

Prefer explicit core columns for common source-reported shot metrics and a separate wide,
versioned table for TraceLoft calculations. Both reference the existing physical shot ID. Keep
multiple source reports/normalization revisions, explicit primary-source selection, immutable raw
evidence and original missingness. Provider flight calculations are source-reported, not automatically
sensor measurements. Calculations pin exact inputs, code/model/settings and relevant context;
recalculation appends a version and explicit publication selects it for analysis. Played outcomes
and scores never change through analytical recomputation. Everyday views expose units, club/bag
labels and selected methodology without long-form pivots. The user's confirmed list has 17 fields;
retain all 17 plus core reported total distance. Missing/invalid source values remain nullable;
the core total column is never filled from a model. Preserve source Smash Factor separately from
a versioned ball-speed/club-speed calculation. Supported columns do not imply available input values.
Equipment, tags and original/corrected shot intent use separate relational context/history tables.
Bag mapping and wedge matrix results are versioned multi-shot analyses with frozen member/input
revisions, not rows of per-shot derived metrics. Existing per-bag club IDs are not automatically
merged into a shared physical club; migration retains the original catalog and shot-time labels.
Add local golfer profiles and explicit ownership for equipment, shots, sessions and analysis.
Profiles do not imply authentication. Core editable/queryable data is relational; JSON remains for
original packets, model-specific snapshots and versioned artifacts. Avoid two editable authorities.
Schema 2 implements wide source/derived storage, quality/source selection, attempt pins and compatible
readers/writers/exports with verified backup and transactional backfill. Users, relational equipment/
context/plans, group analyses and full recalculation UI remain pending. See
[implemented scope](docs/SHOT_DATABASE.md) and [design/migration plan](docs/DATABASE_REDESIGN.md).

## D50 — Audited game corrections (2026-10-03)

Mulligan and Misread rewind the latest effective scored attempt, restoring its frozen pre-shot
position, aim, lie and score (including associated penalty/gimme strokes). They are separate
from analysis inclusion: a mulligan preserves the current analysis flag; a misread excludes the
reading. Original measurements and game outcomes remain immutable, with a correction overlay and
an append-only audit containing time, reason, target, previous state and restored state.

Completion is reversible: reopen the current hole, the previous hole from an untouched next tee,
or hole 18 from saved review. Corrections work newest-first; undo later shots before an earlier
shot. Remove affected completion snapshots, never earlier results, and increment the current turn
rather than reusing the historical turn. Reject stale key/turn, pending saves, abandoned/deleted
rounds and competing active session ownership. Save score, exclusion and audit atomically in
SQLite before publishing the resumed context. No schema migration or raw-shot deletion.


## D49 — Boulder Beach round package (2026-10-03)

Use the official January 2026 Blue scorecard (6,801 yards/par 72) for yardage/pars only, with
eighteen original coastal layouts and generated, registered aerials. Freeze every hole in the
SQLite session; keep per-hole result snapshots, hole-tagged attempts and a monotonic turn across
the round. Require an explicit next-tee action after intermediate completion. Paused or stale
inputs remain unscored evidence and cannot move a later hole. Preserve the existing endpoint rules,
legacy one-hole sessions and separate raw measurements from simulated outcomes.

The course is available through the existing Play/setup/session routes. Other tee sets, real-course
multi-hole imports, animated trajectories and more realistic physics remain separate backlog work.
See [delivery and operating guide](docs/PEBBLE_BOULDER.md).

## D48 — Independent application and direct Relay (2026-10-03)

TraceLoft and TraceCapture are sibling repositories with clean independent history. The combined
GolfData repository remains a private archive. TraceLoft contains no acquisition implementation.
Use GSPro Open Connect v1 on localhost:900 for input and optional direct localhost:921/999 output.
Do not require rēlā. Local persistence precedes acknowledgement, and forwarding cannot block storage
for more than its bounded write timeout. Preserve raw extensions and freeze shot-time context.

Use one auto-saving destination selector and remembered settings. No separate listening start/stop
step. Normal shutdown preserves the unfinished session and next launch restores it. Explicit session
end/abandon remains the user's action. Keep the existing SQLite path and immutable historical metrics.

## Carried-forward product decisions

- Python owns shared practice and SQLite; browser clients present/control it.
- Localhost needs no pairing. LAN mode is opt-in for trusted networks.
- White Vector surfaces, square controls, cobalt selection; circular club buttons remain.
- Robust club summaries use median/IQR, with sample counts and missing data distinct from zero.
- Original shots, source evidence and exclusions remain traceable; session deletion is recoverable.
- Models, demo shots and course artwork are explicitly distinguishable from measured outcomes.
- Full research and historical decisions remain in the private combined archive; current operation
  follows README, docs/RELAY.md and DESIGN_PRINCIPLES.md.

## D51 — Sheboygan Straits and artwork registration (2026-10-03)

Use the official Straits Blue pars/yardages (7,142 yards/par 72) with original lakeside layouts.
Generate from original geometry guides, then trace the finished art and visually review scoring
edges before shipping. Hash each asset with its registered geometry. Keep all design-only image
analysis dependencies outside the application environment. Existing endpoint lie rules, round
snapshots and corrections apply; dense sand does not imply simulated bunker depth or terrain.
See [course guide](docs/SHEBOYGAN_STRAITS.md).

## D52 — Map-first Play layout (2026-10-03)

Implement approved Option 1: consolidate hole scoring into the round scorecard strip, place the
compact club row above a full-width map, and replace the position sidebar with map readouts.
Put planning settings and secondary tools in disclosures below the map. Closing planning controls
does not change heatmap visibility. Preserve explicit exits, recording/completion warnings, frozen
review and the authoritative scoring model. Course scaling preserves aspect ratio and registration.
See [approved concept and implemented review](designs/play-map-first/README.md).

## D53 — Selected-nine rounds (2026-10-03)

Offer Full 18, Front 9 and Back 9 for the two full courses. Freeze only the selected hole packages
and their original numbers in the round, with selected totals and a `selection` key. Default to
Full 18 for new and legacy full-course sessions. Completion/review/corrections follow that saved
sequence; corrections remove result snapshots by hole ID, never by assuming index equals number.
Imported individual holes retain their existing flow. No database migration or old-session rewrite.
Retire the four starter holes from the catalog while retaining their assets/load compatibility.

## D54 — Source-anchored illustrative ball replay (2026-10-03)

Use reported carry/total when valid; otherwise retain reported total with a modeled carry ratio,
or use available modeled endpoints on Range. Preserve missing source measurements. Fit the saved
OpenGolfCoach trajectory to the chosen distance anchors and use its estimated hang time in seconds
without compressing the flight clock. Landing lateral position and roll timing remain illustrative;
missing model inputs produce an explicitly labeled endpoint-only replay. Play additionally fits
the presentation to the frozen scored endpoint and lie adjustment, never rescoring it. Putting
replays the existing estimated roll endpoint, without invented flight or gimme movement.

Save independent flight predictions on new applied full shots in Play, using the existing versioned
flight payload; do not backfill old rounds. Use presentation-only clocks, no replay writes, latest
arrival only for batches, no automatic history replay, Replay/Skip and reduced-motion support.
This is a limited presentation step; validated bounce/roll, obstacles, terrain and realistic physics
remain separate backlog work. See [verification](designs/shot-motion/README.md).

## D55 — Simple carry-landing rollout rules (2026-10-03)

At reported carry, stop immediately in sand; remove 75% of remaining rollout in rough and 100%
in OB by default, with separate setup percentages. Calculate the landing point by carry/total
interpolation along the original adjusted shot vector; lateral landing remains an estimate. Apply
the existing starting-lie reduction and direction variation first. Final position determines lies
and water/OB penalties. Missing/invalid carry skips landing rules without discarding the shot.

Version new outcomes as endpoint-golf-v2 with frozen landing-rollout-v1 evidence. Preserve raw
readings and all prior outcomes; legacy active rounds use default rollout settings for new shots.
Animation consumes saved landing/final points, preserving flight landing when rollout shortens.
This does not add bounce, continuous terrain interaction, new putting physics or adjusted heatmap
predictions. See [operation and verification](docs/PLAY_LANDING_RULES.md).

## D56 — Finished-art course registration (2026-10-03)

Audit every hole against the finished raster artwork, using registered overlays and reviewed pixel
landmarks. Publish corrected Boulder Beach and Sheboygan Straits as immutable v2 packages for new
rounds. Retain original assets/v1 packages and frozen session layouts; never change the surface or
score of a previously saved shot through a catalog update. Soft vegetation and surf transitions use
simplified vector edges, and the playable image perimeter remains an explicit game OB boundary.
Keep extraction dependencies in design tooling, outside the running app. Hash artwork/geometry and
retain fixed classification probes to detect drift. See [review](designs/course-registration/README.md).

## D57 — Fairway control-point refinements (2026-10-03)

Follow user review with Boulder v3 for fairways 6, 16 and 18. Use explicit native-art control points
and smooth perimeter sampling where mowing/lighting fragmented the color masks. Keep all other
surfaces, yard registration and artwork unchanged; retain v2 and frozen rounds. Check putting-apron
continuity and independent inside/outside landmarks in addition to structural/hash validation.
See [images and reproduction](designs/boulder-fairway-refinement/README.md).

## D58 — Judges Course map/photo adaptation (2026-10-03)

Use the supplied 18 illustrated maps and exact scorecard yardages, with four photographs as
woodland/lakeside style inspiration. Generate separate overhead aerials and trace finished art.
Use provisional middle tee pads and label Provided yardages instead of inferring a tee color.
Keep uniform approximate route scale, native image proportions, grass cutouts and split fairways.
Shared review tooling supports native dimensions and first-version packages. Preserve older
courses and frozen rounds; no acquisition or database schema changes.

## D61 — SQL analyses and frozen calibration cohorts

Analyze defaults to source columns. Bag/wedge results freeze exact report/context/derived IDs, inclusion flags and distinct physical-shot membership. Explicit per-golfer/bag/kind/data-mode publication is invalidated by cohort changes; future predictions use selected versions, historical scores remain pinned.

## D62 — Reviewed calculation publication and preserved history (2026-10-10)

Freeze exact report, shot, attempt, equipment context, inclusion flags, handedness and putting settings
for each batch. Hash the adapter and installed flight implementation. Commit outputs independently so
interrupted runs can resume without duplication; changed code requires a new batch. Require complete
ready coverage, unchanged dependencies and a freshly reviewed selection token before atomic publication.
Keep source reports and historical drill/game pins immutable. Analytical publication can change future
statistics and invalidate dependent Play profiles, but never rescore old sessions. Preserve old results,
publication history and model lineage in readable views and CSV. Analyze defaults to reported metrics,
including total distance; estimates require explicit selection and labels.

## D63 — Shared Analyze query and compact exploratory views (2026-10-10)

Use one authoritative SQL-backed attempt selection for multi-club OR filters and inclusive numeric
AND predicates, charts/detail/export and recalculation inputs. Preserve pre-numeric inclusion-scoped
context separately. Displaying a missing metric does not discard the attempt; a range on it does.
Keep medians/type-7 IQR/n, independent units, configuration/intent/version cohorts and real/demo/
source/estimate identity explicit. Date buckets use recorded session starts; shot plots use UTC.

Selections & filters collapses without changing query membership. Inspecting an interval/shot only
changes highlighting/displayed detail; range filters change the query and CSV. Compare replaces
common date bounds with named cohort dates, inherits common equipment/inclusion/numeric scope and
shows overlap. Browser-local saved views store dynamic queries/layouts per golfer, never frozen
publication. Shared views, frozen comparisons and advanced brushing/normalization remain future.
See [Analyze operation](docs/ANALYZE.md).
