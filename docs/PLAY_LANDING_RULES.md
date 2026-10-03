# Simple Play landing and rollout rules

New full shots use reported carry, total and signed offline to estimate the carry landing point.
First apply the existing starting-lie distance reduction and saved direction variation. Interpolate
the landing position along that adjusted start-to-total vector using `carry / total`. This estimates
carry offline; the launch monitor has not supplied a separate measured lateral landing coordinate.

| Carry landing surface | Remaining rollout |
|---|---|
| Sand | None; stop at the carry landing point |
| Rough | Retain 25% by default (75% reduction) |
| Out of bounds | None by default (100% reduction) |
| Other surfaces | Retain the original remaining rollout |

The rough and OB reductions are separate 0–100% sliders in round setup. They affect only rollout;
the existing Shot from rough/sand sliders affect the distance of a shot starting in that lie.
For example, 80 yards of carry and 20 yards of rollout becomes 85 yards on a rough landing at 75%.
With sand, it stops at 80 yards. The final stopping surface determines the next lie. A final water/OB
position adds one penalty and restores the prior position under the existing replay rule.

Only the carry landing surface is checked. Crossing a surface during later rollout does not apply
another reduction. These are simple game rules, not validated bounce/ground physics. Putting retains
the flat-green speed/Stimp endpoint calculation. Missing, negative or carry-greater-than-total values
skip the landing rule, preserve the original total endpoint and display an explanation.

Each new outcome is `endpoint-golf-v2` and saves a `landing_rollout` record: original adjusted total
endpoint, estimated landing point/surface, carry ratio, rule version, percentage and rollout before/
after adjustment. Raw monitor values remain intact. The shot log displays source carry/total/offline,
actual game travel, landing surface and remaining rollout. Animation uses the saved landing and
stopping points; a sand landing has no artificial roll phase. Misread/Mulligan restore the prior
state while retaining the original measurements and outcome. Replay/Skip do not change scoring.

Settings are frozen for new rounds. Existing active rounds without rollout settings use 75%/100%
for newly received shots and record those defaults in each new outcome. Previously recorded shots
and completed results keep their original rules; no historical rescoring or database migration.
The demo shot form accepts optional carry to exercise landing cases; blank uses 93% of total.

Course heatmaps remain historical dispersion previews, not predictions adjusted for landing terrain.
Saved course polygons determine surfaces. Artwork alignment must be checked separately; the QA
found an existing Boulder Beach hole 1 offset and recorded a backlog item for registration review.

That audit is now complete across both 18-hole courses. New rounds use reviewed v2 boundaries;
existing rounds keep their original frozen geometry. Refresh and start a new round to use the
corrections. See [finished-art review](../designs/course-registration/README.md).

Verification: 31 Python game/landing/correction/nine-hole tests and all 49 JavaScript tests passed.
An isolated service/database verified setup defaults, explicit carry, sand stopping before source
total, animation/Skip, log evidence, reload and Misread. iPad 1366×1024/1376×1032, reduced-height
1366×900, desktop 1440×900 and phone 390×844 had no horizontal page overflow; setup number fields
were 48px tall. Physical iPad Safari and live monitor geometry remain unverified.
