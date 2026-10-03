# Simple 2D golf game plan

Selected direction 2026-10-01. The first playable prototype was implemented 2026-10-02;
see [current behavior and limits](2D_GAME.md). The original planning notes below retain the
physical-validation goals. Live geometry remains unverified; demo is the default and experimental
live mode explicitly acknowledges that limitation.

Use Foresight's reported carry, total distance and signed offline as the full-shot baseline.
GolfData applies simple gameplay rules and maps the adjusted endpoint onto a top-down course.
Open Golf Sim/FUSE is ruled out; an external physics engine or sampled interpolation is not required.
The goal is fun, understandable variation, not an accurate golf simulation.

## Shot flow

1. Touch the course to select an aim point. Show the current lie, remaining distance and active penalty.
2. Freeze aim, starting position and settings for the next accepted shot.
3. Read Foresight's reported result. Apply the starting-lie distance penalty and optional direction variation.
4. Rotate the adjusted result into course coordinates relative to the selected aim; classify the final lie.
5. Apply explicit water/OB recovery and scoring rules, save the outcome and advance once.

Carry locates the landing area where its lateral position is available or explicitly approximated;
total and offline locate the stopping endpoint. Verify Foresight's total/offline geometry and sign
conventions with full-swing evidence before defining the coordinate calculation. Do not substitute
HLA for final offline or count Foresight's modeled spin effects twice. Initially, classify the final
endpoint and avoid claiming accurate obstacle collisions or landing-dependent rollout.
If a required result is missing, leave the ball in place and explain what is unavailable.

## Proposed setup sliders

| Setting | Meaning | Initial proposal |
| --- | --- | --- |
| Rough distance penalty | Reduce reported travel from a rough starting lie | 7%, user-proposed starting point |
| Sand distance penalty | Reduce reported travel from a bunker starting lie | Tunable; default to be chosen |
| Extra direction variation | Optional random angular offset, in degrees | 0 degrees by default; adjustable by lie |
| Green speed (Stimp) | Existing flat-green putting estimate | Player-selected |
| Gimme radius | Finish a hole inside a configured distance, with explicit stroke rule | Default/rule to be chosen |

Use degrees for direction variation so the golfer can understand the spread. Show a numeric value
beside each slider and offer reset. Keep these controls in setup; if later editable during a round,
apply changes only to future shots and record the settings per shot. Proposed defaults are gameplay
choices, not researched surface coefficients. OB is a scoring/recovery rule, not a distance slider.

## Putting and shared state

Start with flat greens and the existing speed/Stimp putting estimate, plus an explicit cup/gimme rule.
Keep the Python service authoritative for rounds, settings, shot acceptance and penalties. Save raw
Foresight values separately from adjusted endpoints, aim, starting/final lie, settings and any random
draw so review reproduces the played shot. Label Foresight distances as reported modeled outcomes
and GolfData adjustments as gameplay estimates; preserve measured launch inputs.

## First implementation milestone

Verify reported full-swing total/offline semantics and capture readiness, then build one original
hole with touch aiming, rough/sand controls, endpoint placement, scoring and flat-green putting.
Check missing-result handling and one advancement per accepted shot using isolated data. Course
assets need established reuse permission. Play now contains this single-hole prototype; validation and multiple holes remain follow-ups.
