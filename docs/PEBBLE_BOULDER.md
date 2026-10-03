# Boulder Beach

Renamed from Pebble Boulder on 2026-10-03. New rounds use `pebble-boulder-blue-v2` with terrain
traced from the finished artwork. The older v1 package and original artwork paths remain intact.
Existing round snapshots retain their original data; the interface shows the current name.
All 18 holes' greens, tees, sand, water and grass regions were reviewed and registered again;
see the [complete course audit](../designs/course-registration/README.md). Start a new round to
use the corrections; refreshing an earlier round preserves its geometry and outcomes.

Requested 2026-10-03: an original eighteen-hole coastal course inspired by Pebble Beach, with the
same Blue tee yardages and pars but distinct layouts, hazards and lies. The Sim companion feature
remains deferred; this work extends the existing Play game.

## Delivery checklist

- [x] Verify Blue scorecard: official January 2026 PDF, par 72, 6,801 yards (hole 15 is 392 yards).
- [x] Build eighteen original, versioned holes with uniform artwork registration and playable surfaces.
- [x] Generate and review continuous coastal aerial artwork for every hole.
- [x] Implement durable multi-hole progression, per-hole and round scoring, completion and review.
- [x] Integrate course selection, scorecard, next-hole controls and historical hole inspection.
- [x] Test all eighteen holes, hazards, putting, stale inputs, resume and legacy one-hole compatibility.
- [x] Review Play journeys at iPad Pro landscape, desktop and phone sizes.
- [x] Update operation/navigation/backlog and make the completed course available in Play.

## Yardage source

[Pebble Beach official scorecard](https://www.pebblebeach.com/content/uploads/PebbleBeach-Scorecard.pdf),
January 2026 edition, reviewed 2026-10-03. Blue distances by hole:
378, 509, 397, 333, 189, 498, 107, 416, 483, 444, 370, 202, 401, 559, 392, 400, 182, 541 yards.
Front nine 3,310; back nine 3,491. These are playing-route distances; direct ball-to-pin distances
may be shorter on doglegs. Earlier scorecards and marketing totals differ; retain this edition.
Use only factual yardages/pars as inspiration, with original geometry and generated art. No official
course rating/slope, geographic reconstruction or Pebble Beach artwork is implied.

## Round contract

Each round freezes the eighteen hole packages. Each shot retains its hole identity, source readings,
starting/ending state, penalties and conceded putts. Completing an intermediate hole pauses scoring
until Next hole; it does not end the round. The eighteenth completes the round. Inputs during that
pause remain evidence but cannot advance a hole or be replayed into the next one. A monotonically
increasing turn plus hole context rejects late shots from prior holes. The scorecard includes partial
scores honestly and analysis exclusions never remove strokes. Existing one-hole sessions stay intact.

Use the current endpoint game: flat greens, configurable rough/sand reductions, no tree collisions
or elevation, water/OB replay with one penalty. Coastal art does not add undisclosed physics.
New full shots also use [carry landing rules](PLAY_LANDING_RULES.md): sand stops immediately,
rough rollout is reduced 75% and OB rollout 100% by default. Setup can change rough/OB percentages.

## Playing and reviewing

1. Open Play and choose **Boulder Beach → Set up round**. Choose demo or acknowledged live input,
   Full 18 / Front 9 / Back 9, lie effects, Stimp, gimme radius and equipment. Full/Front starts
   hole 1; Back starts hole 10. Blue totals: Full 6,801/par 72; Front 3,310/par 36; Back 3,491/par 36.
2. Select a club, tap the map to aim or choose Aim at pin. The existing bag mapping/wedge profiles
   supply the optional historical dispersion overlay. Distance follows the current aim; it is not
   a terrain-aware club recommendation.
3. Play to the green, then putt using the displayed estimated pace. Completing an intermediate hole
   pauses scoring until **Next hole**. The hole score explains played shots, penalties and gimmes.
4. Tap the compact **scorecard** to see front/back scores. End round saves a partial round; Exit
   round confirms ending and returns to Play. Merely visiting Play/Practice leaves it active.
5. Hole 9 ends Front 9; hole 18 ends Back 9 or Full 18. Sessions → Review → **Review a hole**
   inspects its map, shot log and score. Only selected holes appear; back-nine numbering remains
   10–18. Excluding shots affects analytics only. Delete remains recoverable through Sessions.
   Misread/Mulligan can reopen the final selected hole while preserving earlier scores.

The map spans the full content width. The scorecard strip above it shows the current hole's played
shots + penalties + gimmes = total, separately from the round total and correction counts. Distance,
lie and next stroke appear on the map; on the green this includes estimated pace and Stimp.
Expand **Club dispersion** below the map to change source, Carry/Total, swing profile or visibility.
The heatmap continues to display while these controls are collapsed. **Map options & hole guide**
contains coordinate aiming, terrain/boundary switches and hole strategy. The shot log is collapsed
during play and opens in saved review. Demo rounds have a separate **Simulate a shot/putt** disclosure.

The full course package is `courses/pebble-boulder-blue-v1.json`. A normal service restart restores
an unfinished round or its between-hole pause. No database migration or reset is required.
Artwork provenance and editable geometry references are in [design notes](../designs/pebble-boulder/README.md).

## Correcting a shot

Use **Mulligan** or **Misread** in the header before End round. Both remove the latest
scored attempt from gameplay and restore its previous position, aim, lie and score. Any penalty or
gimme added by that attempt is removed too. Mulligan keeps its current analysis inclusion; Misread
excludes it from analysis. The original reading and original result remain in the shot log with
an explicit correction label. Counts appear in the scorecard summary; expand the scorecard and
**Shot correction history** to see correction types, holes and timestamps.

Choose your bag in course setup. The active round has a compact **Club for next shot** row with
that bag's name. Changing or clearing the club keeps the same bag and preserves earlier shot tags.

These buttons remain available after a hole finishes, after advancing to the next tee, and after
hole 18. In Sessions review, correcting explicitly reopens the round and returns to its active
screen; you cannot displace another active session. Button help identifies the latest
scored attempt in the entire round, regardless of which hole is being reviewed. Repeat to go back
newest-first. Unscored and already corrected attempts are skipped. Abandoned rounds cannot reopen;
deleted rounds must first be restored. Analysis Include/Exclude alone never changes the score.

## Verification

The isolated API test plays all eighteen holes along their routes, approaches each green, putts out,
checks cumulative/per-hole totals, reloads SQLite and exercises exclusion/deletion/restore. Additional
checks cover pause evidence, stale prior-hole context, duplicate next actions, save-failure rollback
and resuming a paused round. Geometry checks cover all routes, tee/pin lies, water/sand centers,
official yardages and every PNG's registration aspect ratio. Existing one-hole tests remain passing.

Fresh browser checks use an isolated HTTP/input/database service: setup, launch, club selection,
completion → Next hole, partial ending, full-round saved review, selecting earlier holes and exits.
Reviewed 1366×1024 and 1376×1032 iPad landscape, 1440×900 desktop and 390×844 phone viewports.
The scorecard and shot log scroll within their containers on narrow screens; the page does not
overflow horizontally. This is browser viewport verification, not a physical iPad/Safari test.
