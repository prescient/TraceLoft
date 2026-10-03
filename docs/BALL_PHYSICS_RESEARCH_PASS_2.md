# Ball physics research: data and benchmark preparation

Research pass 2, 2026-10-03. Follows the [approved plan](BALL_PHYSICS_RESEARCH_PLAN.md) and
[initial literature log](BALL_PHYSICS_RESEARCH.md). This pass retrieves concrete model parameters,
audits bounce data, inspects another engine's source/tests and prepares the next experiments.
The numerical work below is a data inventory and equation sanity check, not a fitted or validated engine.

## What is ready

| Workstream | Evidence obtained | Readiness |
| --- | --- | --- |
| Flight | Ferguson's published coefficient formulas, fitting conditions and validation errors | Candidate baseline identified; independent flight data and domain policy still needed. |
| Bounce | Both numeric campaigns downloaded; 1,023 rows parsed and checked | Ready for exploratory fitting; launcher-setting groups must be recovered before a grouped benchmark. |
| Putting and cups | Penner's rolling/capture formulas; Holmes' original experimental context | Ready to specify flat/slope/capture cases; launch skid and modern cup validation remain open. |
| Bunkers | Full particle-model paper, its experiment and limits | Mechanisms identified; no defensible universal launch penalty yet. |
| Second engine | Pinned OpenFairway flight/bounce source and selected tests | Useful reference for architecture and pitfalls; no runtime benchmark performed. |

## Flight: accessible coefficients and their domain

**Source:** Spencer Ferguson, *A Two-Armed Forward Dynamic Model of a Golf Drive: A Simulation and
Optimization Tool for Golf Equipment and Biomechanics*, MASc thesis, University of Waterloo (2023).
[University PDF](https://dspacemainprd01.lib.uwaterloo.ca/server/api/core/bitstreams/a9cd0c81-1120-4f22-8066-c78bd9420237/content).
**Access:** title/contributions, sections 3.4 and 4.4 inspected. Chapter 3 incorporates the physics
work from [Ferguson, McNally and McPhee 2022](https://doi.org/10.5703/1288284317493), whose conference
download remains blocked; the thesis does not reproduce its neural-network work.

**Evidence:** 1,040 shots using 2021 Pro V1 balls, GCQuad launch inputs and FlightScope X3 flight
outputs; wind below 1.3 m/s. About half were drivers. Observed spin ratio spans 0.02–0.75;
80% was used for fitting and 20% for validation. Reported mean absolute errors: carry 2.74 yd,
offline 1.68 yd, apex 1.28 yd. These are author-reported results, not our reproduction.

Equation 3.15 gives dimensionless coefficients, with `S = |omega| × radius / speed`:

```text
CD = 0.1304 + 0.9287 S - 0.8259 S²
CL = 0.0504 + 1.2031 S - 1.1490 S²
CM = 0.01 S
```

The moment uses the diameter convention: magnitude `2 × Q × CM × radius`,
where `Q = 0.5 × density × area × speed²`; angular speed is rad/s.
**Applicability:** useful baseline candidate; one ball generation and limited conditions.

**Our checks and proposed handling:**

- At S=0.02, the equations give CD=0.14864364, CL=0.0740024; at S=0.75 they give
  CD=0.36235625, CL=0.3064125. These are arithmetic checks of the transcription.
- Extrapolating to S=1.5 gives negative CD and CL. That makes unconstrained extrapolation
  unsuitable. The observed launch range is also not proof of coverage at every point during flight.
- CL's nonzero intercept does not define a force direction at exactly zero spin. A candidate solver
  needs an explicit zero-spin/zero-relative-speed branch and documented behavior outside coverage.
- Reproduce the source equations first. Treat later bounds, low-speed blending and ball-profile
  changes as new model assumptions, with their own versions and tests.
- Evaluate wind using air-relative velocity; keep ground-relative velocity for position updates.
  Verify axis conventions before comparing curved shots. These are implementation requirements,
  not evidence that wind performance has been validated by this dataset.
- Seek the underlying shot data or independent observations. An average carry error alone does not
  set acceptable error for wedges, low shots or unusual spin. Coefficients without data are not a benchmark.

## Bounce: downloaded data and reproducible audit

**Source:** Biber, Jones, Champneys, Green and Szalai (2023),
[article](https://link.springer.com/article/10.1007/s12283-023-00442-4) and
[Online Resource 2](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs12283-023-00442-4/MediaObjects/12283_2023_442_MOESM2_ESM.zip).
**Access:** ZIP README and both CSV files inspected; parsing and descriptive counts executed.
Campaign A is artificial teeing turf; B is natural teeing turf.

The archive has six unheaded columns: inbound horizontal velocity, vertical velocity and spin,
followed by the same outbound quantities. Linear velocities are **ball radii per second**, not m/s;
spin is rad/s, anticlockwise positive. Multiply linear values by the experiment's ball radius in metres
for SI conversion. No radius value, launcher group IDs, timestamps or uncertainty columns are supplied
in these CSVs. Preserve the native units until the radius and mapping are documented.

Our audit results:

| Check | Campaign A | Campaign B |
| --- | ---: | ---: |
| Parsed rows, each six finite values | 330 | 693 |
| Exact duplicate rows | 0 | 0 |
| Inbound vertical velocity nonnegative | 0 | 0 |
| Outbound vertical velocity nonpositive | 0 | 0 |
| Horizontal velocity changes sign | 62 | 26 |
| Contact-slip expression changes sign | 215 | 539 |

The last row checks `(vx_in + omega_in) × (vx_out + omega_out) < 0` in the source's scaled units.
It detects a sign crossing, not a measured contact-time history. Values near zero require the
original uncertainty estimates before making strong classification claims. The counts above are
our calculations, not a reproduction of the authors' trained classifier or fitted models.

The source files are downloaded to a temporary research directory. The repository retains only
the [audit program](../research/ball_physics/audit_bounce_data.py) and
[computed JSON inventory](../research/ball_physics/bounce_audit.json), including ranges and hashes.
Run from the repository root after downloading the linked ZIP:

```powershell
python research/ball_physics/audit_bounce_data.py C:/path/to/12283_2023_442_MOESM2_ESM.zip
```

The script verifies the inspected ZIP's SHA-256, reads it without extracting files, checks dimensions
and finite values, and produces deterministic JSON. A changed archive requires a provenance review.
The article uses CC BY 4.0; the ZIP README contains no separate license declaration. Before bundling
raw data, confirm the supplement's coverage and retain attribution. No paper or raw CSV is redistributed here.

**Benchmark limitation:** the paper's split holds out one repeat per launcher setting. That evaluates
prediction for familiar settings. Our proposed harder split holds out whole settings, so its errors
must not be compared as though both protocols were identical. Do not infer group labels from row
blocks: campaign B has mixed repeat counts. Recover the mapping from the authors' supporting material
or document an explicitly exploratory alternative before fitting.

**Equation check:** [Online Resource 3](https://media.springernature.com/original/springer-static/esm/art%3A10.1007%2Fs12283-023-00442-4/MediaObjects/12283_2023_442_MOESM3_ESM.pdf)
defines rigid/Coulomb and inclined-surface baselines. Visual inspection confirms that typeset S3.1
inverts the restitution ratio relative to S3.2 (`vy_out = -r × vy_in`). This is our identified internal
inconsistency, not a publisher-issued correction. For that update rule, the consistent ratio is
`r = |vy_out / vy_in|`. Resolve this explicitly when reproducing the baseline; no fitted constants
were adopted.

## Bunkers: launch mechanism and missing coverage

**Source:** T. Koizumi, N. Tsujiuchi, H. Horii, M. Miki and J. Hidaka,
*Computer aided sand wedge shape assessment by using particle simulation*, WIT Transactions on
Modelling and Simulation 41, 281–288 (2005), DOI 10.2495/CMEM050271.
[Publisher PDF](https://www.witpress.com/Secure/elibrary/papers/CMEM05/CMEM05027FU.pdf).
**Access:** model, experimental procedure, discussion and conclusions inspected; graph values not digitized.

**Evidence:** a 2D particle-element model uses approximately 100,000 sand particles and a disk-shaped
ball. Two experimental entry depths, 15 and 27 mm under the ball, check the modeled launch response.
Shallower contact produces higher speed/lower launch; deeper contact gives lower speed/higher launch.
The model underrepresents the observed difference; the authors identify its 2D approximation as a cause.
Three wedge shapes are compared. This is equipment-design research, not broad bunker-condition calibration.

**Applicability:** medium for identifying launch dependencies, low for transferable numerical penalties.
**Proposal:** research a reduced launch-response model conditioned on lie depth, sand condition and
available delivery data. A clean mat shot generally lacks sand entry point/depth, so those inputs must
be explicit assumptions or remain unknown. Keep bunker landing/plugging separate from playing out of sand.
**Next:** seek moist/compacted sand, buried lies and landing experiments; do not adopt a fixed distance
percentage or real-time particle simulation from this evidence alone.

## Putting: rolling assumptions and cup capture

**Source:** A. R. Penner, *The physics of putting*, Canadian Journal of Physics 80(2), 83–96 (2002),
[DOI 10.1139/p01-137](https://doi.org/10.1139/p01-137).
[Accessible paper copy](https://www.waddengolfacademy.com/putting/Penner_The%20Physics%20of%20Putting.pdf).
**Access:** sections 2–3 and initial level-green results inspected. This copy has provisional pagination;
the original author's host still fails access.

**Evidence:** assumes immediate pure rolling and constant resistance, treating the ball as a uniform
sphere. It models slopes and fits Holmes' flat-hole capture boundary using
`v_critical(delta) = 1.63 × [1 - (delta / hole_radius)²] m/s`, where delta is the lateral impact offset.
The fit is an approximation, with additional small-slope corrections; it does not simulate all rim
collisions. Penner uses nominal Stimpmeter exit speed 1.83 m/s.
**Applicability:** useful rolling/capture baseline, limited for launch skid, irregular turf and lip-out dynamics.
**Next:** retain the existing flat-green baseline as an explicit approximation; evaluate launch/skid
separately and compare capture classification across speed and offset before animating a detailed lip-out.

**Source:** Brian W. Holmes, *Putting: How a golf ball and hole interact*, American Journal of Physics
59(2), 129–136 (1991), [DOI 10.1119/1.16592](https://doi.org/10.1119/1.16592).
[Scanned original article](https://waddengolfacademy.com/putting/BW%20Holmes%20Putting_How%20a%20golf%20ball%20and%20hole%20interact.pdf).
**Access:** original pages 129, 135–136 visually inspected, including experimental setup and plots;
the complete derivation remains unread.

**Evidence:** a computer model relates capture to arrival speed and offset. Tests used a plywood
hole faced with corklike material, an inclined launch ramp and photogates. Some balls were captured
above the modeled boundary; the discussion attributes discrepancies to rim bounce/skid and possible
slowing between gates and the hole. The abstract's 1.626 m/s limit assumes no skid/bounce at opposite-rim
contact. **Applicability:** high for designing tests, limited as a universal modern-green threshold.
**Next:** specify ball/rim geometry and restitution, then validate speed/offset outcomes on representative
cups. A gimme radius is a scoring rule and cannot validate physical capture.

**Measurement context:** the [USGA's 2013 Stimpmeter description](https://www.usga.org/content/usga/home-page/articles/2013/01/usga-introduces-updated-stimpmeter-21474853935.html)
explains averaged roll distance and the newer half-distance notch, whose reading is doubled.
Its [2024 measurement guidance](https://www.usga.org/content/usga/home-page/course-care/green-section-record/62/issue-12/details-matter-when-measuring-green-speed.html)
identifies technique, timing and surface moisture as measurement influences. The latter was available
as indexed official text; direct retrieval and the instruction-booklet PDF returned 403.
**Proposal:** record instrument/notch, direction, repeats and conditions with future calibration data.
Stimp alone does not specify every part of the launch-to-stop speed curve.

## OpenFairway: pinned source and test audit

Revision `4f3e11be005e7fd118fd0ae6946a85eed4bed8bb`; source read directly from that revision.
No Godot/.NET installation, execution or performance measurement was performed.

| Inspected source | Observed implementation | Implication for our evaluation |
| --- | --- | --- |
| [FlightAerodynamicsModel.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/addons/openfairway/physics/FlightAerodynamicsModel.cs) | Re/spin fits plus low-speed transitions, launch-dependent scales and caps | Version every adjustment; identify which terms have independent data support. |
| [BounceCalculator.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/addons/openfairway/physics/BounceCalculator.cs) | Switches between retention and Penner-inspired response; uses spin magnitude and surface boosts | Include equal-magnitude opposite-spin tests; named physics alone does not establish sign-correct behavior. |
| [BallPhysics.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/addons/openfairway/physics/BallPhysics.cs) | Force/torque updates and speed/spin-dependent ground friction | Check state continuity and energy accounting across phases. |
| [DistanceBenchmarkTests.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/tests/PhysicsTests/DistanceBenchmarkTests.cs) | Out-of-tolerance distances call Assert.Warn; targets mention surface retuning | Warning-only checks do not enforce an accuracy gate. |
| [FsCarryRegressionTests.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/tests/PhysicsTests/FsCarryRegressionTests.cs) | Asserts carry windows and selected apex windows | Useful regression structure; named simulator references are not independent physical observations. |
| [RolloutPhysicsTests.cs](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/tests/PhysicsTests/RolloutPhysicsTests.cs) | Some tests reproduce the friction-multiplier formula locally | Test the production function and external expectations separately. |

The [test README](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/tests/PhysicsTests/README.md)
distinguishes formula-only CI from Godot-backed runtime tests.
The [root license](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/LICENSE)
is MIT. This does not clear every external fixture/asset for reuse. No engine code was copied into
TraceLoft and no dependency choice follows from this audit.

## Staged research tasks

Execute in this order; each task has a concrete output and an evidence requirement.

| Task | Next action | Completion evidence |
| --- | --- | --- |
| R1 — Bounce grouping | Recover launcher-setting labels, ball radius and measurement uncertainties from supporting material | Provenance-backed row mapping; repeat-aware split manifest. If unavailable, mark exploratory fits accordingly. |
| R2 — Flight baseline experiment | Reproduce the candidate equations in an isolated research harness; define domain/zero-state handling | Analytic vacuum/zero-spin cases, step-convergence results and coefficient-domain report; no accuracy claim without held-out observations. |
| R3 — Bounce comparison | Fit rigid restitution/friction and empirical alternatives after R1 | Held-out normal/tangential/spin errors, energy checks, uncertainty and per-campaign results; distinguish repeat interpolation from new-condition generalization. |
| R4 — Putting/cup cases | Finish Holmes' derivation and add skid/modern rim evidence | Speed/offset/slope test matrix, geometry and assumptions; quantitative stopping and capture references. |
| R5 — Lie coverage | Find rough/bunker launch and landing data spanning conditions | Coverage table by club, burial, moisture and available inputs; explicit unsupported cases. |
| R6 — Browser budget | Define a small trajectory payload and playback benchmark after model scope stabilizes | Measured latency/frame-time/memory on target devices; no inference from desktop solver timing alone. |

R1 and literature portions of R4/R5 can proceed without app work. R2/R3 are research experiments,
not an instruction to replace production physics. Wind, actual elevation fields, obstacles and ball
profiles still need their own coverage decisions. The next model recommendation should name which
regimes it supports, its fallback behavior and the evidence that justifies each claim.

## Verification and access record

- Inspected the thesis coefficients and validation table; checked formula transcription at two
  in-range values and one extrapolated value. Underlying flight measurements were not obtained.
- Parsed both bounce campaigns; verified row counts, six finite columns, signs, exact duplicates,
  ranges and immutable download hashes. No parameters were fitted and no train/test split created.
- Read the bunker paper and selected putting/cup sections; distinguished empirical tests,
  approximate theory, simulator regressions and our own proposals.
- Retried inaccessible sources; found accessible thesis and putting copies. Penner's run paper,
  original Smits/Smith and Quintavalla parameter data, and USGA technical bounce proposal remain open.
- Downloaded source material stays temporary; repository files contain original notes, the audit
  program and derived inventory. Link/whitespace and audit repeatability checks recorded in WORK_LOG.md.
