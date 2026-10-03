# Additional range metrics: recommendation

Reviewed 2026-10-02 against GolfData's expanded Foresight mapping, installed OpenGolfCoach 0.3.0
outputs and upstream API/source. This is a recommendation; these additional metric tiles are not implemented. A Side/Top flight
profile switch was implemented from already-saved trajectories in this update.

## Inputs and existing output

Our capture supports ball speed, vertical/horizontal launch, total spin, spin axis, backspin and
sidespin. Optional Foresight flight fields are carry, total, offline, descent angle, peak height,
curve and hang time. Availability still depends on the displayed row and confident OCR.
GolfData currently feeds speed, angles and total spin/axis to OpenGolfCoach; it already stores/displays
modeled carry, total, apex, descent, hang time, shape and trajectory/endpoint coordinates.

## Suggested priority

| Priority | Addition | Provenance and practical use |
| --- | --- | --- |
| 1 | Landing speed · mph | Magnitude of OGC landing_velocity; adds arrival speed alongside descent angle. An estimate, not proof a green will hold. Native velocity is currently used transiently but not retained in the saved adapter output; a versioned adapter change should save it for new shots. |
| 1 | Carry-side / total-side · yd | Numeric tiles from already-saved model endpoints, with L/R labels. Makes landing vs rollout lateral position explicit; Foresight offline's endpoint must still be verified. |
| 1 | Runout · yd | Show reported total-minus-carry separately from modeled total-minus-carry. This scalar difference is not the curved ground-path length; use endpoint-vector separation for modeled ground displacement if desired. Rollout depends on the model's typical-fairway assumptions. |
| 2 | Reported vs modeled comparison | Carry, total, apex, descent and hang time side by side, with model-minus-reported differences. Only compare matching units/definitions; this evaluates agreement, not physical truth. |
| 2 | Time / downrange position at apex | Derive from saved 10 Hz trajectories and label approximate. Useful for distinguishing flight windows without adding a new input. |
| 2 | Start direction versus curvature | Surface captured launch direction, spin axis and Foresight curve first. A modeled curve metric needs an explicit launch-line/target-line definition before comparing sources. |

The installed package also returns optimal_maximum_distance_meters and distance_efficiency_percent.
Upstream estimates a maximum from club speed times 4.91 (m per m/s), then divides carry by it. In our
input mode club speed is itself inferred. This is a rough heuristic, not optimized potential carry
or a valid wedge/iron quality score; defer it from normal practice feedback.

Do not add club speed, smash factor, face-to-target, face-to-path or club path as measured metrics.
The upstream source uses assumed impact bands, head mass/restitution and simplified face/path
relationships. Our captured data has no measured club speed or club delivery to validate these.
Their numerical availability does not make them reliable swing diagnostics. Shot rank/color is a
gamified classifier; the range now reserves dot color for club identity rather than a shot grade.

Adding model fields should version the adapter and preserve prior saved predictions. Do not silently
recompute old shots. Historical values missing from stored predictions stay unavailable unless a
separate, explicitly versioned reanalysis is requested. No backend/model changes were made here.

## Sources and local verification

- [OpenGolfCoach API](https://github.com/OpenLaunchLabs/open-golf-coach/blob/main/API.md)
- [Club estimation assumptions](https://github.com/OpenLaunchLabs/open-golf-coach/blob/main/core/src/clubhead_data.rs)
- [Distance-efficiency implementation](https://github.com/OpenLaunchLabs/open-golf-coach/blob/main/core/src/lib.rs)
- [GolfData's Foresight mapping](../data/metric_mapping.v2.json)
- [Current adapter](../flight_model.py)

A direct local call confirmed 0.3.0 exposes landing_velocity, the current flight metrics, trajectory
position/velocity samples, club estimates and efficiency fields. Repository main is a documentation
reference, not an assertion that its commit is the installed wheel's source revision.
