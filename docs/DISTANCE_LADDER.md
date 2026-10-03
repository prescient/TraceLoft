# Wedge and iron distance ladder

Open **Practice → Distance ladder**. This full-swing drill is separate from Putting ladder.
It scores the selected Foresight-reported **carry** or **total** in yards; it does not calculate
flight distance from ball speed or use a putting model.

## Setup and progression

- Wedges starts at 30–100 yd in 10 yd steps; Irons starts at 90–170 yd in 10 yd steps. These are
  editable convenience presets, not recommendations based on your bag. Custom keeps your edited range.
- Choose carry/total, shortest/longest target, an evenly dividing step, shots per target, rounds,
  ascending/descending order and an inclusive ± yd distance window. Limit: 1000 scored shots.
- Choose a starting bag and club, or leave the club untagged. Setup includes an optional session label.
  Three quick bag tabs sit to the left of directly tappable club circles in setup and the active drill.
  **More bags** opens every bag; selecting a fourth bag keeps it visible in the third quick slot.
  Empty slots offer **Add bag**, opening the existing manager with the new-name field focused.
  The live **Tag upcoming shots** controls let you switch bag/club without restarting the ladder.
  Changing bags clears the club choice; choose the club from the new bag before hitting. Wait for the
  saved **Next shot** message. Each shot keeps its own tag; earlier shots are never relabeled.
  **Clear club** returns to untagged. Buttons wrap on smaller screens with at least 44 px tap targets;
  abbreviations have full-name accessible labels/tooltips and the selection footer shows the full name.
  The actual club list is editable; it is not limited to the mockup's 14 clubs.
- **Manage bags** starts with editable My bag and 15 common clubs. Create more named bags; rename bags,
  add/rename/remove clubs, then Save bag. Close/Escape discards unsaved bag edits. Catalog saves are
  immediate and separate from launching a drill; leaving setup does not undo a saved bag edit.
  Names must be distinct within each bag. Selected club removal clears upcoming-shot tagging.
  Selection is manual and does not send GSPro keys or infer a physical club from its reported code.
- Every valid distance shot advances the configured count, including misses. After shots per target
  are complete, the ladder moves to the next rung; a new round restarts its chosen order.
- Duplicate receipts and failed reads do not advance. Excluding a shot changes analysis, not its
  saved target, ladder position or captured repetition. Real misses remain available in the log.

## Capture and feedback

Healthy capture activity appears in the app header without a repeated listening bar. Stopped,
preview-only, stopping and unreadable-source warnings appear above tagging. The red **Session over**
banner stays visible after completion even if global capture is still running.

Select a calibrated Capture profile that contains the chosen distance column; the expanded VDD
profile has both. Start capture before hitting shots. The service publishes the required distance
with the active drill, and the worker waits for a confident numeric reading before consuming a new
row. Temporary distance dashes and Tesseract fallback do not establish readiness. Existing spin,
launch and row-shift checks remain active. This requirement is cleared after the drill ends.

Missing data remains unavailable, not zero, and carry never silently substitutes for total or vice
versa. A missing-distance accepted record arriving from another ingest path is saved as **Unscored**
with the target unchanged. It stays in the shot log and is excluded from the scored denominator.
Capture read failures remain available in capture diagnostics and raw storage. There is no automatic
historical late-update repair or manual distance-entry workflow in this release.

The runner shows large latest distance/error, next yardage/window, round/rung progress, reported
distance vs per-shot target and signed short/long error charts. Offline and launch data are context,
not scoring inputs; no proximity/holed outcome is inferred. Selecting a log row shows that shot's
feedback and enables exclusion. End session, Exit session and Abandon session share the established
save/confirmation flow. Reviews have explicit Practice selector and Exit review controls; completed
sessions retain the red Session over warning. Deletion remains recoverable.

## Storage and verification limits

SQLite retains original measurements and source observations. Session/attempt payloads store the
yard target, selected distance, error, metric, scoring availability, manual equipment snapshot and rung/round.
`session_attempts.csv` exports `target_distance_yd`, `distance_yd`, `distance_error_yd`,
`distance_metric`, `distance_tolerance_yd`, `scored`, `unscored_reason`, `club_label`, `bag_id`,
`bag_name`, `club_id`, `catalog_revision` and `selection_mode` alongside
the shared attempt columns. Putting feet/model columns remain separate and empty for full-swing
ladders; the schema version stays unchanged. Wide shot export still uses measured source metrics.
The versioned manual bag catalog is saved in SQLite metadata, included in snapshots. Bag/club IDs are
stable within the bag; each attempt snapshots names and catalog revision, and the worker freezes its
selection in the durable receipt at acceptance time. Queued/replayed receipts keep that selection.
Edits affect subsequent shots. Earlier sessions without equipment remain unchanged; their legacy
club/session labels are still displayed. A session label is retained as a fallback only without a bag.
Finished/review sessions have no next-shot selector. Bulk historical corrections, shared physical
clubs across bags, loft/specification revisions and bag mapping/wedge analysis remain future work.

Automated and isolated browser tests verify drill logic, saved targets and display behavior. They
do not establish live numeric full-swing OCR accuracy. Compare several actual wedge/iron carry and
total readings to the source table before relying on scored live results; see
[VDD validation](RELAY.md). Bag mapping, wedge matrices, random approaches, pressure/retry
rules and cross-session analytics remain backlog work.
