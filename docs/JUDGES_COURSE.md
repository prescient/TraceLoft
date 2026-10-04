# Judges Course

An 18-hole wooded parkland course adapted from the user's illustrated maps and four lakeside/
woodland photographs. Supplied scorecard: **6,163 yd / par 72**.
Play → Judges Course → Set up round. Full 18, Front 9 (3,066 yd/par 36) and Back 9
(3,097 yd/par 36) preserve original hole numbering.

| Hole | Par | Yards | Hole | Par | Yards |
| --- | --- | --- | --- | --- | --- |
| 1 | 4 | 353 | 10 | 4 | 362 |
| 2 | 5 | 460 | 11 | 5 | 552 |
| 3 | 3 | 157 | 12 | 4 | 322 |
| 4 | 4 | 365 | 13 | 4 | 335 |
| 5 | 4 | 372 | 14 | 3 | 137 |
| 6 | 5 | 496 | 15 | 4 | 424 |
| 7 | 4 | 380 | 16 | 3 | 145 |
| 8 | 3 | 153 | 17 | 5 | 442 |
| 9 | 4 | 330 | 18 | 4 | 378 |

The maps guide routing and hazards; photos guide wooded parkland textures, natural lakes, pale
sand and stone banks. Built-in imagegen generated a separate overhead aerial per hole. It
reinterpreted some shapes, so this is an adaptation, not surveyed geometry. Middle pictured
tee pads are provisional; **Provided yardages** avoids an unsupported tee-color identification.
Uniform route scale matches your yardages while retaining native image proportions.
Widths and straight-line distances are approximate; elevation is not modeled, greens are flat,
stone banks are decorative, and trees use simplified nature regions.

Finished art was traced with reviewed turf controls and seeded contours. The 55 sand regions
include grass cutouts on 2 and 5. Fairways on 12 and 15 have separate patches; lakes appear on
7, 8, 9, 15, 16 and 17. Map options exposes scoring outlines and the simple-fill fallback.
Existing bag/club tags, dispersion, putting, replay, scorecard, Mulligan/Misread and saved review
apply. Historical dispersion requires included matching samples; artwork creates no shot history.

## Reproduction

Design-only OpenCV, NumPy and Pillow stay outside the app environment.
Run `python courses/build_judges_course.py`, then `python courses/render_registration_review.py`.
The builder refuses changed released versions; `--candidate <path>` is for pre-release review.
After play, publish corrections under a new immutable ID. Existing rounds freeze their geometry.

Assets: `web/art/judges-course-v1-hole-01.png` through `-18.png`.
Package: `courses/judges-course-v1.json`; controls: `courses/judges-art-controls.json`.
[Design record, prompts and source hashes](../designs/judges-course/README.md).
