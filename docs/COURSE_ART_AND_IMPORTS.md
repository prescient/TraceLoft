# Course artwork and assisted real-course imports

## Implemented: continuous aerial course, 2026-10-02

New rounds default to `meadow-one-v2`: one original AI-generated 1774×887 aerial image,
with a visibly blue, irregular pond, two bunkers and continuous grass/forest. There are no
repeating texture tiles in this version. `courses/meadow-one-v2.json` freezes hand-traced
surface polygons and the image-to-yard transform. The tee-to-pin distance is 350 yards.
Geometry is approximate fictional artwork tracing, not a surveyed real course.

Polygon surfaces support disconnected pieces and interior holes. The same saved polygons
drive Python lie classification, simple-color fallback and the optional boundary overlay.
Image failure leaves those fallback fills. The artwork is decorative; the boundary overlay
is authoritative near edges. Saved rounds retain their original geometry/art version.
Green zoom uses the same registered image, so there is no change of scale between views.

## Legacy course: tiled terrain

Meadow One retains its saved `meadow-one-v1` geometry and 350-yard par four. The browser now paints
AI-generated grass, sand, water and tree textures inside the same SVG shapes used for the schematic
map. The Python service remains authoritative for surface classification, distances and outcomes.
The art is cosmetic: it adds no trees with collision, elevation, slopes or new playable hazards.

**Map display → Show scoring boundaries** reveals the saved fairway, green/tee, bunker, water,
nature and out-of-bounds geometry. **Detailed terrain** switches between textured and simple fills.
Both work in overview, green zoom, live/demo and saved review, without changing session state.
Display choices last for the current page lifetime; refresh restores detailed terrain with boundaries
hidden. A missing texture still leaves colored fills. Tap/click to aim, use **Aim at pin**, or use
the numeric coordinates for keyboard access. Left/right step buttons were removed per user feedback.

`web/course-art.js` owns rendering only. `web/art/course-materials-v1.png` is a 1536×1024 texture
atlas with six 512-pixel squares: rough/fairway/green on the top row, sand/water/nature below.
Generated with the built-in imagegen tool on 2026-10-02; no aerial photograph or third-party course
was used. SVG patterns select each tile, preserving exact geometric edges. The generated material
repetition and original simple course shapes limit realism; this is the first textured prototype.
Asset path/version is fixed rather than overwriting material history.

## Implemented: assisted one-hole geometry importer

**Play → Import a course** (`#play/import`) accepts an OpenStreetMap course way link/ID or
a local Overpass JSON (`out geom`) / WGS84 GeoJSON FeatureCollection (≤2 MB). The Jackson Park,
Seattle shortcut is a public mapping pilot, not a certified reconstruction. Download uses the
public Overpass API; outages return a file-import fallback. Only the requested course ID goes
to that service. No shot data is transmitted.

**Open Jackson Park example** reads a bundled October 2, 2026 OSM snapshot locally, so the preview
workflow works without a successful network request. It is explicitly dated and incomplete.
Source data and attribution are in [the example package](../courses/examples/README.md).

Choose a mapped `golf=hole` path and set the name/par/tee label and optional scorecard yardage.
Preview projects longitude/latitude to local yards using a local equirectangular projection,
rotated along tee → endpoint; the saved transform records origin and axis. Both playing-line
and straight distances are shown. Scorecard disagreement produces a warning; it never rescales
geometry. This local projection is an approximation, not a survey or elevation model.

Supported surfaces: golf fairway/green/tee/bunker/water_hazard/lateral_water_hazard, and natural
water/wood/scrub. GeoJSON Polygon/MultiPolygon interior rings are supported. OSM relation geometry
is explicitly skipped with a warning; export those multipolygons as GeoJSON first. A missing
green at the hole endpoint blocks publication. Invalid/nonfinite/out-of-range coordinates,
degenerate/crossing rings, overlapping interior rings, and excessive payloads are rejected.
Missing/low fairway coverage is warned; unknown terrain plays as rough. Nearby-hole surfaces can
be included. A tee marker may be inferred from the path start and is disclosed.

The preview has an **artificial game boundary**, not official OB. Tee set, pin position, penalty
boundaries and terrain freshness require inspection. Review acknowledgement is required before
publication; importing does not start/end a session. The browser workbench now supports drawing
surfaces, moving/inserting/deleting vertices, interior cutouts, replacing the game boundary, tee/pin
placement, keyboard coordinates and Undo. Incomplete valid geometry can be saved as a draft;
publication requires the pin on a green, tee/pin inside the boundary and outside water/sand.
Invalid polygon edits are rejected without replacing the previous map. Official-rule boundaries
and penalty types still require simulator extensions. See [the operating workflow](COURSE_IMPORT_WORKFLOW.md).

**Save draft / Open draft** retains the source, metadata and local-yard edits in SQLite with revision
checks against concurrent overwrites. Export draft JSON is portable; opening it creates a separate
draft identity. Publishing first saves the draft and then adds an immutable library version.
Drafts are not playable until published. Review approval resets on edits/reopen. Finish a drawn
shape before saving or exporting; unfinished points are not persisted. Undo covers map edits in the
current editing visit; it is not a stored revision-history browser.

Saved holes appear in Play and round setup. The service copies the complete version into each
round. Repeating an identical import reuses its ID; changing geometry/settings creates another
version. SQLite metadata `course_import.v1.<id>` retains normalized geometry, original source
JSON, attribution, transform, warnings and review timestamp, all included in database backups.
No external downloaded imagery is added. OSM attribution and license link remain visible in play.

## Current direction: fictional holes first

On 2026-10-02 the user chose a simpler next step: generate plausible fictional holes from target
yardages, then create matching gameplay overlays. The [starter concepts](../designs/fictional-holes/README.md)
cover a 155-yard par 3, 365-yard par 4 and 525-yard par 5. These began as artwork candidates; target
yardages required uniform image registration and reviewed polygon tracing before publication.
Retain real-course import and Golfbert research as optional later work. Dynamic aim, distance,
ball and historical heatmap overlays stay separate from decorative pixels.

**Now playable:** Willow Cove, Pine Bend and Meadow Reach are bundled version-1 packages under
`courses/`, with production artwork in `web/art/`. `courses/build_fictional.py` preserves the reviewed
pixel traces and uniformly scales the saved tee/route/pin to 155/365/525 yards. Pine Bend and Meadow
Reach have shorter straight tee-to-pin distances, which the live map correctly displays. Fairway,
green, tee, water, sand and nature surfaces feed the existing classifier; the image rectangle is
an artificial game boundary. Edge tracing remains approximate fictional geometry. Overview, green
zoom, simple fills and boundary inspection use the same transform. See [play operation](2D_GAME.md).

## Deferred: registered real-course imagery and AI restyling

User direction: retrieve aerial imagery, identify boundaries, cross-check yardages, then improve
the appearance with AI. The geometry import/review/save portion above is implemented. Automated
imagery acquisition, image segmentation and mask-constrained AI restyling remain
proposed. A Jackson Park hole was imported into an isolated test database; its fairway coverage
is incomplete, so it is not a verified playable reconstruction. The club heatmap remains separate.

### Sources

- [OpenStreetMap golf tags](https://wiki.openstreetmap.org/wiki/Key:golf) describe tees, hole paths,
  pins, greens, bunkers, fairways and hazards. Use mapped geometry when present; actual coverage
  and freshness must be assessed for the selected course. These tags do not guarantee completeness.
- [USGS NAIP archive](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip)
  supplies orthorectified, georeferenced aerial imagery through EarthExplorer. Assess acquisition
  date, resolution and availability for the chosen location. This is aerial photography, not
  necessarily satellite imagery. Other countries require suitable regional/provider sources.
- Obtain hole numbers, pars and tee-specific yardages from the course's own scorecard or authorized
  data. Keep the original source/date and allow manual correction of extraction.
- Retain imagery usage terms, attribution and source identifiers. OSM data has attribution and ODbL
  obligations; consult its [license page](https://www.openstreetmap.org/copyright) before distributing
  imported data. AI restyling does not remove upstream obligations. Do not treat arbitrary map
  screenshots as distributable course assets.

### Suggested pipeline

1. Select course, tee set and one pilot hole. Gather source geometry, imagery and scorecard metadata.
2. Project geographic coordinates into a local metric coordinate system; preserve the transform
   between pixels, meters and game yards. Use georeferencing for scale. Cross-check scorecard
   yardages along the hole's playing route, rather than stretching terrain to match straight-line
   distance on doglegs. Report disagreements for review.
3. Use mapped polygons as a starting point. Image analysis can propose missing grass, sand, water
   and tree regions; store them as unverified candidates. Shadows, stale photos, tee locations,
   temporary works and official OB/penalty boundaries need review. A vegetation edge is not an OB rule.
4. Provide a review editor with original imagery, proposed geometry and labels. Correct shapes,
   identify tees and pin candidates, and mark confidence/source per feature. Never silently invent
   missing course rules or claim current pin positions from old imagery.
5. Generate or restyle visual layers using the reviewed shapes as masks. Composite material layers
   through those masks so AI cannot move an edge or invent a playable hazard. Preserve registration,
   scale and aspect ratio; compare original imagery, artwork and boundary overlays side by side.
6. Package a versioned course with local geometry, tees, pins, par/yardage metadata, original
   transforms, provenance, attribution and visual assets. Validate units, polygon intersections,
   surface priority and tee/green association. Freeze the course version in each played round.

The first milestone should be one reviewed real hole, not unattended eighteen-hole generation.
Current simulator geometry supports polygon/multipolygon surfaces and interior holes, alongside
legacy circles. Rich real-course support still requires official per-hole rules,
multiple tee sets/holes, and versioned backward-compatible rendering and scoring. Elevation/green
contours require separate data and physics work; aerial artwork alone does not supply putting slopes.

## Candidate commercial geometry source

[Golfbert evaluation](GOLFBERT_EVALUATION.md) records the 2026-10-02 pricing, polygon/tee/scorecard
capabilities and unresolved licensing questions. It is an optional importer candidate, not an
implemented integration or selected provider. Local caching, retained round geometry, distribution
and AI-derived artwork rights need clarification before adoption; imagery remains a separate concern.

## Verification

For the implemented visual layer, automated tests check saved-geometry placement, surface order,
simple-color fallback and unchanged data through overview/zoom rendering. Isolated browser review
checks aiming, terrain/boundary toggles, scoring and saved review at the target device sizes.
Every real-course import needs an independent alignment/yardage audit before its geometry can be trusted. Passing structural validation alone does not establish geographic accuracy.
