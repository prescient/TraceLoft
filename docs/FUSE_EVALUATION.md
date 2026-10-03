# Fuse evaluation for GolfData's planned 2D simulator

Reviewed 2026-10-01. Research and recommendations only; no Fuse code, course assets or dependencies
have been added to the app. GolfData's full simulator remains unimplemented. Follow-up: an independently integrated flat-green braking comparison and a constant-Stimp baseline now support labeled putting estimates/ladder; see [model notes](PUTTING_DISTANCE.md). Calibration remains pending.
Source inspected: [OpenGolfSim/fuse](https://github.com/opengolfsim/fuse), commit
`bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42` (2026-09-26), package version 1.0.9.

## Current status — ruled out 2026-10-01

User ruled out Open Golf Sim as too immature for GolfData's purposes. This removes its desktop API
and FUSE engine from the 2D-game shortlist and supersedes the selection below. Retain this evaluation
as historical research, not an implementation plan. The current direction is simplified 2D gameplay
with tunable lie effects and Foresight reported full-shot outcomes; see [current plan](2D_GAME_PLAN.md).
The existing independent putting braking comparison is unchanged by this candidate decision.

## Earlier selected direction — superseded 2026-10-01

User selected FUSE as the initial simulator engine. This supersedes the earlier recommendation
to defer engine integration. Selection is a design decision; no engine integration or course import
has been implemented or validated.

Use FUSE flight/ground physics behind a GolfData adapter and retain its terrain/surface geometry
for collision and lie queries. Present a top-down course with touch aiming, a prominent next-shot
lie/distance card and a close-up putting view. Start with explicitly flat greens and selectable Stimp;
flattening a display map alone does not flatten the physics terrain. Preserve measured inputs and
label all simulated positions, holed outcomes and benchmark-based strokes gained as estimates.
Do not add random dispersion to measured shots by default.

The Python service retains round/scoring authority. A designated engine owner computes each
shot once; shot IDs, frozen aim/start state and idempotent result acceptance prevent duplicate
advancement across browsers. Engine disconnect/recovery must not replay a shot as a new stroke.

Prefer a compatible existing course with verified asset permission. Availability to play in
OpenGolfSim does not establish permission to copy or distribute its course assets in GolfData.
Record source, creator, permission/license, hash and attribution per asset; use an original test
hole if no reusable course is established. Public documentation confirms GLB export/testing but
does not establish blanket reuse rights for the hosted course library.

Bundle the upstream license/required notice with reused engine code and distributed browser bundles;
provide accessible third-party notices. Benchmark full shots, surface rollout and putting before
calling physics validated. Initial prototype belongs under Play; detailed performance belongs under
Analyze. Current routes remain placeholders until implementation.

## Earlier recommendation (superseded by engine selection above)

Use the course-building approach to inform a small GolfData course format: surface polygons,
tee/pin/aim positions, real scale and optional elevation. Start with an original hole and our existing
browser interface. Evaluate a permitted SVG or GLB importer later. Benchmark Fuse's putting and
flight behavior before selecting any model; importing its complete 3D engine is a separate option.

Keep the Python service authoritative for shots, round transitions and saved outcomes. A browser
must not independently advance a round each time another device receives the same shot. If a future
engine adapter computes results outside Python, define one designated engine owner, shot IDs,
idempotent result submission and authoritative service acceptance before supporting shared clients.

## Course layout: useful formats and limitations

The inspected loader reads GLB/glTF course metadata. Hole groups identify hole number and par;
waypoints identify tee, pin and other named positions using map coordinates. Mesh metadata identifies
surfaces. Its horizontal world plane is X/Z, with Y elevation; internal distance calculations use
meters. Course size and image alignment matter when converting these coordinates.
[Course loader](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/courses/loader.ts).

The course map is an embedded JPEG with ball, aim and pin overlays. The map UI supports pointing to
aim and placing the ball. This is a useful interaction reference, but a raster image alone cannot
reliably determine whether a shot finished in rough, sand or water. Gameplay needs semantic geometry
alongside the display map.
[Map implementation](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/ui/UICourseMap.ts).

OpenGolfSim's documented authoring workflow begins with SVG outlines for playing areas and combines
them with terrain through Meshery. It can optionally search OpenStreetMap for existing course shapes.
The final course export is GLB. **Inference:** a legally usable authoring SVG is likely a simpler
starting point for our polygon map than reverse-engineering a rendered map or full terrain mesh.
The SVG still needs surface labels, scale, orientation and tee/pin locations; an arbitrary illustration
is not automatically a playable course.
[SVG authoring](https://help.opengolfsim.com/course-building/course-layers/svg/),
[course export](https://help.opengolfsim.com/course-building/course-export/).

An optional GLB importer would need to apply node transforms, preserve surface metadata, project and
union relevant ground triangles, retain islands/holes and reconcile overlaps. It must extract scale,
bounds and waypoints without depending on decorative meshes. This conversion has not been tested
against a course asset. Do not assume all OpenGolfSim tool versions export the inspected format.

For an initial flat-green sim, elevation can be absent and explicitly modeled as flat. Later terrain
imports need source resolution and vertical units/datums. Course-scale terrain is not sufficient
evidence of accurate putting-green contours.
[Terrain documentation](https://help.opengolfsim.com/course-building/course-terrain/real-world/).

## Calculations worth evaluating

Fuse uses a Stimp-based braking baseline derived from a 1.83 m/s release speed, with Stimp distance
converted from feet. Its implementation adds speed-dependent braking, slopes and cup handling.
Putts enter ground motion directly rather than modeling measured launch/skid. This makes it a useful
candidate simulation model, but does not establish agreement with GSPro or our physical putting setup.
[Ball physics](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/physics/ballPhysics.ts).

For a flat constant-deceleration model, stopping distance is proportional to speed squared and Stimp
distance. Validate integrated stopping distance across speeds/settings, using held-out observations;
matching braking at one speed is insufficient. Keep measured launch speed distinct from rolling speed,
and label pace/travel estimates with model/calibration identity.

The surface definitions distinguish green, fringe, fairway, first cut, rough, sand, water and other
areas. Parameters separate impact friction/restitution from rolling resistance and spin grip.
These offer useful design references for landing and rollout. They do not establish a calibrated
launch-distance penalty for hitting out of rough or a bunker; our proposed lie adjustments need their
own explicit gameplay rules and validation.
[Surface definitions](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/courses/surfaces.ts).

Flight coefficients vary with ball speed. Shot input includes speed, vertical/horizontal launch,
total spin and spin axis; these broadly overlap our capture fields. An adapter must verify units,
target/aim conventions, spin signs, missing values and any engine input clamps. Keep the original
measurements unchanged even when a simulation transforms an input.
[Physics coefficients](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/physics/constants.ts),
[shot/event contracts](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/globals/globals.ts).

The event contract includes starting, landing and ending positions and optional trajectory samples.
That is compatible in concept with our planned miss maps, but our round writer must additionally
preserve aim, before/after lies, penalties, next playable state, course/rules/model revisions and
randomness. A result contract is not evidence that every producer populates every optional field.

## Proposed course storage contract

Extend [the database proposal](../DATABASE_PROPOSAL.md) with versioned course data:

| Entity | Proposed contents |
| --- | --- |
| `courses` | Stable ID, name, original/course-inspired identity |
| `course_revisions` | Immutable layout version, source/import profile and hash, coordinate frame, origin, meters-per-unit, orientation, bounds and elevation assumptions |
| `course_holes` / `course_waypoints` | Revision, hole number/par, named tee sets, pin options and aim points in the declared frame |
| `course_features` | Stable feature identity within a revision, surface/hazard type, polygon rings with interior holes, overlap priority and optional elevation reference |
| `course_assets` | Source URL/creator, artifact hash, license/attribution, permission evidence and import lineage for SVG/GLB/maps/terrain |

Start with validated JSON geometry in SQLite; a spatial extension is optional future work. Keep
course-relative coordinates distinct from latitude/longitude and target-relative miss coordinates.
Transform SVG pixels or geographic inputs into a documented local metric frame; do not calculate
yardages directly from pixels or longitude/latitude. Verify a known hole length and tee/pin orientation.

Pin each played round to its course revision and chosen tee/pin configuration. Editing a layout must
not relocate old shots, change historical lies or silently recompute played outcomes. Display overlays
and semantic surface tests must share one transform. Define boundary/overlap handling deterministically;
preserve which feature and rules revision determined the lie or penalty.

## Reuse and asset rights

The repository's README and license file specify **PolyForm Noncommercial 1.0.0**. It permits qualifying
personal/hobby noncommercial use and requires license/notice retention when distributing covered
software. Commercial reuse would need different permission. The inspected package metadata instead
says ISC: this conflicts with the explicit license file, so do not assume an unrestricted ISC grant.
[License](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/LICENSE.md),
[package metadata](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/package.json).

Engine rights do not automatically cover hosted courses, maps, imagery, terrain or creator content.
Verify each asset's own permission and attribution before bundling/importing it.
[OpenStreetMap inputs have separate licensing obligations](https://www.openstreetmap.org/copyright).
Start with original course geometry; no third-party course library
has been verified or downloaded for this review.

## Implementation sequence and acceptance evidence

1. Define the versioned course format; create one original flat hole with surface polygons and tee/pin.
2. Implement map aiming, yardages, deterministic lie selection and explicit scoring/recovery rules
   inside the existing modular practice flow, with exits and recording/completion states.
3. Collect putting calibration observations; compare our simple model with permitted candidate
   implementations across relevant speeds/Stimp settings before selecting a distance model.
4. Prototype one permitted SVG/GLB import in isolation; confirm transformed yardages, surface queries,
   overlapping boundaries, pin/tee placement and historical revision behavior.
5. Add measured-shot flight/bag/wedge integration and miss analysis using saved simulated outcomes.

This review inspected source and official documentation; it did not execute Fuse, import assets or
validate physics. The package test command is a placeholder, and no test/spec files were found in
the inspected tracked-file inventory. Our own isolated geometry, replay, calibration and shared-shot
acceptance checks are required before integration can be called verified.
