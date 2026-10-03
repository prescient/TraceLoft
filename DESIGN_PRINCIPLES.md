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
- Offer fixed and random targets when appropriate. Make the mode and next target explicit;
  retain each shot's actual target so scoring and review remain meaningful.

## 3. No screen should be a dead end

- Main navigation follows **Capture → Practice → Play → Analyze → Sessions**. Play contains the game and Analyze contains comparisons; both retain global navigation and
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

The user requested a futuristic design exploration on 2026-10-02. See
[Orbit, Vector and Aura](designs/future-language/README.md) for layout alternatives. These proposals
establish Vector (white, black and cobalt) as the user's preferred exploration direction. The current
studio remains implemented until replacement components and layouts are verified. The user's
refinement is to retain the current app's functional layout and controls, apply Vector styling,
and use a consistent practical type scale rather than oversized editorial panels. See hybrid
studies in the same concept notes; this supersedes treating Vector's new layouts as the target.
The latest refinement removes the grey page and rounded-card treatment: use pure white surfaces,
square edges, straight thin dividers and no shadows, retaining functional circular club selectors.

The selected direction is the dark studio in
[putting-studio-dark-concept.png](designs/putting-studio-dark-concept.png): navy backgrounds,
raised slate cards, clear light text, mint accents, generous spacing and restrained borders.

- Reuse the colors, typography, spacing and component patterns in [studio.css](web/studio.css).
  Prefer shared tokens and components to a new visual treatment for every drill.
- Use mint for primary actions, targets and success; amber for misses and recoverable warnings;
  red for ended recording, errors and destructive actions. Always include a readable label.
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

- The background Python service owns capture and shared practice state; browsers present and control it.
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
a white outline/size change for focus. Excluded points keep a lighter tint of their club color and a
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
uses light Trace and mint Loft within the existing dark studio design. Historical GolfData
artwork and internal compatibility identifiers may retain the old name.


Course import workbench: distinguish unsaved edits, durable drafts and published fixed versions.
Allow incomplete valid geometry to be drafted, but show explicit publication blockers. Every applied
edit/reopen clears review approval; failed edits retain the last valid geometry. Preserve original
source and coordinate registration, offer keyboard equivalents to map taps and Undo, and never
modify existing rounds when publishing corrections. Structural validation is not geographic
verification. Save/export applies only finished shapes; communicate pending drawing clearly.
