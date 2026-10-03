# Map-first Play — Option 1

Approved and implemented 2026-10-03. Follow the pure-white Vector language and
[design principles](../../DESIGN_PRINCIPLES.md).

The compact scorecard contains current-hole components, round total and correction counts.
The setup bag is referenced beside compact club buttons. A full-width map carries distance,
lie, next stroke, estimated putting pace and the latest result. Ball-to-aim and aim-to-pin
readouts stay in a fixed lower-left position for legibility instead of following the tapped point.

Dispersion controls sit below the map in a disclosure; closing it leaves the heatmap visible.
The summary retains club, Carry/Total, sample count, source and overlay status. The live shot
log, map options/hole guide, demo input and bag suggestions also expand in place. Scorecard
and shot log open in ended/review states. Existing corrections and explicit exits remain visible.

The responsive camera fills the wide panel with uniform world scale. Overview trims peripheral
scenery on shorter landscape screens, preserving tee, pin and playing route. Green view matches
the panel aspect ratio and clamps inside the artwork. Phone overview retains the complete course;
readouts move outside the image. Scoring polygons, aim and density share the same camera transform.

## References

Course setup now offers Full 18, Front 9 and Back 9 as touch-sized radio cards with selected
par/yardage. Course changes update totals; Back 9 retains hole numbers 10–18. Only selected holes
appear in the expanded scorecard and saved review. [iPad setup review](round-options-ipad.png).

- [Approved generated concept](approved-concept.png): visual direction, not application evidence.
- [Implemented iPad landscape](ipad-landscape.png): 1376×1032 browser viewport, isolated demo
  Sheboygan Straits round with synthetic Tour mapping. This is the application, not generated art
  composited into a UI mockup.
- [Responsive course fit](course-fit-ipad.png): 1366×900 Boulder Beach overview with scoring
  boundaries enabled, after replacing the letterboxed camera.

Verified browser viewports: 1366×1024, 1376×1032, reduced-height 1366×900, desktop 1600×1000
and phone 390×844. No physical iPad Safari/touch or LAN verification was performed.
