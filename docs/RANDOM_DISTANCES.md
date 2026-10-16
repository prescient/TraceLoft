# Random distances

Practice → Full swing → Random distances (`#setup/random-distances`). TraceLoft draws a carry
target at random; the golfer chooses the club, tags it in the club picker and hits. Each scored shot
ends its target and draws the next, so a session moves between clubs the way a round does (D67).

## Setup

- **Shortest / longest target** (1–450 yd) and **round targets to** (1–50 yd): targets are the
  shortest distance plus whole steps, up to the longest. 60–180 yd every 5 yd gives 25 targets.
- **Minimum change between targets** (0–200 yd): every new target is at least this far from the
  last one; 0 still never repeats a target twice in a row. A setup where some target would have no
  valid next one is refused, and the setup line says to widen the range or lower the change.
- **Number of targets** (1–200): the session finishes itself after that many scored shots. End
  session stops earlier; Abandon keeps the shots as Abandoned.
- **Distance window** (full depth) and **target width**, as on the range: a shot is in window when
  its carry is within ±depth/2 of its target. Width only draws the target box on the dispersion chart.
- Starting bag/club and handedness. Start a live session, or a demo whose synthetic shots are aimed
  at each drawn target (with noise and an occasional mishit).

## Scoring

- Carry is the range's OpenGolfCoach estimate from launch data (D63), labeled `est.`; reported
  distances are the fallback only when the model cannot run. Measurements are never changed.
- Every shot keeps its own target (`target_distance_yd`), target number, club tag and result.
- A shot without a usable carry is saved unscored with "Carry unavailable; target unchanged" and
  does not count toward the number of targets.
- The session's own draw is the target. A shot that arrives before the source received the new
  target is still scored against the session's target.
- Exclusion, removal and retagging use the shared range cleanup. They change the score and
  statistics (in window, average absolute miss, short/long counts, included scored shots only),
  never which targets were drawn or how many are done.
- No club is suggested. Picking the club is part of the practice (the user's choice, D67).

## Screens and data

The runner is the range workspace with a next-target panel first: the next yardage, target number,
the last shot's result in words, the running score and progress. The club picker sits directly
below it. Change target is not offered; Edit setup copies the parameters to a new session.
Finished and saved sessions show the result headline instead. The Sessions list shows `N in window`.

Sessions are `driving_range` sessions with `drill: 'Random distances'` and `target_plan: 'random'`
(`random_distances.py`, restored through `drills.session_kind()`); targets are drawn one at a
time, so future targets are never stored or sent. The input context publishes the next target to
the source as `range_context`. The shots are stored like other full-swing range shots and appear in
Analyze and the database CSV export (covered by a test).
