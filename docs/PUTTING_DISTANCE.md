# Putting distance estimates and ladder

Implemented 2026-10-01. These are provisional flat-green estimates, not observed travel, hole
proximity, holed-putt outcomes or a verified GSPro equation. Python owns estimates, targets and scoring.

## Model choice

**Stimp constant braking v1** is the default baseline. Constant rolling deceleration is the simplifying
assumption used in [Penner (2002), The physics of putting](https://www.raypenner.com/golf-putting.pdf).
Using a nominal release speed of 1.83 m/s and entered Stimp S in feet:

```
a0 = 1.83² / (2 × 0.3048 × S)  [m/s²]
D = S × (v / 1.83)²           [feet; v in m/s]
v_required = 1.83 × sqrt(D / S)
```

This baseline rolls to zero speed and matches the nominal Stimp distance at the reference release
speed. Penner assumes immediate pure rolling; that does not resolve launch/skid in our captured data.
It is a transparent starting point, not evidence of greater predictive accuracy on this mat or GSPro.

**Fuse speed-dependent braking v1** is an optional simulation comparison. Source inspected at
[Fuse commit bd9e622](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/physics/ballPhysics.ts),
with the green's 0.18 m/s stopping threshold from
[surface definitions](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/courses/surfaces.ts).
GolfData independently integrates the documented braking law analytically:

```
a(v) = a0 × [1 + 0.3 × (v - 1.83)]
D = integral(v / a(v), v = 0.18 .. initial speed)
```

Travel is zero when initial speed is at/below the threshold. Distance targets invert the same function
numerically. This is a continuous flat-green approximation, not a port of the full Fuse engine:
terrain, time-step effects, bouncing, spin friction, cups and slopes are omitted. No Fuse source code,
course assets or dependency is bundled. See [the Fuse evaluation](FUSE_EVALUATION.md) for reuse scope.

Matching the *instantaneous* braking rate at 1.83 m/s does not make the integrated Fuse travel equal to
Stimp. At Stimp 10, illustrative computed estimates are:

| Launch speed | Constant braking | Fuse braking approximation |
| --- | --- | --- |
| 2 mph | 2.4 ft | 3.6 ft |
| 4 mph | 9.6 ft | 12.0 ft |
| 6 mph | 21.5 ft | 22.6 ft |

Both models treat measured launch speed as initial rolling speed, assume a flat uniform green, and
omit skid/cup effects. [Pope et al. (2014)](https://shura.shu.ac.uk/8354/) measured skid and final distance
on artificial/natural surfaces; those observations motivate calibration rather than a universal
replacement equation. Physics/numerical tests validate our equations, not real stopping distance.

## Setup, feedback and scoring

- New drills expose Stimp (3–20 ft) and a model selector. Existing saved sessions keep their original
  measurements/targets; missing historical Stimp/model remains unavailable rather than backfilled.
- Fixed Pace consistency and Pace + start line offer measured speed or estimated distance targets.
  In distance mode, the service derives required pace and scores estimated travel within ± ft.
  Combined drills also score the configured angular window. Start line scores angle only.
- Random pace still varies speed. Distance estimates and each putt's derived distance target are saved
  as context; it is not a random-distance drill.
- Putting ladder sets shortest/longest distance, an evenly dividing step, ascending/descending and
  rounds. One putt per rung advances on every confirmed putt, including a miss. After the last rung
  the next round restarts; total rungs × rounds must be ≤1000. There is no pressure/retry-on-miss mode.
- Ladder scoring uses estimated distance only. Start line remains measured and explicitly unscored.
  Exclusions do not rewind rungs or remove captured repetitions. Duplicate/failed receipts do not advance.
- Latest travel and signed short/long error are large; distance-mode charts show per-putt target zones.
  Required pace and next rung/round remain visible. Capture warnings, end/abandon/review/exits are shared.
- Putting speeds are supported through 15 mph. Unreachable targets and invalid ranges/models are
  rejected before a session is saved. Estimates retain full precision; presentation rounds for readability.

## Persistence and export

Schema v1 session/attempt payloads save estimated travel/target/error in feet, selected model identity,
entered Stimp, source revision, assumptions, reference speed, braking coefficient, stop threshold and
ladder rung/round. Measured `vals` and typed launch observations remain unchanged. Historical estimates
are read from saved outcomes, never recomputed when reviewing or excluding a putt.

`session_attempts.csv` exposes distance outcomes, model/Stimp, target mode/tolerance and rung/round
columns. `putting_models.json` contains complete per-session model assumptions in the same export
snapshot. Distance estimates are not inserted as measured ball/roll-distance metric values.
Summary bias/spread uses each included putt's own distance target; excluded observations stay in the log.

## Future GSPro calibration

Requested next research: collect repeated GSPro putts across relevant launch speeds and Stimp settings,
record actual simulated stopping distances and evaluate fitted speed-to-distance curves against held-out
putts. Keep the theoretical baseline and Fuse approximation as comparison models.

Use a flat, consistent virtual green and let putts stop without entering a cup. Record GSPro version,
green/Stimp, slope, assistance/boost settings, ball/setup and available launch/spin inputs. A holed putt
does not reveal its unconstrained stopping distance; flag it as censored rather than fitting hole
distance as stopping distance. Record failed captures separately. Fit monotonic curves or a calibrated
physical model per settings/version, inspect short/long residuals across speed and compare mean absolute
and tail errors on independent validation putts. Expose sample coverage and uncertainty.

A GSPro fit models GSPro behavior; calibrating physical mat travel requires its own observed outcomes.
Save immutable calibration IDs/inputs with future estimates so new fits do not rewrite old results.
Collection/outcome entry, fitting, held-out comparison and calibrated model selection remain backlog
work; this release does not collect actual stop distances or claim calibration accuracy.
