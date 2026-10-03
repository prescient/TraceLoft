# TraceLoft: basic 2D golf

Implemented 2026-10-02. Open **Play → choose a hole → Set up round**. Four original holes are bundled;
no external course assets or FUSE engine are used. Python owns the round and SQLite saves every
accepted attempt and its outcome. This is an experimental endpoint game, not a validated simulator.

| Hole | Par | Playing-route yardage | Straight tee-to-pin |
| --- | --- | --- | --- |
| Meadow One | 4 | 350 yd | 350 yd |
| Willow Cove | 3 | 155 yd | 155 yd |
| Pine Bend | 4 | 365 yd | 352.1 yd |
| Meadow Reach | 5 | 525 yd | 504.8 yd |

Each is a separate single-hole round; there is no automatic multi-hole scorecard yet. The new holes
use uniformly registered original artwork and hand-traced game surfaces. Their listed yardage follows
the saved playing route; live aim/pin measurements remain straight-line distances. All support the
same bag/club selector, historical heatmap, lie penalties, putting, demo generator and saved reviews.
Course packages and image versions are fixed; existing rounds are never upgraded in place.

## Play

- Choose Demo (default) or experimental live capture, a bag/club, lie settings, Stimp and gimme radius.
  Demo provides explicit distance/offline inputs and a Simulate shot/putt button. Synthetic receipts
  never enter live sessions or GSPro delivery. Live mode requires acknowledgement of the unverified
  Foresight geometry, and capture must be running separately.
- Tap the map to aim, use Aim at pin, or enter course coordinates. Whole-hole
  and green views share the same coordinates. Positive course lateral is right when facing down
  the hole; the overview displays forward to the right and lateral down the screen. The live map
  shows **Ball → aim** and **Aim → pin** distances, in yards or feet when putting. These measure
  straight-line geometry before lie adjustments and update after map, button or coordinate aiming.
- Select bag/club before hitting. Earlier tags stay intact. The next aim resets to the pin after a
  move; a penalty replay retains the prior aim. One round/drill owns capture at a time.
- On the green, distance switches to feet and the app shows needed pace from the existing
  constant-Stimp putting model. Change to your putter manually; lie selects the putting calculation.
- End round saves a partial round; Exit round confirms ending and returns to Play. Abandon also
  keeps the shots. A red completion banner stops further recording into that round. Saved review
  exits to Sessions; Practice selector and Play menu remain available. Delete/Undo is recoverable.

The score panel above the map shows par, total strokes, played shots, penalties and gimme putts.
For example, three played shots + one OB penalty + one automatic gimme = five strokes. A gimme
represents the final unplayed putt; an actual simulated hole-out adds no extra stroke. Unscored
attempts are omitted from played-shot count; excluded played shots still count. Live play also
shows the next stroke number; ended partial rounds are labeled separately from hole completion.

**Map display** offers detailed AI terrain and a scoring-boundary overlay. Surface shapes, yardages
and scoring remain unchanged; the textures are cosmetic. See [art and import plans](COURSE_ART_AND_IMPORTS.md).

## Explicit rules and estimates

| Rule | Implementation |
| --- | --- |
| Full swing | Reported total + signed offline; no modeled-flight fallback or HLA substitution |
| Geometry | Setup selects downrange total, or radial total with forward = sqrt(total² − offline²) |
| Rough / sand | Adjustable reductions, initially 7% / 20%, applied to both endpoint components |
| Nature | Dark outer bands beyond ±60 yd lateral; 30% reduction on the following shot |
| Extra variation | Uniform ±degrees, only from rough/sand/nature; default zero; saved seed and draw |
| Surfaces | Endpoint only; tee/fairway/rough/green/sand/water/nature/OB match the drawn geometry |
| Water / OB | +1 stroke penalty plus the played stroke; replay from previous position |
| Putting | Flat-green travel from speed/Stimp, rotated by measured start line and selected aim |
| Hole / gimme | Endpoint within 0.2 ft finishes; otherwise inside configured green gimme radius adds one putt |
| Overshoot | Endpoint stays beyond the hole; no path-crossing or cup-speed capture model |

Course geometry and settings are copied into each round. Each attempt stores the original readings,
frozen capture context, before/after state, endpoint/destination lie, random draw, distance reduction,
penalty/concession strokes and model version. Replay/review uses saved outcomes, not recalculation.
Missing total/offline (or putting speed/direction), impossible radial geometry and stale/missing turn
context save an unscored attempt and leave the ball in place with an explicit message. Duplicate
keys/receipts do not advance again. Aim changes after acceptance do not replace the receipt's aim.

Excluding a shot affects analysis only; it never refunds the stroke or changes a played position.
Analyze's **Simulator rounds** filter compares the original source readings. Rich round miss maps,
automatic outliers, mulligans and strokes-gained benchmarks remain future work.

## Bag suggestions

Suggestions use included Bag mapping/Wedge matrix attempts for the selected bag and matching
real/demo mode, separating swing labels. At least five available reported total readings per group
are required. The three nearest medians to pin distance adjusted for starting-lie reduction are shown
with IQR/count. Missing profiles produce an actionable empty state. No automatic club selection,
hazard strategy, weather normalization or predicted probability is implied.

## Verification and limits

Isolated API/model tests cover complete hole/gimme scoring, missing/stale/duplicate records, live/demo
separation, frozen aim, rotation/radial geometry, water/OB, lie reductions, deterministic outcomes,
recommendation exclusions, persistence and recoverable deletion. Browser checks cover setup, map and
button aiming, club changes, approach-to-putting, completion, review/exclusion, exits, abandon, restore,
and responsive 1366/1376 iPad landscape and 390 phone widths. Actual iPad Safari/touch, physical live
full-swing geometry and green calibration remain unverified. Do not use scores as a real-course handicap
or infer validated ball flight. Multiple holes/course imports and more sophisticated physics are deferred.

## Club dispersion overlay

Select a bag and club in an active round. **Density** is initially on in the Club dispersion card
beside the map (below it on phones); **Outline** and **Off** simplify/hide the overlay.
All course previews use bright blue with a bold solid outline for visibility over the terrain. Aim on the
map or with Aim at pin/coordinates. The club's distance remains unchanged by the aim point's distance.

Choose the mapping/swing profile for wedges; Bag mapping and each Wedge matrix swing stay separate.
The initial source is reported/synthetic Total + offline with the round's selected geometry. To see
**Carry**, choose **OpenGolfCoach estimate** first: its carry and total have separate saved lateral
endpoints. Missing paired fields are counted, never replaced with launch direction or zero.

The card shows median down-aim distance, middle 50%, plotted/excluded/removed/missing counts and date
range. The info button explains smoothing, the descriptive 80% outline and median diamond. Below
five points shows dots only; under twenty shows a small-sample warning. Density is historical
smoothing, not the probability of a future shot or a hazard. Real/demo profiles never blend.

These are current included mapping session attempts using corrected equipment tags. Exclusion,
removal and retagging refresh the preview across clients. Reused physical shots count once per
mapping session, matching Analyze. Preview does not alter measurements, saved outcomes, selected
aim or the game's scoring rules. It is explicitly unadjusted for lie penalties/extra variation.
On the green and in ended/review rounds, the full-swing planning overlay is hidden. Display/swing
preferences are local to this browser and reset on reload; bag/club tags remain shared service state.
