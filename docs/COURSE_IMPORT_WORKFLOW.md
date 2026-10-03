# Importing a course into TraceLoft

The implemented workbench imports **one hole and one tee position per published version**.
Open **Play → Import a course**. It does not take capture ownership or change an active round.
The bundled Jackson Park snapshot is a workflow example with incomplete fairway mapping, not a
verified recreation. Use a separate test instance for experiments with invented boundaries.

## 1. Collect the source

Paste an OpenStreetMap course way link/ID, open an Overpass `out geom` JSON file, or use a WGS84
GeoJSON FeatureCollection. Geometry files are limited to 2 MB. Include a `golf=hole` LineString
running from tee toward green and available fairway/green/tee/bunker/water/wood polygons.
OSM relations currently require conversion to GeoJSON Polygon/MultiPolygon. Invalid rings must
be repaired in the source before import; missing surfaces can be added inside TraceLoft.

Keep source links, source date and usage/attribution information. Use the course's scorecard to
check hole number, par, tee set and yardage. Course lookup by name and automatic scorecard
extraction are not implemented. The OSM request sends the requested course ID, never shot data.

## 2. Select and check scale

Choose the mapped hole; enter a recognizable name, par, tee label and optional scorecard length.
**Preview boundaries** computes local yards from geography. Compare both the playing-line distance
and straight tee-to-pin distance. A dogleg can legitimately differ from the straight distance.
Scorecard length is a cross-check and display value; it never stretches the course geometry.

## 3. Correct the map

- **Shape** selects a surface or game boundary and highlights its vertices.
- **Inspect / select vertex** selects a point. **Move selected vertex** then places it with a map tap.
- **Draw new surface** adds fairway, green, tee, sand, water or nature. Tap at least three points,
  then **Finish drawn shape**. **Cancel drawing** discards unfinished points.
- **Draw game boundary** replaces the artificial play boundary. It is not official out of bounds.
- **Draw interior cutout** removes an interior area from the selected polygon.
- **Place tee / Place pin** sets those positions with a map tap.
- **Precise coordinates / keyboard editing** provides vertex selection, lateral/forward yard input,
  insertion and deletion. This is also useful for points outside the visible map.
- **Undo map edit** reverses the last applied correction. Reopening clears the in-memory Undo stack.

Shapes must not self-intersect; cutouts must be valid and inside their outer polygon. Coordinates
stay in the original hole's projected yard frame even after moving its tee or pin. The original
source remains intact. Missing terrain plays as rough; nearby holes may need removing from the map.
The current editor has no zoom/pan, snapping, vertex dragging or source-image background.

## 4. Save and resume

**Save draft** stores the source, settings and applied corrections in the local SQLite database.
Choose it under **Saved draft → Open draft** to resume on any connected device. Saving from a stale
revision is rejected: export your local version first, then reopen the server draft to reconcile.

**Export draft JSON** downloads a portable file. Open it with the geometry file chooser; it becomes
a separate unsaved draft and must be saved on the destination server. Draft files allow up to 4 MB.
Database backups include server drafts. Session deletion does not remove courses or drafts.

Finish or cancel drawing before leaving, changing tools or editing hole settings: unfinished drawing
points are not part of the draft. Applied unsaved edits survive app navigation in the same page,
but not a page refresh. Refresh/close warns about unsaved changes; save explicitly before leaving.
Changing the selected hole starts separate geometry and clears the prior draft identity.

## 5. Review and publish

Fix blocking issues: pin outside a green, tee/pin outside the boundary, or tee/pin inside water/sand.
Review warnings for incomplete fairway coverage, inferred tees, yardage mismatch and nearby surfaces.
Confirm positions and boundaries against a suitable source; a green validation message establishes
structural validity only. Acknowledge the review, then **Publish hole to Play**.

Publication saves the current editable draft and creates a fixed library version. If library saving
fails after draft saving, the draft remains recoverable. In Play, choose **Set up this hole**.
Start with a demo round and check map distances, lies, hazard penalties and green transitions.
Existing rounds retain their original geometry even when a corrected version is published later.

## Next stage: imagery and full courses (not implemented)

1. Obtain permitted, georeferenced aerial imagery for the selected location and date.
2. Register the image against the saved geographic/yard transform; verify tee, green and hazard edges.
3. Review missing-boundary proposals; record confidence and provenance.
4. AI-restyle only after geometry review, compositing through fixed masks so artwork cannot move
   playable edges. Retain original imagery and a boundary overlay for comparison.
5. Package multiple holes and tee sets with explicit rules and versioned assets.

Automatic imagery acquisition, segmentation, AI restyling, eighteen-hole sequencing, official
penalty-zone rules, elevation and sloped greens remain separate milestones. The first target is
one independently reviewed real hole. [Architecture and sources](COURSE_ART_AND_IMPORTS.md).
