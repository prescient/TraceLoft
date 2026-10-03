# TraceLoft design principles

These principles capture the product direction established with the user. Apply them when adding
or changing interfaces, drills, games and analysis tools. They are design requirements for future
work, not a claim that every existing screen already meets them. Later user instructions can change
the direction; update this document when a principle changes.

## 1. Design for the golfer standing at the putting setup

The practice screen should answer three questions at a glance: what happened on my last putt,
what is my next target, and are new putts being saved to this drill?

- Give the latest measurements, target, outcome and progress the strongest visual hierarchy.
- Use large numbers and charts readable from several feet away. Keep units and direction visible.
- Put the detailed shot log, statistics and diagnostics below the main feedback or in a secondary view.
- Avoid competing controls and decorative content that make the golfer search for the next action.

## 2. Keep practice modular

Use collapsible Full swing / Irons / Wedges / Putting sections in the selector, preserving expanded
categories on return and keeping active-session access outside them. Reuse shared drill implementations
with category presets; expansion never changes session state.

Use the shared flow: **Practice selector → drill/game setup → active session → results/review**.

- Give each drill its own description, relevant parameters, targets and scoring.
- Share capture, session storage, navigation and common visual components across modules.
- Add ladder drills, wedge matrix collection and future games through this flow as they are
  implemented. Connect bag management and analysis to practice results without forcing unrelated
  settings into the runner. Keep unimplemented ideas in the backlog rather than presenting working controls.
- Full-swing ladder uses reported carry/total in yards, a prominent next yardage and latest short/long
  error, and per-shot distance targets. Keep it visually and semantically distinct from putting feet
  estimates. Missing distance must leave the target unchanged with clear feedback.
- Put the full-swing bag/club selector within easy reach above feedback. Show the saved next-shot
  selection; switching bags clears the club choice. Snapshot tags per shot and keep earlier tags
  visible when the next-shot choice changes. Catalog editing must not relabel recorded history.
- Show actionable recording warnings above full-swing tagging; healthy activity belongs in the header.
  Use a compact left column of three
  quick bag tabs and direct circular club buttons to its right. Keep club buttons smaller than the
  original concept while retaining at least 44 px touch targets; wrap them on narrow screens.
  More bags keeps every bag reachable; three quick choices are not a storage limit. Empty slots offer
  Add bag. Render the actual editable club list, without imposing the illustrative 14-club limit.
  Keep bag controls within the rail's padded width with a clear gutter before its vertical divider;
  long names use ellipsis with accessible full-name labels. Stack full-width More bags and Manage bags
  beneath the tabs, leaving BAGS as a standalone heading. Keep primary controls at least44px tall.
- Offer fixed and random targets when appropriate. Make the mode and next target explicit;
  retain each shot's actual target so scoring and review remain meaningful.

## 3. No screen should be a dead end

- Main navigation follows **Relay → Practice → Play → Analyze → Sessions**. Play contains the game and Analyze contains comparisons; both retain global navigation and
  explicit exits. New placeholders must be clearly labeled until implemented.

- Keep the screen title, selected navigation section and action labels consistent with its purpose.
  Saved reviews belong to Sessions, even when they reuse the practice charts.
- Provide explicit exits with predictable destinations. Review needs both a path to Sessions and
  a path to the Practice selector; long session/review screens need exits above and below the log.
- Keep navigation separate from ending a session. Visiting another screen leaves the drill active;
  End session, confirmed Exit session and Abandon session have explicit lifecycle effects.
- Support Back, Forward, refresh and session links. An old link must identify the original session,
  rather than silently switch to a newer drill. Explain missing sessions and provide a useful exit.
- Explain guards and draft behavior. If another drill blocks setup, provide a path back to it.
  Do not imply unsaved parameter edits have persisted.
- Update [NAVIGATION.md](NAVIGATION.md) whenever screens, routes, exits or guards change.

## 4. Make recording state unmistakable

Global capture and an active practice session are separate states. A running bridge does not mean
that the drill on screen is accepting putts.

| State | Required feedback |
| --- | --- |
| Active drill; healthy run capture enabled | Header capture indicator, target and progress; no duplicate listening bar |
| Active drill; capture stopped or preview only | Prominent warning that putts are not being recorded, with the next action |
| Session finished automatically or manually | Large red Session over banner stating that no more putts will be saved to this session |
| Saved or interrupted review | Clear review identity; never present it as a resumed live drill |
| Read, connection or save failure | Visible explanation and recovery action; retain confirmed results where possible |

Keep the completion warning visible while scrolling. Pair status colors with text or icons;
the golfer should not have to infer recording state from a small connection dot or frozen graph.

Detailed capture configuration/errors belong to TraceCapture, rather than a second raw error box
in practice. Keep practice recording-state warnings and generic capture-attention feedback visible;
session/save errors remain specific to practice.

## 5. Use graphs to explain feedback

- Show measured pace and start line with labeled axes, units, target lines and tolerance zones.
- Highlight the latest putt and preserve enough session context to show progress and consistency.
- For random pace, plot each putt against its own target rather than a single final target.
- Distinguish excluded observations without erasing them. Show included sample counts and explain
  that exclusions do not remove a captured repetition.
- Keep scales and precision understandable; changes in chart scale must not exaggerate improvement.
- Use summary statistics to support the graphs, rather than crowd out the latest-putt feedback.
- Range Club snapshot uses median and IQR to reduce sensitivity to extreme shots. State the IQR
  convention and available sample count for each metric; do not substitute zero for missing values
  or show a one-reading spread as established consistency. Keep absolute offline distinct from signed
  direction, and preserve mishits unless explicitly excluded from the selected analysis.

## 6. Separate measurements, estimates and outcomes

- Display only measurements actually collected or explicitly entered. Missing data is unavailable,
  not zero. Keep units and left/right sign conventions consistent across capture, practice and review.
- A pace/start-line window success is **In window**; it does not establish a holed putt.
- Scraped launch measurements do not establish stopping distance, proximity, skid or final ball position.
- Label modeled putting travel, simulator outcomes and club suggestions as estimates. Make their
  assumptions and calibration relevant to the decision visible without cluttering the practice screen.
- Distance models need validation against recorded outcomes and the applicable surface/settings.
  Do not present a provisional Stimp equation or community chart as a verified GSPro calculation.
- Bag and wedge recommendations should reflect the selected bag, available samples and uncertainty.
- For future range/round analysis, distinguish reading validity, statistical unusualness and shot cost.
  Automatic outlier detection flags candidates by default. Scoped exclusions preserve the original
  shot and its reason/history; real mishits stay available in all-valid inconsistency analysis and
  counted strokes/penalties stay in round results. Show selected versus all-valid counts/results and
  label modeled strokes impact as an estimate. This is a design requirement, not implemented behavior.
- Range Data cleanup now reviews shots by club and previews bulk reassignment/exclusion with explicit
  selected counts/scope, before/after effects and Undo. Save captures immediately; approve analysis
  separately. Range corrections preserve original assignments; future sim cleanup must preserve played
  outcomes. Future trend views show assessed/reviewed
  denominators, coverage and policy/baseline changes so data cleanup is distinct from skill improvement.

## 7. Maintain the chosen visual language

Vector is the implemented web visual language as of 2026-10-03. Use the approved
[pure-white hybrid studies](designs/future-language/README.md), preserving the existing functional
layout and every control. Earlier dark studio and alternate layouts are historical references.

- Use pure-white page and panel surfaces, square panel/control edges, thin straight dividers and
  no shadows. Retain circular club selectors, status dots and info icons.
- Reuse shared tokens in [studio.css](web/studio.css): navy text, cobalt primary actions/selection,
  green healthy/success feedback, amber warnings and red errors/destructive actions. Keep the
  sticky Session over banner solid red with white text.
- Use page headings at 32 px (28 px on phones), panel headings at 20 px, body/controls at 14 px,
  units/secondary labels around 13 px and latest metrics at 36 px. Wrap instead of shrinking
  the whole interface. Primary controls remain at least 44 px high.
- Chart labels and club colors must contrast against white. Selected scatter points use a dark
  outline; excluded points retain a lighter tint of the bag/club color and dashed edge.
- Compare implementations with the selected concept for hierarchy, chart prominence and overall feel.
  Concept numbers are illustrative; real charts and acceptance evidence use recorded or labeled test data.
- Avoid adding unrelated themes, decorative course imagery or dense settings to the practice runner.
- Use spare chart-card space for the plot rather than empty padding. In the wide range layout,
  dispersion grows with the adjacent flight/shape panels while retaining readable text/markers and
  keeping its legend/summary below. Stacked layouts retain bounded chart proportions.

## 8. Target iPad Pro landscape; support desktop and phone

- Primary device: **13-inch / 12.9-inch iPad Pro in landscape**. Design and verify at CSS viewports
  1376 × 1032 and 1366 × 1024, plus reduced height (1366 × 900) for browser chrome. CSS pixels,
  rather than the display panel's physical pixels, determine responsive layout. Record viewport
  emulation separately from actual iPad Safari, touch and LAN verification.
- Keep the range latest-shot bar readable as one row of seven readings at the primary landscape
  sizes. Wrap on smaller widths; preserve units, unavailable values and source/model distinctions.
- Keep main actions reachable with touch and keyboard; use meaningful labels and visible focus.
- Aim for at least 44 px touch targets for primary controls. Do not rely on hover to expose essential actions.
- Stack charts and cards on narrow screens. Keep the page within the viewport; allow a wide shot table
  to scroll inside its own container without pushing navigation off screen.
- Use headings, labels and status announcements that communicate purpose beyond visual styling.
- Check the primary iPad Pro landscape sizes, a smaller tablet fallback and a phone around 390 px wide. Verify exits and
  warnings at both the top of the screen and after scrolling through the log.

## 9. Keep the service responsive and the user's data recoverable

- The background Python service owns shot input, storage and shared practice state; browsers present and control it.
  UI rendering and network requests must not block shot detection or create competing workers.
- Preserve the user's local workflow: localhost access without pairing; LAN access is an explicit
  launcher option. Keep GSPro sending explicit and off by default on service startup.
- Persist confirmed results and report failed saves. Keep finish, abandon, exclusion and deletion distinct.
- Use recoverable session deletion with Undo/Restore. Restoring results does not resume a finished drill.
- Keep logs, crops, calibration and training backups separate from session deletion and UI changes.
- Keep the screen-captured receiver unobstructed and at its calibrated size during live use and verification.

## 10. Verify the whole interaction before calling it done

For an interface change, check the affected journeys, not only the new button or screenshot:

- Enter the screen, perform its main action, cancel where appropriate, leave it and return.
- Check live, completed, abandoned, review-only, empty and error states relevant to the change.
- Confirm the screen title, selected section, exits, recording status and browser history agree.
- Verify responsive layout and keyboard/touch access; record screenshots for material visual changes.
- Use isolated session files and a separate service for state-changing QA. Preserve real sessions and
  avoid interrupting live capture unless the task requires it.
- Run checks appropriate to the changed behavior. Record results, failures and unverified live behavior
  honestly; an old screenshot or audit is historical evidence, not proof of a new implementation.
- Update affected documentation and [WORK_LOG.md](WORK_LOG.md) with the change and verification evidence.

## Related documents

- [AGENTS.md](AGENTS.md): development entry point and requirements for applying these principles.
- [NAVIGATION.md](NAVIGATION.md): implemented paths, guards, draft behavior and navigation audit.
- [designs/README.md](designs/README.md): visual targets and implementation screenshots.
- [README.md](README.md): app architecture, launchers and current operating instructions.
- [DECISIONS.md](DECISIONS.md): technical decisions and their evidence.
- [BACKLOG.md](BACKLOG.md): feature priorities, planned research and remaining acceptance work.


## Range-specific interpretation

Driving range uses reported outcome tiles plus separately labeled OpenGolfCoach model views.
Carry/total plots identify coordinate provenance; target-width decoration must not imply verified
lateral scoring. Model failure never discards the shot. Demo sessions display a persistent synthetic
identity and cannot accept live shots. Cleanup exposes scope/counts, a reason, history and Undo;
all-recorded comparisons preserve evidence of inconsistency. See [range operation](docs/DRIVING_RANGE.md).

Range scatter uses bag/club colors with a labeled legend; preserve club color on selection and use
a dark outline/size change for focus. Excluded points keep a lighter tint of their club color and a
dashed edge; untagged points use neutral gray. Show excluded context in the default chart, while
the default table and summaries remain included-only. Removed shots stay hidden by default.

Dispersion circles share bag/club colors and use only included positions from the selected plot
source and distance. Keep the legend to colored bag/club names; put the explanation in an info
button beside the chart title, accessible by hover, focus and tap. Describe coverage and minimum samples: current circles use coordinate medians
and a nearest-rank 80% radial extent, requiring five positions. Do not present empirical shot spread
as a confidence interval or future-shot probability. Note independently scaled axes; circle extents
must not be clipped. Recompute from corrected tags, filters and cleanup state in live and saved views.

## Cross-session analysis

Use median and IQR with metric-specific sample counts; preserve missing values. Keep demo and real
cohorts separate. Explain session-attempt counting, exclusions and source provenance. Manual exclusion
rate is not an automated outlier/mishit rate. Warn when mixed clubs/intents make trends incomparable.

## Simple golf games

Multi-hole rounds keep the current hole's played shots, penalties and gimmes separate from round
totals. Pause scoring visibly between holes and require Next hole before accepting play at the next
tee. Keep the scorecard compact during play, expandable by touch/keyboard, and open in saved review.
Offer Full 18, Front 9 and Back 9 during course setup with touch-sized choices and selected
yardage/par. Freeze that selection when launching; keep original hole numbers. The scorecard,
completion boundary and review choices contain only selected holes. Corrections must use saved
hole identity so back-nine scores survive reopening the final hole. Imported single holes keep
their single-hole flow without irrelevant nine-hole controls.
Review selects frozen holes without moving the active ball. Distinguish ended-early rounds and
unplayed holes from completed scores; never count analysis exclusions as mulligans.
Keep Play header actions in order: Mulligan, Misread, End round, Play menu, Exit round.
Show correction counts in the scorecard summary and tuck the audit history inside its expansion;
do not add a separate replay card. Button help identifies the latest scored attempt and effect.
Select the bag in course setup. During play, use the full width for compact Club for next shot
buttons and reference the selected bag by name, without repeating bag management or selection.
Practice retains its bag-and-club selector. Preserve the setup bag when changing or clearing a club.
Use the [approved map-first layout](designs/play-map-first/README.md): current-hole shots,
penalties, gimmes and total share the compact scorecard strip with round totals. Give the map the
full content width; put distance, lie, next stroke and estimated putting pace on the map instead
of a separate position card. Keep aim-distance readouts and latest-shot feedback legible over art.
Below it, collapse dispersion controls and the live shot log by default. Collapsing controls must
never turn off the heatmap; show club, endpoint source, sample count and overlay state in the summary.
Put map options, keyboard aim coordinates and hole guidance in a disclosure. Keep stop/exit actions
and recording/completion warnings directly visible. On phones, move map readouts outside the art
and wrap controls. Preserve uniform world scale and scoring registration at every viewport.
Fit the camera to the panel's aspect ratio; overview may trim peripheral scenery while keeping
the tee, pin and playing route in view. Green framing stays inside the registered artwork to avoid
empty sidebars. Never stretch the course or alter yardages to fill a display. Narrow overview
screens retain the whole saved course frame.
Completion must not lock out correcting the last shot: allow reopening a hole or round, including
the previous hole from its untouched next tee. Restore score and position together, including
penalties/gimmes. Preserve raw readings and original outcomes; misreads default out of analysis,
mulligans retain the analysis selection. Review only resumes after an explicit correction, with
active-session ownership enforced. Keep correction buttons touch-sized and available above the map.

Default to an explicit demo experience when physical geometry is unverified. Keep aim, next equipment,
lie, remaining distance and score easy to find. Use feet on the green. Match map surfaces to the scorer;
show endpoint connectors without implying a flight path. Freeze played course/settings and per-shot
aim/randomness; analysis exclusions cannot erase strokes. Missing/stale inputs leave the ball in place
with a clear saved-but-unscored message. End/abandon/exit/review remain distinct.

Show game score as played shots + penalties + conceded putts, with par and total together.
Distinguish actual-shot count from next stroke number; never hide an automatic gimme in the total.
Map aiming should expose ball-to-aim and aim-to-pin distances, with explicit units and no implication
that straight-line distances already account for lie or flight adjustments.

Course artwork is cosmetic and must follow saved scoring geometry. Use masks or geometry-based
compositing to keep visible hazard/lie edges aligned; provide a boundary overlay for inspection and
a simple rendering fallback. Prefer map taps plus Aim at pin over left/right step buttons, retaining
keyboard coordinate entry. Real-course imagery and AI restyling require reviewed geometry, scale
and provenance; do not infer course rules, elevation or putting slopes from decorative pixels.

Prefer one registered aerial artwork layer over obvious repeating tiles. Preserve a simple-fill
fallback and visible scoring-boundary inspection. Import drafts must show missing coverage and
separate mapped route length, straight-line distance and scorecard yardage. Never stretch geometry
to hide a disagreement. Explicit review precedes publication; publication never changes a running
session. Imported geometry, decorative artwork and official golf rules are distinct claims.

For new fictional holes, artwork may come first from a target yardage/layout brief. Treat distances
as design targets until a uniform image-to-yard transform and terrain polygons have been reviewed.
Do not present unregistered concept art as playable geometry. Keep aim/ball/pin and dispersion
overlays separate, and preserve immutable versions once a hole has been played.

On-course dispersion is a historical planning preview. Use paired coordinates, retain lateral bias
and club distance when aim changes, separate real/demo and named wedge intents, and honor effective
tags and analysis exclusions. Show source, sample coverage and whether lie effects are applied.
Never recycle final offline for carry or label smoothed density as future-shot probability. Hide
full-swing planning on the green and in historical review; preserve score and exits.

Use one bright blue for on-course dispersion previews, with a bold, screen-sized outline and dark
contrast backing over detailed terrain. Keep range scatter colors specific to each bag/club.

## Product name

Use **TraceLoft** in visible app copy, window/page titles and launch instructions. The wordmark
uses navy Trace and cobalt Loft within the pure-white Vector design. Historical GolfData
artwork and internal compatibility identifiers may retain the old name.


Course import workbench: distinguish unsaved edits, durable drafts and published fixed versions.
Allow incomplete valid geometry to be drafted, but show explicit publication blockers. Every applied
edit/reopen clears review approval; failed edits retain the last valid geometry. Preserve original
source and coordinate registration, offer keyboard equivalents to map taps and Undo, and never
modify existing rounds when publishing corrections. Structural validation is not geographic
verification. Save/export applies only finished shapes; communicate pending drawing clearly.

## Relay simplicity and separate acquisition (2026-10-03)

TraceLoft listens automatically; users choose Off, GSPro or Infinite Tees once. Save that choice
immediately and restore it on restart. Hide optional port overrides in Connection details. Show
source readiness separately from simulator connectivity. Keep OCR/calibration in the private source
app. Replace in-drill Start/Stop capture with a Relay link. Input disconnected/unready shows an
actionable warning; healthy recording uses only the header. Keep raw diagnostics out of practice.

Course artwork review: generated aerials may drift from their input guides. Trace/reconcile the
finished hazards and putting surfaces, inspect all holes with scoring outlines, and register
tee/pin and scale to the final art. Reject texture fragments that would become invisible hazards.
Keep optional hole strategy in a disclosure and game-physics limits in the existing assumptions.

Audit every finished course hole with registered surface outlines, including green zoom and the
wide/narrow overview. Pair visual review with asset hashes and fixed image-pixel landmarks; neither
geometry validity nor matching aspect ratios prove terrain alignment. Correct released layouts in
new immutable course/hole versions, preserve older packages and frozen rounds, and state when a
new round is needed to use the revised layout. Keep image-analysis dependencies out of the app.

## Ball replay (2026-10-03)

Recording, scores, completion warnings and correction controls update immediately; animation must
never gate them. Use source carry/total anchors where available and label modeled shape, hang time,
landing lateral position and illustrative roll timing. Never imply a reconstructed path is measured
or that animation adds collision/ground physics. Missing model inputs show an endpoint-only replay.
Respect reduced motion, provide touch-sized Replay/Skip, baseline session entry/reload, and interrupt
old playback on a new shot, correction or navigation. Review requires explicit replay. Keep course
world coordinates and final scored position authoritative; hazard replays return to the saved
penalty position, and gimme strokes do not become invented ball movements.

Landing rules belong to Python scoring, with versioned landing/surface/rollout evidence per shot.
Separate starting-lie distance reductions from carry-landing rollout reductions in setup. Sand stops
at carry; rough/OB reduce only remaining rollout. Keep raw carry/total unchanged and disclose
interpolated lateral landing; missing carry skips the rule with feedback. Animate the saved landing
and final points without moving the airborne landing when rollout shortens. Preserve older outcomes.
