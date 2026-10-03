# TraceLoft architecture decisions

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
