# Club dispersion preview — concept, 2026-10-02

Status: implemented 2026-10-02 after user approval. The image below remains a concept; see
[golf-club-heatmap-ipad.png](golf-club-heatmap-ipad.png) for the actual isolated UI.
User requested a bag/club mapping overlay showing where a shot might finish along the selected aim.
The [current image](golf-sim-club-preview-concept-v2.png) uses illustrative values and course shapes; it is not
a screenshot, a measured player profile or a change to Meadow One geometry.

## Implemented interaction

- User refinement: tap/click the map to aim; keep **Aim at pin** as the only visible aiming button.
  Remove the left/right step buttons from the proposed design. Preserve an accessible keyboard
  alternative through coordinate entry or keyboard map aiming when implemented.

- Selecting a bag/club loads its mapped shot endpoints; changing aim rotates/translates them from
  the current ball position. Preview distance follows the club, not the clicked point's distance.
  A short club should remain short even when aiming farther away. Preserve lateral bias.
- Carry / Total changes the endpoint type, with Total as the initial game-relevant view. Density,
  Outline and Off give a choice between a heatmap, a simpler dispersion boundary and a clean map.
- Show the selected profile's median, middle 50% (Q1–Q3), available sample count, dates and source.
  Use one bright blue for every course preview; intensity conveys historical density, not hazard severity.
- Retain course/ball/aim/pin visibility through translucent shading. Distinguish the aim cross from
  the median finish. Info help explains density on hover, focus and tap, as in the range charts.
- Excluded/removed shots never enter the preview. Counts should explicitly say included versus
  excluded (the generated image's shorthand “mapped shots” is illustrative copy to refine).
- Changes to club or preview controls affect upcoming planning only, never saved outcomes or aim
  automatically. Keep par, played strokes, penalties and gimmes visible with the course.

## Data and modeling requirements

Reuse the selected bag/club's mapping collections, with real/demo separation and named swing intent
kept separate. A wedge's half/full swings must not be silently blended. Preserve effective cleanup
tags and inclusion state. Preview uses paired endpoints; independent distance and offline summaries
cannot recover joint dispersion or correlation.

Require compatible endpoint geometry and lateral provenance. Current reported offline must not be
silently reused as carry offline: confirm the provider definition or disable that carry overlay.
Do not infer missing lateral coordinates from launch direction. Show available counts per view and
an explicit insufficient-data state. Implemented display thresholds: dots below five; outline and density from five, with a small-sample
warning below twenty. This refines the proposed twenty-point density gate so an initial mapping
collection can be inspected; smoothing is descriptive, never a confidence claim.

Use an empirical density estimate in yard coordinates, preserving asymmetric misses. Show a boundary
with explicitly stated historical coverage if using an outline; reuse the range's descriptive
80% envelope where appropriate. Do not treat IQR as standard deviation or assume a normal distribution.
Do not claim future-shot or hazard probabilities from the smoothed heatmap.

Label whether the display is the original mapped spread or adjusted by the current game's lie rules.
If adjusted, transform each endpoint using the same versioned game geometry/reduction rules and
explain any modeled angular variation; never alter measured samples. Flat-green putting needs its
own profile and should not inherit the full-swing cloud. Empty profiles should link to Bag mapping.

## Acceptance work

Verify bag/club/swing switching, aim rotation and persistent short/long distance, Carry/Total with
missing data, exclusion/retag refresh, sparse/zero-spread and strongly skewed samples, lie adjustment
labels, real/demo isolation and ended-review identity. Review readability and controls at 1366×1024,
1376×1032, 1366×900 and phone widths, plus actual iPad touch when available. No new route is proposed.

## Implementation details

- Read-only Python profile endpoint uses saved Bag mapping and Wedge matrix attempts; effective tags,
  inclusion flags, collection kind and exact swing label determine membership. Counts use session
  attempts, matching Analyze; a physical shot reused in two mapping sessions can appear twice.
- Reported/synthetic Total uses the round's explicit downrange/radial geometry. Carry is disabled
  for that source because reported offline has no confirmed carry provenance. OpenGolfCoach 0.3.0
  uses its saved paired carry/total endpoints only; incompatible/missing predictions are omitted.
- Compact product-kernel smoothing operates in yard coordinates with separate robust bandwidths.
  It retains asymmetric/separated clusters and all compatible included misses. Outline uses
  coordinate medians and the nearest-rank 80% radius. Diamond marks the median endpoint.
- User refinement: every on-course heatmap uses bright blue (#35c7ff). A solid 3px outline with
  a dark 5px backing stays visible over grass, sand and water; non-scaling strokes preserve its
  weight across map sizes. Stronger density shading and blue sample dots improve visibility.
  Range scatter retains its separate bag/club colors.
- Spread is unadjusted: no lie reduction, wind or extra angular randomness. Preview controls are
  browser-local, retain display choices across club changes and remember a profile per bag/club
  for the round. Reload resets these display preferences. Swing choice does not retag game shots.
- Full-swing preview hides on the green and in ended/saved review. Empty profiles link to existing
  mapping setup with the active-session guard. Endpoints outside the view are counted explicitly.
- Verified isolated browser switching, cleanup refresh (12 → 11), keyboard aim rotation, source and
  wedge separation, plus iPad landscape and phone widths. Actual iPad Safari/touch remains unverified.
