# Fictional starter holes

2026-10-02. Original AI-generated aerial concepts for TraceLoft, created with the built-in imagegen
tool. These are original fictional holes, now bundled and playable as separate single-hole rounds.
Full prompts and
intended layout constraints are in prompts.json (historical design archive).

| Hole | Target yardage | Par | Design intent |
| --- | --- | --- | --- |
| Willow Cove (historical design archive) | 155 yd | 3 | Short iron near a pond edge, dry bailout and greenside sand |
| Pine Bend (historical design archive) | 365 yd | 4 | Dogleg, strategic fairway bunkers, woodland framing |
| Meadow Reach (historical design archive) | 525 yd | 5 | Two landing zones, safe layup, water beside the final approach |

The initial distance labels were design targets. The published packages now register the artwork
uniformly to the saved route: 155, 365 and 525 yards. Straight tee-to-pin distances are respectively
155, 352.1 and 504.8 yards. Par-four/five yardages follow the route, not a direct tee-to-pin line.

Visual review: Pine Bend's generated route bends more strongly than the brief and places its tee
upper-left rather than lower-left. Registration follows the actual artwork; prompt coordinates
are not geometry. The frozen transform preserves each image's proportions.
Meadow Reach has a continuous curving fairway and clear layup route above its irregular pond.
All three outputs are 1774 × 887 PNGs, with no UI or dispersion baked in. Their surface proportions
are illustrative and boundaries are hand-traced fictional game geometry, not surveyed surfaces.

## Implemented registration and overlays

The following workflow is complete for all three version-1 holes. Reproducible source traces and
validation are in [build_fictional.py](../../courses/build_fictional.py). Published JSON lives beside
that script; production PNGs live in `web/art`. Keep these versions fixed once played.

1. Select tee, pin and any dogleg route points in the artwork. Set a single uniform pixels-to-yards
   scale from the route length and target yardage. Record image dimensions, points and transform;
   do not stretch one axis. Check plausible green sizes and landing-zone widths after scaling.
2. Trace fairway, green, tee, sand and water polygons. Define rough/nature and an explicit artificial
   game boundary. The artwork does not establish elevation, putting slopes or official course rules.
3. Review visible edges against the polygons at full-hole and green zoom; those polygons must drive
   both scoring and simple-fill fallback. Correct the artwork or boundaries where they disagree.
4. Add existing dynamic ball/pin/aim markers, tap distances, shot endpoints and bright-blue historical
   club heatmaps as separate overlays. Do not bake UI or dispersion into the background image.
5. Validate lie classification, distances, penalties, selection/aiming, overview/green alignment and
   target-device layouts in an isolated demo. Publish immutable course versions only after review.

This artwork-first workflow applies to new fictional holes. Do not regenerate or retrace already
played versions in place. Existing Meadow One rounds and current course-import tools remain intact.

## Verification evidence

API tests complete all three routes through putting, verify penalties/replay and sand reductions,
and retain exact course/state in saved review. Browser review covers all three selections,
Willow Cove completion, Pine Bend/Meadow Reach aim and demo heatmaps, boundary/fallback views,
active-session guards and refresh. Layout checks (historical design archive) cover iPad landscape,
reduced-height desktop, tablet and phone; actual iPad Safari/touch remains unverified.

- Hole library (historical design archive) and additional holes (historical design archive)
- Phone library (historical design archive)
- Meadow Reach map and heatmap (historical design archive)

Willow Cove completion was verified through the browser's rendered state; its malformed full-page
capture was discarded. Library iPad evidence uses a stable viewport capture of production with the
preserved active-round guard, while the additional-hole and gameplay captures use isolated QA.
