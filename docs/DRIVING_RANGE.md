# Driving range

Implemented 2026-10-01. Open **Practice → Driving range → Set up drill**. Choose a bag and club,
player handedness, and optional carry target. Target 0 means free practice. Launch range, then
start capture before hitting shots. The session is open-ended: End session saves results; Exit
asks to end/save first; Abandon saves the recorded shots under an Abandoned label.

## Try it without hitting balls

Choose **Launch demo range** in setup. Use **Add simulated shot** or **Generate sample set (10)**.
Change clubs to generate different launch profiles. Every ninth generated shot is a deliberate
mishit; samples also exercise left/right curvature. These are test inputs, not a prediction of your
personal distances. Demo sessions are labeled SIMULATED DATA and reject live capture events.
Normal range sessions reject simulated events. The generator never sends shots to GSPro.

Sessions offers All sessions / Real sessions / Demo sessions only. End or abandon a demo, then
Delete it to move it to Recently deleted. Undo/Restore recovers the exact data. Permanent purge is
not implemented; raw evidence remains in SQLite. Shot and session exports identify simulated data.

## At-a-glance feedback

- Large tiles show reported carry, total, signed offline, ball speed, total spin (rpm), vertical
  launch angle and descent angle (degrees). Inspecting an older shot updates all seven readings;
  Back to latest resumes following new shots. Missing values stay unavailable, including descent
  when only a modeled value exists. A distance-window result compares carry with the saved target.
- The primary layout is 13-inch / 12.9-inch iPad Pro landscape: all seven readings share one row
  at widths of at least 1200 CSS px. Smaller tablets use four columns, phones two. Charts remain
  below the bar; wide workspace tables scroll inside their containers. Browser viewport QA does
  not establish Safari behavior, physical touch usability or connectivity from an actual iPad.
- The bag column and direct club buttons tag upcoming shots only. More bags, Manage bags and Clear
  club use the shared catalog. Corrections to earlier shots belong in the workspace below.
- Carry/Total selects the scatter endpoint. **OpenGolfCoach · estimated positions** uses independent
  model coordinates (+forward, +right), with distinct landing and rollout endpoints. **Foresight ·
  reported distance / offline** compares reported values; offline's endpoint definition is still
  unverified, so this is not labeled a verified landing map.
- The target rectangle is the current session target. Change target affects future shots only.
  Width is a visual guide; success uses reported carry inside half the full depth on either side.
  Earlier targets remain in shot details/exports, even when the current rectangle changes.
- Dots use distinct bag/club colors within a session, assigned from original recorded club order.
  The legend shows only bag/club names and color swatches; untagged shots are gray. Filtering and Carry/Total
  changes retain colors. Corrected tags determine current membership; a white outline marks the
  selected shot without changing its club color. Excluded points use the same club color mixed with
  white plus a dashed edge; removed points fade in all-recorded/removed views. In the default Included
  view, the chart retains excluded points for context while the workspace table stays included-only.
  Removed points stay hidden by default. Other state filters apply to both chart and table.
- Each tagged bag/club gets an **80% dispersion circle** after five included, plottable shots.
  Center = coordinate-wise medians; radius = the nearest-rank 80th percentile of Euclidean distances
  from that center (sorted radius at ceil(0.8n)). This encloses at least 80% of the current included
  positions; ties may enclose more. It is descriptive coverage, not a confidence interval or future
  landing probability. No automatic exclusions are applied. Identical positions have a zero radius
  with a center marker; smaller samples have no circle. Untagged shots have no circle.
  Independent chart axis scales make yard-space circles appear oval on screen; these are not
  covariance ellipses. The **i** button beside **Shot dispersion** explains circle coverage, minimum
  samples, colors, exclusions and the selected source. Hover or keyboard focus previews the help;
  click/tap keeps it open. Click/tap again, click outside, leave keyboard focus or press Escape to
  dismiss. The explanation is hidden by default. Circle radius/count remain in accessible SVG labels.
- On wide layouts, the dispersion plot expands into the height available beside Flight profile and
  Flight shapes. Legend and statistics remain below it. Plot coordinates adapt to the available
  aspect ratio without stretching text or markers; source data, axis bounds and circle radii do not
  change. Stacked tablet/phone layouts retain compact chart proportions.
- Circles follow selected Carry/Total and plot source, plus bag/club/shape/text/state filters.
  Missing coordinates, excluded shots and removed shots never enter the radius or center.
  Corrected tags determine bag/club membership, with colors shared by dots, circles and legend.
  Circles and their full extents enter axis sizing, so overlays are not clipped at plot boundaries.
- Click a point or an Inspect shot button to link its tiles and side flight. Points support Enter
  and Space. Back to latest resumes following incoming shots. Overlapping points are individually
  accessible through the table and keyboard.
- Flight profile offers **Side view / Top view** for the inspected shot. Top view uses saved
  forward/right trajectory positions: target line upward, right positive, white launch point and
  mint landing point. Its axes scale independently to expose curvature; it ends at carry and is
  not a scale-accurate course map or a rollout animation. The view follows shot inspection and
  Back to latest in both live and saved reviews.
- Flight profile, carry/total/apex/descent/hang time and handed shot-shape labels are estimates.
  Shape frequencies respect the current included cohort. The scatter summary retains included mean
  and population SD from reported distances; All matching mean includes excluded/removed matches too.

## Club snapshot

Above Shot workspace, each bag/club row shows **median and IQR** for carry, total, absolute offline,
vertical launch angle and descent angle. Values come from reported readings (synthetic readings in
Demo ranges), independently of the scatter source. Modeled descent never fills a missing reading.
Absolute offline takes the magnitude of each signed reading before calculating statistics.

The snapshot includes only included shots matching the workspace filters below, using corrected
bag/club tags when present. Each metric shows its own available-reading count, n; missing readings
are omitted, while zero remains valid. With one reading, the median is shown and IQR is unavailable.

IQR is the width Q3 minus Q1, not a symmetric plus/minus interval. Quartiles use linear interpolation
at (n-1)p (type 7 / inclusive convention). Small samples remain descriptive. Exclude, remove, retag
and Undo immediately recompute the snapshot in both live sessions and saved reviews. Older Demo
shots using the legacy descent field remain readable; new demo shots use descent_ang.

## Filter, clean up and export

Filter by bag, club (including Untagged), shape, state or text; sort by time or selected distance.
Select individual rows or all matching rows. Changing filters clears the selection. The confirmation
names the exact selected count, current assignment and inclusion effect; later arrivals are excluded
from that selection. Each operation needs a reason and records its before/after values.

- **Retag clubs** records a bag/club correction without overwriting the original capture assignment.
- **Exclude / Include** changes session analysis membership while preserving the shot.
- **Remove / Restore** hides/reinstates shots in the normal workspace. Restoring retains any prior
  exclusion. Use the Removed filter to recover shots; All recorded includes every attempt.
- **Undo last cleanup** reverses the latest remaining batch. Revision guards reject conflicting
  edits from another screen. Cleanup works in live ranges and saved range reviews.
- **Export filtered CSV** exports exactly the matching rows in the displayed order, including flags,
  original/effective club tags, target, source launch values and separately named model values.
  Capture → Data & backups still exports the full database, including raw evidence and payloads.

A real mishit is useful data. Excluding it changes the chosen summary, not the historical shot.
Automatic outlier detection, cross-session analysis sets and trend comparisons are future work.

## Model and storage

[OpenGolfCoach](https://github.com/OpenLaunchLabs/open-golf-coach) 0.3.0 is pinned in the web
requirements. GolfData adapter v1 accepts only ball speed, launch angles, total spin and spin axis;
reported carry/total never enter the prediction. Inputs, model ID, assumptions, trajectory and
results are frozen in each attempt. Missing spin or a library failure leaves the original shot
saved with a visible unavailable reason. Model estimates are not source measurements.

Assumptions: flat ground, no wind, 25°C, 101325 Pa, 50% humidity, sea level and typical fairway
rollout. Carry uses native landing coordinates; total reconstructs the native total-radius endpoint
along the horizontal landing-velocity heading. Trajectory ends at landing. Source and estimate
outputs can disagree; no physical accuracy or Foresight agreement has been established.
[License and provenance](../third_party/opengolfcoach/NOTICE.txt) are also linked inside the app.

SQLite schema remains version 1. Existing session/attempt payloads hold range/model context,
correction overlays and cleanup history; transactional audit events preserve changes. Original
capture tags and values remain intact. Demo observations use `synthetic_demo` provenance/method.
The standard local snapshot includes all these fields; no Google Drive sync is implemented.

## Verified and pending

The implementation checklist and actual test/browser evidence are in
[RANGE_IMPLEMENTATION.md](RANGE_IMPLEMENTATION.md). Physical full-swing OCR, Foresight offline
semantics, model accuracy and phone network access still need hardware/user-shot validation.

Additional metric recommendations are recorded in [OpenGolfCoach metrics](OPEN_GOLF_COACH_METRICS.md).
