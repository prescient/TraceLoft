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


## D49 — Pebble Boulder round package (2026-10-03)

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
