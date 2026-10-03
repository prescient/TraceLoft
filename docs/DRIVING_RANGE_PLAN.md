# Driving range research and feature plan

Reviewed 2026-10-01. User confirmed GSPro was intended by “GoPro.” The first range is now
implemented, including the subsequently requested OpenGolfCoach model and demo harness.
See [operation](DRIVING_RANGE.md) and the [execution checklist](RANGE_IMPLEMENTATION.md).
The feature research below remains a broader roadmap; selectable tiles, touch-to-aim targets,
validated Foresight endpoints, advanced dispersion and challenges remain future work.

## Product references

| Product | Documented capabilities relevant to GolfData |
| --- | --- |
| Trackman TPS | Configurable data tiles, top-view trajectories/dispersion, shot analysis, bag distance/dispersion profiles, target/on-course practice, custom tests and standardized Combine. |
| Foresight app | Range/table/tiles views, MyBag, dispersion, tags/zones, comparisons, ladder/target drills, normalization and course dispersion overlays. Availability varies by plan. |
| Foresight FSX 2020 | Change target distance and club, top/side flight views, per-club averages, shot tables, disable outliers, club comparisons, gapping tests, CSV/PDF exports and swing video. |
| GSPro Practice Range | Adjustable range/green width and target distance, randomized distances with shots-per-target, carry/total ladder scoring, dynamic holes, ball placement, wind controls, CTP, local multiplayer and CSV export. |

Sources: [Trackman TPS guide](https://www.trackman.com/blog/your-guide-to-trackman-performance-studio),
[Foresight app](https://mobile.foresightsports.com/),
[FSX 2020 manual](https://support.foresightsports.com/fsx-2020-user-manual),
[GSPro range manual](https://gspro.gitbook.io/gspro-knowledge-base/practice-main-menu/practice-range).
Trackman TPS is the indoor simulator reference; outdoor Trackman Range is a separate product.
These are feature references, not evidence that their proprietary data or graphics can be imported.

## Proposed first release

- Open-ended range session under Practice, with optional target and explicit End/Abandon/Exit controls.
- Reuse the compact three-bag column and directly tappable club circles from the distance ladder.
  Retain More bags, Manage bags, Clear club, visible next-shot selection, full-name accessibility and
  44 px minimum touch targets. Python saves selection before the next shot; each accepted shot keeps
  its original bag/club identity. Catalog edits never change historical tags.
- Show large latest-shot carry, total and offline; selectable secondary tiles for ball speed, HLA,
  VLA, spin, apex, descent and hang time where captured. Missing metrics stay unavailable.
- Top-down range with yardage markers, touch target selection, a configurable target distance and
  fairway/target widths. Each shot retains its target; scoring must say whether it uses carry or total.
- Show Foresight stopping endpoints, highlight the latest shot and allow current-club/all-club filters.
  Verify total/offline coordinate semantics before plotting. Landing markers need a known or clearly
  estimated lateral carry position; total offline must not silently become carry offline.
- Per-club counts, average/typical carry, distance spread, lateral bias, dispersion and target hit rate.
  Show raw points before adding statistical ellipses; indicate small sample sizes.
- Shot log with inspection, recoverable inclusion/exclusion, saved session review and CSV export.
  Exclusions affect summaries, preserve the captured shot and remain visible.
- Clear capture health and save failures; accepting a shot advances range state once. Use the shared
  Python-owned capture/session infrastructure and isolated data for state-changing verification.
- Practice defaults to unchanged Foresight results with no added random dispersion or lie penalties.
  Game sliders belong to Play or an explicitly selected range scenario with separately labeled results.

## Follow-on features

| Feature | Proposed behavior |
| --- | --- |
| Flight visualization | Optional top/side tracers, replay, latest/all shots; label inferred trajectories. |
| Random targets | Minimum/maximum distance and shots per target; retain frozen target per shot. |
| Target challenges | Bullseye zones, fairway challenge, CTP and carry/total scoring; define scoring geometry. |
| Club gapping | Guided shots per club, compare distances/dispersion and identify gaps with sample counts. |
| Session comparison | Compare the same club across sessions or equipment choices without relabeling history. |
| Course practice | Repeat shots from chosen locations on our permitted 2D courses. |
| Environment scenarios | Wind/elevation/lie experiments only with explicit modeled effects and source conditions. |
| Multiplayer/video | Later local challenges or swing-video pairing; separate prerequisites and scope. |

Reuse existing distance-ladder mechanics for structured targets. Keep free practice available without
mandatory scoring. Advanced club-delivery tiles require a real captured source; do not infer measured
club path, face angle or smash factor from a flight library.

## Ball-flight candidates and Foresight comparison

Our existing integrations are flat-green putting estimates, including independent calculations based
on Penner and Fuse braking. They do not generate full-shot flight. Open Golf Sim/FUSE remains ruled
out as the game engine. A small standalone flight library can be evaluated without reviving that choice.

First candidate: [OpenGolfCoach](https://github.com/OpenLaunchLabs/open-golf-coach), an Apache-2.0
Rust library with Python and WebAssembly bindings. It accepts ball speed, launch angles and spin;
documents carry/total/offline estimates and optional time-stamped trajectory points through landing.
Ground rollout is an estimate for typical fairways, not a verified match to Foresight.
Alternative: [Simple Golf Simulator](https://github.com/markccchiang/Simple-Golf-Simulator),
an ISC-licensed Python project with flight, spin, drag/lift and wind calculations; extracting its
trajectory calculation from the GUI would need evaluation. OpenGolfCoach 0.3.0 is now installed and adapter-tested; the alternative remains unevaluated.
Retain applicable license/notice files if code is reused and pin the evaluated revision.

Treat Foresight as the product's reference (“truth” for comparison), while labeling its flight
outputs as reported modeled results. Agreement demonstrates compatibility, not real-world accuracy.

1. Collect paired full-swing launch inputs and Foresight results across clubs, speeds, launch angles,
   spin and left/right curvature. Preserve mishits; flag invalid OCR separately.
2. Record source/software version, units, spin/axis signs, normalization and environmental settings
   where available. Verify settled full-shot capture and carry/total/offline meanings first.
3. Run the model on launch inputs only; do not give it Foresight carry/total during a genuine comparison.
4. Compare carry, total, signed offline, apex, descent and hang time where both supply matching definitions.
   Separate aerial carry error from rollout/total error; report bias, absolute error and a high percentile
   by club and shot family, not just one aggregate score.
5. Tune only on a development set and check later untouched sessions. Store model version/settings,
   predictions and residuals separately; model failure must not interrupt shot capture or range use.
6. Keep Foresight authoritative for distances and scoring. A predicted tracer can add visual feedback,
   but cannot be labeled an observed flight path. If later anchored to Foresight endpoints, call it a
   reconstructed display and keep the original unanchored prediction for error analysis.

Readiness milestone: source-semantics/full-swing capture checks, then one simple range using endpoints
and our current selector. The user subsequently requested model integration in the first range. The model is implemented,
while physical source validation and paired Foresight accuracy comparison remain pending.
