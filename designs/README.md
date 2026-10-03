# TraceLoft interface concepts

The app was renamed from GolfData on 2026-10-02. Earlier concepts and screenshots retain their
historical branding. `traceloft-ipad.jpg` and `traceloft-phone.jpg` show the implemented wordmark
and navigation after the rename at 1366 × 1024 and 390 × 844 CSS viewports.

Generated with the built-in imagegen tool on 2026-10-01. These are illustrative visual targets;
chart numbers in generated artwork are not authoritative scoring examples. The app's actual charts
use saved measurements and per-shot targets.

Apply [DESIGN_PRINCIPLES.md](../DESIGN_PRINCIPLES.md) when translating these concepts into app screens.
It defines the shared hierarchy, visual language, session states, navigation and verification expectations.

- `putting-studio-concept.png`: bright studio direction.
- `putting-dark-concept.png`: alternative dark practice direction.
- `putting-studio-dark-concept.png`: selected direction, the first layout in a dark palette.
- `putting-dashboard-demo.png` / `putting-dashboard-wide-demo.png`: actual app layout captures with
  temporary demo data; no live session records were created.
- `web-practice-wide.png` / `web-practice-mobile.png`: implemented web interface at 1120×1300 and
  390×844 viewports, using five isolated test putts. These are browser renders, not live acceptance tests.
- `web-session-management.png`: session deletion, Undo and Recently deleted recovery controls,
  checked with isolated browser test data.
- `web-direct-access.png`: running studio opened directly without pairing after the local-access update.
- `web-session-over.png`: red completion warning and Exit session on the user's saved ten-putt session;
  viewed without changing its results or stopping capture.
- `web-session-over-mobile.png`: phone-width completion layout with isolated two-putt test data.
- `web-review-navigation.png`: saved review with Sessions selected and separate exits to the session
  list and Practice selector, checked on the user's saved ten-putt results without modifying them.
- `web-review-navigation-mobile.png`: the same review controls at phone width with isolated data.
- `navigation-audit.json`: screen/location evidence for the 125 passing isolated navigation checks;
  the complete map and guards are documented in `../NAVIGATION.md`.

Practice flow: choose a drill/game, configure its parameters, launch a dedicated view, then review.

`sqlite-storage-controls.png`: live Capture storage/export controls and verified local snapshot
feedback after migration; Google Drive is explicitly not connected. SQLite-backed review/Capture
layouts were checked at 390 px without horizontal page overflow.
Keep session feedback prominent and setup/log details secondary. Add future games through this shared
flow with their own parameters and scoring, rather than putting every control on the practice screen.

## Future design language exploration · 2026-10-02

[Orbit, Vector and Aura](future-language/README.md) explore futuristic range and drill layouts.
These are synthetic-data visual proposals; selection, responsive implementation and interaction
verification remain pending. The existing dark studio remains the implemented interface.

## Generation prompts

### Fictional course concepts · 2026-10-02

[Starter holes](fictional-holes/README.md): original 155-yard par-three, 365-yard par-four and
525-yard par-five aerial concepts. Built-in imagegen prompts are saved alongside them. All three
now have registered artwork, reviewed game polygons and playable version-1 packages. Implementation
screenshots and responsive checks are linked from their notes; the original PNGs remain preserved.

### Bright studio

Use case: ui-mockup. Create a high fidelity UI target image for GolfData Windows desktop golf putting analysis app. Portrait-ish 4:5 dashboard viewport, only app UI no device frame. Bright premium sports studio: off white background, white cards, deep navy typography, teal highlights, generous spacing, highly readable numbers from several feet away. Top slim header GolfData, tabs Practice Capture Sessions, green capture connected dot. Title Putting practice / Pace + start line. Compact controls collapsed New drill. Dominant latest-putt row showing illustrative demo metrics: 4.2 mph, +0.2 mph pace error, 0.4 degrees R start line, In window. Large two chart cards below: Pace chart ball speed mph by putt 1 through 8, horizontal teal target line4.0 with pale green band3.7 to4.3, latestpoint highlighted; Start line horizontal gauge ranging Left2 degrees through0 to Right2 degrees with tolerance +/-1 shaded and latest marker0.4R. Then large Start line trend chart direction vs putt with shaded +/-1degreeband. Session8/10,6/8inwindow75percent progress strip. Tiny secondary Shot log table bottom. Footer DEMO DATA — DESIGN CONCEPT. Crisp realistic implementable dashboard, clean clear graph axes. Do not show modeled ball trajectory, hole position or inferred stopping distance. Do not add photo golf course background.

### Alternative dark practice

Use case: ui-mockup. Create a high fidelity modern GolfData desktop putting practice app design target. Portrait-ish4:5 dashboard only, no monitor hardware. Dark premium practice view slate navy background, raised charcoal panels, mint teal target bands, off white large readable typography, amber miss markers. Navigation GolfData / Practice / Capture / Sessions with connected status. Latest putt huge 3.5 mph, pace -0.5mph, start line 1.2degrees L, Outside window. Big pace-by-putt graph target4.0 shaded3.7to4.3 with latestdot below band. Big startline gauge targetcenter0 +/-1degreezone and marker1.2left. A large session direction trend graph, previousgraydots and amberlatestpoint. Session7/10,4/7inwindow57percent. Compact secondary log below graphs and Finish session button. Footer DEMO DATA — DESIGN CONCEPT. Sport instrument feel, accessible contrast, very clean graphs, roomy cards, no inferred roll distance, no trajectory simulation, no photographic backgrounds.

### Selected studio layout in dark colours

Reference/edit target: `putting-studio-concept.png`.

Use case: ui-mockup. Create a dark-theme version of this exact bright GolfData concept, retaining its clean card layout, hierarchy and typography. Slate/navy background, slightly lighter slate cards, bright offwhite text, restrained mint teal target bands, amber misses. The user wants the FIRST bright concept in a dark palette, not a different layout. Keep large latest putt numbers and two-column charts: pace-by-putt on left, latest-startline horizontal gauge plus direction trend on right. Session progress top right. Change New drill control to conspicuous Edit targets button. Add compact visible Fixed / Random pace segmented control near title, with Random pace selected and readable Min3.0mph Max6.0mph, Next target4.6mph. Demo pace graph must depict varying target band per shot; label Speed and Target. Latest illustrative putt4.2mph against target4.0, +0.2mph,0.4degreesR, Inwindow. Keep shotlog secondary below charts. Footer DEMO DATA — DESIGN CONCEPT. No inferred distance or physical trajectory. High fidelity implementable dashboard, portrait4:5.

`distance-ladder-setup-concept.png` and `distance-ladder-live-concept.png`: approved full-swing
ladder for wedges, irons and custom yardages. Setup chooses carry/total, distances, step, shots per
target, rounds, window, order and an optional club/session label. The live concept emphasizes latest
reported carry, signed short/long error, next target, rung progress and two large distance charts.
Illustrative data only: these are generated concepts, not screenshots of implemented features.
The concepts originally used manual session labels; the implemented ladder now includes editable
multiple bags and per-shot club selectors. Numeric full-swing capture
still needs verification. Prompts/tool provenance are saved in `distance-ladder-prompts.json`.

Implemented layout evidence: `distance-ladder-setup-web.png`, `distance-ladder-live-web.png`,
`distance-ladder-mobile.png` and `distance-ladder-setup-mobile.png` use labeled isolated test data.
`distance-ladder-setup-live-app.png` shows the real idle app after reload, without creating a session.
The concepts are design references; actual scoring and source validation are described in
[Distance ladder operation](../docs/DISTANCE_LADDER.md) and WORK_LOG.md.

`distance-ladder-equipment-web.png` and `distance-ladder-equipment-mobile.png` show per-shot bag/club
selection with isolated synthetic shots from two bags. `distance-ladder-equipment-live-app.png` shows
the real app after reload with its preexisting active ladder preserved; no real shots were added.

`club-tap-ladder-concept.png`: proposed one-tap replacement for the live club dropdown: two rows of
seven circular club buttons, with a filled mint selection and checkmark; bag remains a dropdown.
`bag-selector-options-concept.png` compares the bag dropdown, direct bag tabs and a bag-identity card
with Change bag. Generated by built-in imagegen; prompts/provenance in `club-tap-prompts.json`.
These are mockups for review, not implemented screens. The illustrative 14-club bag does not change
the actual editable catalog or impose a 14-club cap. Phone layout should wrap into a touch-friendly
grid and preserve all actual clubs without shrinking tap targets; implemented in the selected revision below.

`club-tap-ladder-bag-column-concept.png`: revised preferred layout after user feedback. Listening
status precedes tagging. Three bag tabs form a narrow left column; fourteen smaller club circles
sit in a single row to the right, retaining selected checkmarks and next-shot identity. Bag names
are illustrative quick choices, not a storage limit. Prompt iterations/tool provenance are in
`club-tap-bag-column-prompts.json`. This is a mockup; the implemented version follows the later request
to use the header for healthy capture and retain only recording warnings above tagging.
`club-tap-ladder-web.png` / `club-tap-ladder-mobile.png` show the actual compact picker with isolated
synthetic shots. All 15 default clubs remain available; More bags reaches additional bags, and phone
circles wrap with 44 px tap targets. These images do not verify live full-swing OCR.

`putting-ladder-web.png` / `putting-ladder-mobile.png`: new distance metrics, per-rung distance graph and next-target pace/progress with isolated synthetic putts. Estimates are not physical outcomes. Model selection was added following the academic comparison; current screenshots use the default constant-braking baseline.
`vdd-capture-web.png`: actual web Capture screen with VDD selected at 3840 × 2160 and its independent
calibration preview. Capture is stopped; calibration/replay did not add saved session measurements.
Phone-width VDD selection and profile/Practice navigation were checked; details are in WORK_LOG.md.
`navigation-five-sections-web.png` and `navigation-five-sections-mobile.png`: actual reordered
Capture/Practice/Play/Analyze/Sessions header, with an unchanged saved review on desktop and the
Analyze Coming soon page at 390 × 844. Play/Analyze feature implementation remains future work.


`driving-range-web.png`, `driving-range-mobile.png` and `driving-range-charts.png` show the implemented Driving range with
explicitly labeled synthetic data on an isolated service. The dark studio uses compact bag/club
controls, large reported-value tiles, estimated carry/total dispersion and side flight, shape
frequencies and a separate shot cleanup workspace. These are actual browser screenshots, not
concepts or physical ball-flight validation. Operation: [Driving range](../docs/DRIVING_RANGE.md).


`driving-range-club-colors-top.png` and `driving-range-top-mobile.png`: 2026-10-02 actual isolated
browser screenshots of per-club scatter colors/legend and the estimated top-down flight profile.
Data is synthetic. Top-view axes are independently scaled and the path ends at carry.


`club-snapshot-robust-web.png` and `club-snapshot-robust-mobile.png`: 2026-10-02 actual isolated
browser screenshots showing median/IQR, per-metric sample counts and the snapshot above Shot
workspace. Synthetic 7 iron/PW samples; desktop 1440 × 1100 and phone 390 × 844. The phone table
scrolls horizontally within the card. These images do not establish physical measurement accuracy.


`range-ipad-pro-landscape.png` and `range-ipad-pro-snapshot.png`: 2026-10-02 isolated browser
screenshots at 1366 × 1024 and 1366 × 900 CSS px. Seven reported/synthetic shot metrics fit one row;
Club snapshot stays above the workspace. `range-ipad-layout-checks.json` records five viewport
checks, metric-cell bounds and primary club touch-target sizes. These are Chromium viewport checks,
not physical iPad Safari, touch, LAN or ball-flight validation. iPad Pro 13-inch / 12.9-inch landscape
is the primary design target going forward.


`range-dispersion-circles-ipad.png` and `range-dispersion-circles-mobile.png`: actual isolated
synthetic range at 1366 × 1024 and 390 × 844. Three bag/club combinations share dot/ring/legend colors;
one excluded shot remains lighter and outside the calculation. The rings are median-centered 80%
radial envelopes, displayed with independently scaled axes. `range-dispersion-layout-checks.json`
records counts/colors and overflow checks at both large iPad sizes, reduced height and phone width.


`range-compact-legend-ipad.png` and `range-dispersion-info-ipad.png`: actual isolated 1366 × 1024
browser screenshots of the name-only legend and on-demand dispersion explanation. Synthetic 6 iron
and 8 iron shots. These supersede the verbose legend presentation in earlier range screenshots.


`range-expanded-scatter-ipad.png` and `range-expanded-scatter-mobile.png`: actual isolated browser
screenshots after the plot was made to fill spare vertical card space. Synthetic five-club session;
1366 × 1024 and 390 × 844 viewports. `range-scatter-sizing-checks.json` records dynamic plot/viewBox
sizes across large iPad, reduced-height, stacked tablet and phone layouts. Text and dots retain their
proportions; the card's legend/summary now sit below the expanded plot instead of above unused space.


2026-10-02 five-feature delivery screenshots (all isolated synthetic data):
- `practice-categories-ipad.png` / `practice-categories-mobile.png`: collapsible Practice groups.
- `bag-mapping-ipad.png` / `bag-mapping-mobile.png`: collection coverage, medians/IQR and gaps.
- `wedge-matrix-ipad.png` / `wedge-matrix-mobile.png`: named swing cells and distance suggestions.
- `analyze-ipad.png`, `analyze-charts-ipad.png`, `analyze-mobile.png`: cohort filters and robust trends.
- `golf-sim-ipad.png`, `golf-sim-green-ipad.png`: full-page desktop-browser captures at 1366px width;
  `golf-sim-preview.png` is a course/putting detail from that viewport; `golf-sim-mobile.png` shows
  the completed-round warning at 390px. Layout checked at 1366×1024, 1376×1032 and 1366×900;
  these are Chromium viewport checks, not actual iPad Safari/touch validation.

`golf-sim-score-ipad.png`, `golf-sim-score-mobile.png` and `golf-sim-aim-ipad.png` show the
score breakdown and map-distance refinement using isolated demo rounds.
`golf-sim-score-aim-checks.json` records additional landscape/phone layout and feet checks.

[Club preview concept](GAME_CLUB_PREVIEW.md) and `golf-sim-club-preview-concept.png` propose a
mapped club dispersion heatmap over the selected aim. Generated mockup with illustrative data
and original schematic course art; the image is not a validated prediction. The functional implementation is now documented below.

`golf-sim-club-preview-concept-v2.png` is the current preview mockup: map taps plus Aim at pin,
with left/right step buttons removed per user feedback. The earlier concept is retained for history.

`golf-terrain-overview-ipad.png`, `golf-terrain-boundaries-ipad.png`, `golf-terrain-green-ipad.png`
and `golf-terrain-mobile.png` show actual isolated gameplay with the first AI terrain materials.
`golf-terrain-layout-checks.json` records responsive checks. Surface geometry is unchanged;
[implementation and import direction](../docs/COURSE_ART_AND_IMPORTS.md) distinguish this textured
prototype from the more organic conceptual course artwork and future real-course imports.

`meadow-v2-aerial-ipad.png`, `meadow-v2-boundaries-ipad.png` and `meadow-v2-green-ipad.png`
show actual isolated play with the continuous aerial course, hand-traced polygon boundaries
and registered green zoom. This replaces tiles for new rounds, while retaining legacy rounds.

`tour-demo-matrix-ipad.png` shows the 12 sampled wedge cells from the separate Tour reference pack.
`course-import-review-ipad.png`, `course-import-review-phone.png` and `course-import-play-ipad.png`
show the geometry importer and an isolated Jackson Park hole prototype. Incomplete fairway coverage
is explicitly warned; these are functional screenshots, not verified aerial course reconstructions.

`golf-club-heatmap-ipad.png` and `golf-club-heatmap-phone.png` show the implemented historical
club preview using isolated synthetic mapping data. `golf-club-heatmap-layout-checks.json` records
1366×1024, 1376×1032, 1366×900 and 390×844 viewport/44px-control checks.

`golf-club-heatmap-blue.png` shows the subsequent user-requested visibility refinement in the
active demo round: common bright blue, stronger shading and a bold solid outlined circle.

`analytics-demo-trend.png` shows the existing Analyze UI populated with the new eight-week
synthetic history, filtered to Analytics lab A / 7 iron at 1366×1024.

`course-workbench-ipad.jpg` and `course-workbench-phone.jpg` show the actual draft editor
with a selected water polygon. Jackson Park is incomplete example geometry in an isolated DB,
not a verified real-course recreation.
