# TraceLoft future design language

2026-10-02 exploration requested by the user. These are generated visual concepts with synthetic
readings, not implemented screens or an approved replacement for the current dark studio.

## Orbit — immersive cockpit

![Orbit](orbit.png)

Graphite surfaces, ice-white typography and restrained cyan. A large central range canvas carries
the estimated flight; a right-hand latest-shot column and left equipment rail frame it. A compact
shot strip keeps history secondary. Best for standing at the range and reading one shot at a glance.
Tradeoff: perspective flight needs a separate measured top-down dispersion view.

## Vector — performance lab

![Vector](vector.png)

Bone-white surfaces, precise black typography and cobalt marks. A full-width measurement ribbon
sits above an asymmetric dispersion/flight workspace, with clubs across the bottom. Best for
comparing patterns and equipment. Tradeoff: brighter surfaces may be less comfortable in a dim bay.

## Aura — focused practice

![Aura](aura.png)

Dark plum and charcoal, lavender accents and restrained translucent panels. Target/progress live
in a task rail, the latest distance/error dominates the center, and upcoming targets sit beside it.
Best for guided ladders and putting drills. Tradeoff: the side rails must collapse on smaller screens.

User preference: Vector selected for further exploration. Develop its white, black and cobalt
language with a shared component system across modules. Orbit and Aura remain alternative studies.

## Vector refinements

The user prefers Vector. Two follow-up compositions retain its white/black/cobalt language:

- **Panorama:** full-width latest-shot ribbon, dominant dispersion plot, bottom equipment dock and
  recent-shot strip. Best for glanceable range feedback on iPad landscape.
- **Split Studio:** persistent navigation/equipment rail, latest-shot hero beside estimated flight,
  dispersion below and a compact club snapshot/history column. Best for desktop analysis density.

![Vector Panorama](vector-panorama.png)

![Vector Split Studio](vector-split-studio.png)

Prompts: `vector-riffs-prompts.json`. These are bitmap studies, not working interface controls.
Visual inspection: both preserve the selected palette and distinct compositions. Generated plotted
positions are approximate (particularly Split Studio's offline marker and flight endpoint), not
numerically validated. Rebuild with actual data scales, full bag access, responsive club lists and
verified touch sizing. Sidebar navigation is a proposal only; current routes/guards remain unchanged.

## Vector across the app

Five additional panel studies extend the selected palette beyond the range. Built-in imagegen
uses `vector.png` as the reference; full prompts are in `vector-panels-prompts.json`.

- Practice: modular activity selector with a separate return path to the active drill.
- Capture: source preview and controls, prominent stopped state, diagnostics and local backups.
- Play: spacious 2D course map with a compact round/equipment column and explicit demo identity.
- Analyze: filters, median/IQR trends, dispersion and equipment comparisons.
- Sessions: saved history and review identity, session completion warning and recoverable deletion.

![Practice selector](vector-practice.png)

![Capture](vector-capture.png)

![Play](vector-play.png)

![Analyze](vector-analyze.png)

![Sessions](vector-sessions.png)

These are visual studies, not implemented route changes. A side-by-side session list/review is a
composition proposal, not a change to review guards or exit destinations. Rebuild charts with real
scales/data and verify states, touch sizing and responsive behavior before replacing the studio.

Visual review notes: the generator carried live/session header controls into Practice and Analyze;
these need shared-state-aware treatment. Practice's illustrative112mph is ball speed, not club speed.
Capture was regenerated to correct inventedUSB ingestion and the stopped/live contradiction, but
minor stale “Live data” text and GSPro wording still need cleanup. Play's “Strokes remaining” should
be Strokes taken; demo shots must not imply live measured recording. Analyze dates/counts are
illustrative, not reconciled records. Sessions invents a30-day deletion retention policy: remove it,
keep recovery across restarts and scope Session over to the reviewed session. Its dispersion ellipse
must not be labeled IQR. No new retention policy, course geometry or recording behavior is proposed.

## Current-layout / Vector hybrid

The user prefers preserving the existing functional layouts and controls, with Vector's visual
styling and a disciplined type scale. This supersedes the earlier compositional redesign direction.
Three studies restyle actual saved app screenshots, preserving their visible controls and scroll crop:

- Range: `../range-ipad-pro-landscape.png` → `hybrid-range.png`.
- Practice: `../practice-categories-ipad.png` → `hybrid-practice.png`.
- Analyze: `../analyze-ipad.png` → `hybrid-analyze.png`.

![Hybrid range](hybrid-range.png)

![Hybrid practice](hybrid-practice.png)

![Hybrid Analyze](hybrid-analyze.png)

Requested styling: pale-grey page, white cards, dark navy text, cobalt selection/actions, retained
semantic warning/error/healthy colors. Requested type scale: page32, panel20, body/control14,
secondary/unit13, main metric36 px. Raster generation approximates this specification; it cannot
verify exact CSS sizes or operational completeness. These are cropped views of scrollable screens;
all below-fold functionality must remain in implementation. Full prompts: `hybrid-prompts.json`.

Visual comparison: Range retains all seven metrics, equipment/demo controls and source/target/view
switches shown in the original. Practice retains the four accordion groups and expanded iron drill.
Analyze retains all nine filter fields, session selection, apply/reset/export, four summary cards
and denominator/exclusion explanation. Its source screenshot is scrolled: full global navigation
remains above this crop in implementation; the generated brand at the crop edge is illustrative.
Analyze's teal dots are inherited from the reference; choose coherent series tokens during build.
Practice preserves the source's “1 activities” copy, which should be corrected to “1 activity”.
No operational, exact-font or responsive acceptance is claimed for generated images.

## Requirements retained for implementation

## Pure-white refinement

Latest user direction: retain functionality and composition, remove grey backgrounds and rounded
cards, use pure-white surfaces, square corners and straight dividers. Circular club selectors remain.

![White range](white-range.png)

![White Practice](white-practice.png)

![White Analyze](white-analyze.png)

Generated with built-in imagegen from the three hybrid references; exact prompt in `white-prompts.json`.
Visual review confirms white surfaces, square controls, line separation and retained visible controls.
Practice uses open accordion sections; Analyze combines summary cards into a divided row. Original
functional grouping remains. Inherited crop/copy/chart-color limitations still apply; font pixel sizes
are approximate. These are design concepts; no CSS, routes, service or saved measurements changed.

## Functional requirements
## Extended pure-white panels

The user requested wedge matrix, ladder drills, gap fit, Play and Analysis. “Gap fit” is represented
by the existing bag mapping/gapping workspace. Six studies use actual app screenshots as content
references and `white-range.png` as the styling reference, with no intended feature removal:

![Wedge matrix](white-wedge-matrix.png)

![Distance ladder](white-distance-ladder.png)

![Putting ladder](white-putting-ladder.png)

![Bag mapping and gapping](white-gapping.png)

![Play](white-play.png)

![Analysis](white-analysis.png)

Full built-in imagegen specification: `extended-white-prompts.json`. Some references are older
saved screenshots or scrolled views. They establish visible layout content, not current runtime
acceptance. Current complete navigation, bag selectors, exports and below-fold functionality must
remain when implemented. Full-height views are scrollable designs, not a claim they fit one iPad
viewport. Game artwork is a visual reference; generated pixels must never replace scoring geometry.

Visual review: matrix preserves cells/unavailable values, distance lookup and export/print;
both ladders preserve target/progress, warnings, charts/log and lifecycle/exclusion controls;
gapping retains median/IQR/sample/gap explanation and export; Play retains mapping/endpoints,
overlay toggles, aim/map controls, simulation/suggestions and round log; Analysis retains filters,
denominators, comparison and chart context. Minor generation drift remains: some matrix/cell controls
retain corner rounding; gapping/review and Analysis inherit the style reference's Practice highlight
instead of Sessions/Analyze; putting inherits old three-tab navigation. Restore full current navigation
and correct selected tabs in implementation. Play photo pixels/geometry are illustrative, not verified
unchanged output. Current circle tagging must replace older ladder dropdown references in a build.

## Retained behavior

- Preserve Capture → Practice → Play → Analyze → Sessions and existing lifecycle guards.
- Retain prominent recording warnings, sticky red Session over, explicit review identity and exits.
- Label estimated flight separately from measured distances; preserve unavailable values and units.
- Keep real club lists, all bag access and at least 44 px primary touch targets.
- Verify 1376×1032, 1366×1024, 1366×900, smaller tablets, desktop and 390 px phone layouts.
- Stack the latest reading, next target, charts and history in that order on phones; do not shrink
  the whole tablet composition. Generated screenshots do not verify responsiveness or interaction.

Full built-in imagegen prompts are recorded in `prompts.json`. Image text/chart geometry is
illustrative and must be rebuilt with real semantic controls and accurate plots before shipping.

Visual inspection: Orbit adds scenic imagery and unsupported weather/Take shot controls; these
are generation drift, not proposed functionality. Vector's plotted endpoints do not match the
measurement ribbon and its summary should use the existing median/IQR convention. Aura's
decorative flight is unlabeled and its target-band placement is imprecise; remove that flight or
label it Estimated flight, then plot each shot against its actual target. Its duplicated recording
indicator should collapse to the healthy header status. All three require stopped, ended and review
variants. No responsive or behavioral acceptance is claimed for bitmap concepts.
