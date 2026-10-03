# Golf ball physics research log

Started 2026-10-03 under the [approved plan](BALL_PHYSICS_RESEARCH_PLAN.md). This first pass covers
flight, turf contact, starting lies and simulator approaches, with putting work queued for expansion.
It supports the immersive 2D-course idea in [BACKLOG.md](../BACKLOG.md). No new engine, coefficients,
trajectory calculation or animation has been implemented or calibrated by this research.

The most useful initial direction is a compact model of 3D motion presented through the existing 2D
map. This is our **proposal**, not a benchmark result. Ground interaction needs particularly careful
validation, and a starting-lie adjustment must be distinct from the surface on which the ball lands.

## Status and evidence rules

All entries below were checked on 2026-10-03. Access depth describes what was actually inspected;
an available PDF is not necessarily a reviewed PDF. Applicability ratings concern TraceLoft, not a
paper's scientific reputation. Unread sources and blocked downloads are listed separately.

The current app is an endpoint game with configurable gameplay adjustments; see
[current behavior](2D_GAME.md), [shot-flow plan](2D_GAME_PLAN.md), [putting estimates](PUTTING_DISTANCE.md)
and the historical [Fuse evaluation](FUSE_EVALUATION.md). Older statements relaxing simulator accuracy
are superseded as a future goal by the user's 2026-10-03 request, without changing implemented behavior.
Fuse remains ruled out as our selected engine; examining its code does not reverse that decision.

## Input audit

Repository inspection: `open_connect.py` accepts ball speed, vertical/horizontal launch and a
total-spin/axis or backspin/sidespin pair. Carry is optional. The standard forwarding subset does not
include a total-distance/offline pair. TraceLoft's extension can preserve additional normalized metrics;
actual completeness depends on the producer. A valid packet is not evidence of measured, accurate spin.
[Wire contract](RELAY.md).

`golf_sim.py` currently uses reported total distance and signed offline for full-shot placement,
with configured starting-lie reductions and optional direction variation. Putting uses a labeled
speed-to-distance estimate. It does not solve airborne or bounce trajectories. These are observations
of the local implementation, not claims about GSPro or the physical course.

| Quantity | Required research or implementation check |
| --- | --- |
| Speed and launch angles | Convert mph/degrees to SI; verify axes/signs against known left/right shots. |
| Spin | Preserve measured/estimated/absent identity; verify axis conversion and provider convention. Do not invent zero spin. |
| Reported carry/total/offline | Verify downrange versus radial distance and lateral definition; endpoints do not determine a unique flight path. |
| Landing speed, angle and spin | Usually must come from our model; do not label them measured without source evidence. |
| Ball properties and atmosphere | Use named assumptions for ball profile, mass/radius, density and wind; freeze them per shot. |
| Course elevation and surfaces | Surface polygons already support lies. Registered heights/normals and fine green contours require a separate audit. Artwork is not height data. |
| Starting lie | Distinguish a real physical rough/sand shot from a mat shot with a simulated course lie. Avoid counting the same launch effect twice. |

## Reviewed academic and experimental sources

### McPhee 2022 dynamic models review

John McPhee, *A review of dynamic models and measurements in golf*, **Sports Engineering 25**, 22
(2022). [DOI 10.1007/s12283-022-00387-0](https://link.springer.com/article/10.1007/s12283-022-00387-0).
**Access:** publisher abstract, notes and bibliography; main text requires subscription.

**Evidence:** narrative review spanning swing, impact and measurement methods; it distinguishes
impulse-based and continuous-contact treatments and cites 172 works. Useful as a discovery map,
not as a source of coefficients that we have inspected. **Applicability:** medium for architecture,
unassessed for specific models. **Next:** follow the flight/contact references and seek an accessible
author manuscript; do not claim the full review was read.

### Bearman and Harvey 1976 golf ball aerodynamics

P. W. Bearman and J. K. Harvey, *Golf Ball Aerodynamics*, **Aeronautical Quarterly 27(2)**, 112–122
(1976). [DOI 10.1017/S0001925900007617](https://doi.org/10.1017/S0001925900007617).
**Access:** publisher abstract and metadata; full coefficient curves not extracted.

**Evidence:** wind-tunnel tests vary Reynolds number and spin for round/hexagonal dimples;
computed trajectories are compared with driving-machine range observations. Dimple design affects
lift and drag. **Inference:** a constant generic coefficient needs a stated validity range.
**Applicability:** high as foundational evidence, limited for modern-ball parameter selection.
**Next:** obtain full curves and investigate ball design, support/blockage and tested ranges.

### Lyu and colleagues 2020 reverse Magnus effect

Bin Lyu, Jeffery Kensrud and Lloyd Smith, *The reverse Magnus effect in golf balls*,
**Sports Engineering 23**, 3 (2020).
[DOI 10.1007/s12283-020-0318-1](https://link.springer.com/article/10.1007/s12283-020-0318-1).
**Access:** open full text; abstract, methods, uncertainty and coefficient definitions inspected.

**Evidence:** three commercial ball designs projected through still air show negative lift in a
restricted regime, approximately Re 50,000–70,000 and 750–2,250 rpm. Coefficients are obtained from
position/speed measurements; design and drag-crisis behavior matter. Definitions include
`Re = V × diameter / kinematic_viscosity`, `S = angular_speed × radius / V`, and
`force_magnitude = 0.5 × air_density × area × V² × coefficient`.
Here V is m/s, radius/diameter m, angular speed rad/s, density kg/m³ and viscosity m²/s.
**Applicability:** medium; not a rule to give every slow shot negative lift. **Next:** extract
validated coefficient coverage and interpolation uncertainty before choosing any lookup model.

### Moriyama and Okanaga 2023 rotating dimple models

Kohei Moriyama and Hiroo Okanaga, *Effect of dimple shape, occupancy, and volume ratio on aerodynamic
characteristics of golf balls during rotation*, **Transactions of the JSME 89(924)**, 23-00083 (2023).
[DOI 10.1299/transjsme.23-00083](https://www.jstage.jst.go.jp/article/transjsme/89/924/89_23-00083/_article/-char/en).
**Access:** English abstract and metadata; Japanese full PDF not reviewed.

**Evidence:** wind-tunnel measurements on 15 model balls feed trajectory calculations. Dimple
geometry changes lift, drag and predicted trajectories. **Applicability:** medium for selecting
a ball-specific profile, low for direct use as commercial-ball constants. **Next:** inspect
dimensions, Reynolds/spin ranges and scaling before extracting numbers.

### Nathan 2008 spin decay note

Alan M. Nathan, *The Effect of Spin-Down on the Flight of a Baseball* (14 July 2008),
[author-hosted technical note](https://baseball.physics.illinois.edu/spindown.pdf).
**Access:** five-page note inspected, especially its golf-data section; not labeled peer-reviewed.

**Evidence:** compares a heuristic torque model with golf spin-decay measurements attributed to
Smits/Smith and Tavares. The cited golf fits differ in magnitude despite similar form.
**Applicability:** medium as a lead on spin decay, limited as an independent golf experiment.
**Next:** inspect original experiments and their units before adopting a decay coefficient;
do not transplant baseball parameters or mix mph with SI equations.

### McNally and colleagues 2023 flight model

William McNally, Jacob Lambeth and Dustin Brekke, *Combining Physics and Deep Learning Models To
Simulate the Flight of a Golf Ball*, **IEEE/CVF CVPR Workshops**, 5119–5128 (2023).
[Primary paper](https://openaccess.thecvf.com/content/CVPR2023W/CVSports/papers/McNally_Combining_Physics_and_Deep_Learning_Models_To_Simulate_the_Flight_CVPRW_2023_paper.pdf).
**Access:** PDF retrieved directly; methods, dataset, baselines, ablation and runtime sections inspected.

**Evidence:** learns aerodynamic terms inside an ODE using 90,233 TrackMan shots, with 9,024 held
for validation. Table 1 reports landing error 4.75 yd versus 6.63 yd for the quadratic baseline
when both use landing and apex loss. Table 2 reports 34.9 ms/shot on an Intel i7-11850H CPU;
nearby prose says 35.9 ms. Treat this as roughly 35 ms, not an iPad benchmark.
Wind inputs were absent; shots below 8 yd apex were excluded. The authors warn learned coefficients
may not represent true aerodynamics. **Applicability:** medium; trajectory validation is useful,
but this does not establish chip/mishit accuracy or give us a trained model/data license.
**Next:** reproduce a transparent baseline before considering learned corrections.

### Biber and colleagues 2023 measured bounce

Stanisław W. Biber, Kristian M. Jones, Alan R. Champneys, Riku Green and Robert Szalai,
*Measurements and linearized models for golf ball bounce on a green*, **Sports Engineering 26**, 50
(2023). [DOI 10.1007/s12283-023-00442-4](https://link.springer.com/article/10.1007/s12283-023-00442-4).
**Access:** open article methods/discussion/conclusion and corresponding preprint sections inspected.

**Evidence:** 330 artificial-turf and 693 natural-tee bounces, with pre/post velocity and spin from
5,000–10,000 fps video. Despite the title, surfaces were artificial teeing turf and a maintained
tee, not a range of putting greens. Rigid friction/restitution and Penner-style fits struggle
particularly with tangential motion and spin; an empirical piecewise fit performs better.
**Applicability:** high for validation design, limited for transferring surface constants to greens,
rough or sand. **Next:** inspect supplementary data, split repeats/launch settings appropriately
and compare held-out bounce states. A [2024 correction](https://doi.org/10.1007/s12283-024-00478-0)
amends acknowledgement text, not the reported physics.

### Biber and colleagues 2023 compliant contact theory

Stanisław W. Biber, Alan R. Champneys and Robert Szalai, *Analysis of point-contact models of the
bounce of a hard spinning ball on a compliant frictional surface*, **IMA Journal of Applied
Mathematics 88(3)**, 498–523 (2023).
[DOI 10.1093/imamat/hxad020](https://academic.oup.com/imamat/article/88/3/498/7235664);
[2022 preprint](https://arxiv.org/abs/2208.11685).
**Access:** journal abstract/introduction/formulation and preprint sections inspected.

**Evidence:** adding tangential compliance to frictional point contact can represent slip reversal
that simpler rigid or normal-only compliant models miss. Analysis uses a rigid sphere, planar motion
and a compliant surface; the result is not a complete 3D course engine.
**Applicability:** medium for a richer bounce candidate. **Next:** identify parameter fitting,
contact-event stability and cost before deciding whether its extra complexity is warranted.

### Strunk and colleagues 2015 starting ball lie

William D. Strunk, Douglas E. Karcher, Joseph R. Young, Aaron J. Patton and Michael D. Richardson,
*Golf Shot Performance Characteristics Influenced by Ball Lie*, **Crop, Forage & Turfgrass
Management 1**, 1–7 (2015).
[DOI 10.2134/cftm2015.0136](https://acsess.onlinelibrary.wiley.com/doi/abs/10.2134/cftm2015.0136).
**Access:** publisher abstract and metadata; full methods/regression coefficients not reviewed.

**Evidence:** two golfers hit seven-irons from lies in three turf species at mowing heights
0.5–4 inches. Ball exposure was quantified; exposure relates to ball speed, carry and smash factor,
with some golfer-specific accuracy effects. **Applicability:** medium for a ball-exposure model,
low for universal club/player penalties. **Next:** inspect coefficients, sample structure and turf
conditions; avoid reducing rough to grass height or applying a seven-iron relationship to all clubs.

### R and A and USGA 2006 spin generation report

*Interim Report: Study of Spin Generation* (7 August 2006), governing-body experimental report,
[copy hosted by the Japan Golf Association](https://www.jga.or.jp/jga/html/rules/image/info_groove_spin_generation_interim_report_en.pdf).
**Access:** summary, project outline and player/surrogate-testing context inspected, not all 107 pages.

**Evidence:** compares clean and grassy lies, face treatments, balls and grass-surrogate interfaces;
the response depends on equipment and contact conditions. **Inference:** virtual rough should allow
changes in launch/spin, not only a shorter endpoint. **Applicability:** medium for mechanism,
limited by historical equipment and tested lies. **Next:** inspect launch tables and modern follow-up
before selecting penalties; keep rough launch effects separate from friction after landing.

### Nolan and colleagues 2024 sloped starting lies

Cormac Nolan, Michael Hiley and Glen Blenkinsop, *The effect of up and downhill slopes on technique
and performance in golf*, **ISBS Proceedings Archive 42(1)**, article 221 (2024).
[University proceedings record](https://commons.nmu.edu/isbs/vol42/iss1/221/).
**Access:** abstract/metadata only; no detailed slope-specific response curve extracted.

**Evidence:** 45 golfers hit from flat, uphill and downhill conditions, with body/club motion
captured and ball flight calculated. Responses do not support treating all coaching rules as universal.
**Applicability:** medium for identifying stance/delivery interactions; limited for an automatic
launch-direction formula. **Next:** inspect slope magnitudes and individual variability; distinguish
a measured shot hit on a slope from a mat shot representing a virtual slope.

### Pope and colleagues 2014 putting skid

Jeremy Pope, David James, Paul Wood and Erik Henrikson, *The effect of skid distance on distance
control in golf putting*, **Procedia Engineering 72**, 642–647 (2014).
[DOI 10.1016/j.proeng.2014.06.109 and repository record](https://shura.shu.ac.uk/8354/).
**Access:** repository abstract/metadata; full experiment not re-extracted in this pass.

**Evidence:** mechanical putting and high-speed video compare lofts on artificial and natural
surfaces, measuring skid and final distance variation; a ramp estimates surface variability.
**Applicability:** medium for calibration design; not a universal putter-fitting prescription.
**Next:** examine initial speed/spin and skid-to-roll transition before extending the existing
pure-rolling estimates. Putting and cup literature receives its own deeper pass after full shots.

## Simulator implementation and vendor references

### Fuse implementation reference

OpenGolfSim/Fuse, inspected at commit `bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42`.
[Ball physics](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/physics/ballPhysics.ts)
and [surface definitions](https://github.com/OpenGolfSim/fuse/blob/bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42/src/courses/surfaces.ts).
**Access:** source sections for input, flight, contact/roll and surfaces inspected; no execution.

**Evidence:** custom flight uses speed-selected coefficients, capped lift and decay; ground spin is
tracked separately. Surfaces separate friction, restitution, roll resistance, grip and stopping
thresholds. Green braking is Stimp-based; putts skip airborne launch. These are implementation choices,
not experimental validation. **Applicability:** medium as a reference, not a selected dependency.
**Next:** use as a checklist for simplifications and spin consistency. Do not assume comments claiming
realism or matching Stimp establish integrated stopping distance; see existing putting-model notes.

### OpenFairway implementation lead

Digitalhand/OpenFairway, commit `4f3e11be005e7fd118fd0ae6946a85eed4bed8bb`.
[Pinned README](https://github.com/digitalhand/openfairway/blob/4f3e11be005e7fd118fd0ae6946a85eed4bed8bb/README.md).
**Access:** README only; algorithms, tests and calibration history await inspection.

**Vendor/project claim:** Godot/.NET library with aerodynamic fits, Penner-inspired bounce,
surface overrides and headless simulation; README links comparisons against simulator references.
**Applicability:** unassessed as an engine. Simulator matching is not physical validation, and the
documented runtime is not a ready browser integration. **Next:** audit equations, benchmark provenance,
test coverage and license at the pinned revision before proposing any reuse.

### EA SPORTS PGA TOUR course and lie behavior

Electronic Arts, *Pure Strike Gameplay Deep Dive* (2023),
[official developer description](https://www.ea.com/games/ea-sports-pga-tour/pga-tour/news/ea-sports-pga-tour-gameplay-deep-dive).
**Access:** course dynamics and recovery/lie sections inspected.

**Vendor claim:** separate surface speed/firmness and rough length, with course-specific profiles
informed by scanned geometry and course data. Recovery attributes influence bad-lie effects.
**Applicability:** medium as product reference; no published equations, coefficients or independent
validation here. **Next:** borrow the distinction between speed, firmness and lie depth; keep fictional
player skills and mid-flight user spin outside measured-shot physics unless explicitly offered as gameplay.

### Trackman aerodynamic modeling reference

Trackman, *Understanding Trackman's Golf Normalization Feature* (2014),
[official explanation](https://www.trackman.com/blog/normalization-feature-explained).
**Access:** aerodynamic model and normalization sections inspected.

**Vendor claim:** builds ball-specific aerodynamic models from controlled launch testing, then
uses launch data to calculate normalized flight for selected conditions.
**Applicability:** medium for workflow, not a source of proprietary parameters or accuracy guarantees.
**Next:** distinguish actual trajectory, modeled carry and normalized results in any comparison;
freeze environmental assumptions rather than fitting a universal distance multiplier.

### SKYTRAK starting lie reference

SKYTRAK, *Play Like It's the U.S. Open: How SKYTRAK Lie Penalties Make Your Practice Feel Like
Shinnecock Hills*, [official vendor article](https://www.skytrakgolf.com/blogs/articles/play-like-its-the-u-s-open-how-skytrak-lie-penalties-make-your-practice-feel-like-shinnecock-hills).
**Access:** article inspected; publication date not independently established in this pass.

**Vendor description:** simulator lie effects account for rough/bunker conditions absent when
hitting from a normal mat. **Applicability:** medium for explaining user controls, unassessed for
quantitative physics. **Next:** consider an explicit physical-lie versus virtual-lie policy; the article
does not supply a transferable penalty function.

### GSPro information boundary

[Official Open Connect v1](https://gsprogolf.com/GSProConnectV1.html) documents launch inputs,
not GSPro flight/contact equations. Its [in-game UI guide](https://gspro.gitbook.io/gspro-knowledge-base/in-game-information/in-game-user-interface)
documents lie display and selection controls. **Access:** previously checked official protocol/UI;
this pass searched for documented physics/lie formulas without finding a verified parameter set.

**Unverified:** exact current GSPro lie reductions and physics implementation. Forum percentages
were excluded as evidence. **Next:** seek first-party technical material and, if separately authorized,
controlled isolated comparisons. Do not send experimental shots into the user's live simulator/round.

## Dataset candidate

Biber, Jones and Green, *Measurements for golf ball bounce*, University of Bristol, available
19 December 2022. [Dataset record](https://research-information.bris.ac.uk/en/datasets/measurements-for-golf-ball-bounce/),
[DOI 10.5523/bris.1cwnj42n63q5w2sc843iww7bbd](https://doi.org/10.5523/bris.1cwnj42n63q5w2sc843iww7bbd).
**Access:** metadata inspected; videos/data files not downloaded or analyzed. The journal also
links numeric supplementary files. **Next:** confirm data format, units, repeat grouping and permitted
reuse before creating a small validation fixture. Dataset access is not yet a reproduced benchmark.

## Candidate models and preliminary conclusions

This table is our **engineering assessment**, subject to experiments and a later implementation decision.

| Candidate | Intended role | Inputs and tradeoffs | Current recommendation |
| --- | --- | --- | --- |
| Reported-endpoint animation | Show motion to an existing reported outcome | Requires valid endpoint geometry; apex/bounce timing remain inferred | Keep as a clearly labeled fallback; never call its path measured. |
| 3D point-mass flight with empirical coefficients | Predict flight from launch speed/angles/spin | Needs coefficient coverage, atmosphere and sign conventions | First baseline to evaluate; use SI and explicit ball profiles. |
| Learned coefficients inside a physics solver | Correct flight model against rich observations | Needs adequate training data, constraints and distribution coverage | Defer until a transparent baseline and independent validation exist. |
| Impulse bounce with friction and restitution | Fast landing approximation | Easy to integrate; tangential/spin behavior may fit poorly | Benchmark as a baseline, not a universal turf model. |
| Empirical landing-state mapping | Fit observed bounce states on known surfaces | Surface-specific training, bounds and energy checks essential | Compare with the simple bounce baseline using held-out cases. |
| Compliant normal and tangential contact | Represent finite-duration turf interaction | More parameters and potentially smaller contact time steps | Evaluate only if measured failures justify added complexity. |
| Slip plus rolling resistance and slope | Continue travel after contact | Needs spin/contact state and surface calibration | Treat as a distinct phase; Stimp does not determine firmness. |

**Proposal:** compute one authoritative trajectory per accepted shot in Python, returning sampled
position/height, phase changes and outcome to the browser. Canvas/SVG can present a top-down path,
shadow and restrained height cue without a heavy scene. This fits current ownership, but performance
and payload size must be benchmarked. Animation interpolation must not recalculate physics or score.

**Proposal for lies:** use separate configuration for (a) modifications to mat-measured launch
conditions representing a virtual starting lie, (b) landing/rolling surface parameters, and
(c) terrain geometry/obstacles. Preserve raw input and each applied transformation. A real shot already
hit from rough must not automatically receive the same synthetic rough launch penalty again.
Ball exposure, grass moisture/depth and bunker condition need evidence; fixed percentages remain
gameplay defaults until validated. Do not infer physical-player adaptation solely from slope angle.

## Proposed validation and performance work

No checks below have been executed against a new physics implementation.

| Validation group | Cases and recorded measures |
| --- | --- |
| Analytic flight | Vacuum parabola, zero spin, zero wind, known elevation; carry/apex/time and consistent axes. |
| Aerodynamic flight | Driver, mid-iron, wedge, low launch/spin, fade/draw and wind; compare carry, offline, apex, flight time and landing state against independent observations. |
| Numerical stability | Reduce time step/tolerance and compare results; detect ground contact between samples; enforce finite state and defined zero-speed handling. |
| Bounce | Hold out repeated launch settings/surfaces; compare normal/tangential velocity and spin before/after impact, then whole-shot rollout. Test energy accounting and multiple hops. |
| Rolling and slope | Flat Stimp reference plus other speeds, uphill/downhill/cross-slope, zero slip and surface crossings; no artificial reversal from overshooting friction. |
| Lies | Paired physical measurements by club, ball exposure and condition; separate starting launch effects from landing behavior. |
| Cups and hazards | Slow/fast centered and edge putts, lip-out candidates, water/OB and obstacle contact; physical capture distinct from a gimme/scoring rule. |
| Replay | Saved model/course revisions, parameters and randomness reproduce the same outcome; refresh/skip/reduced motion do not add strokes. |
| Browser | Real iPad Safari, desktop and phone: solver latency, animation frame times, payload size, memory and load time. Targets remain to be chosen; viewport checks are not device benchmarks. |

Use held-out data grouped by session/launch setting where repeats could leak into both training and
validation. Record bias and distributions, not just one average error. Separate measurement noise,
model error and simulator disagreement. Comparing against GSPro alone cannot establish real-world accuracy.

## Next reading and access gaps

| Lead | Status and next question |
| --- | --- |
| Ferguson, McNally and McPhee (2022), *Predicting the Flight of a Golf Ball*, DOI 10.5703/1288284317493 | [Purdue metadata](https://docs.lib.purdue.edu/resec-isea/2022/session05/4/) verified; PDF returned 403. Extract original fitted polynomials, dataset and limits before use. |
| Smits and Smith (1994), *A new aerodynamic model of a golf ball in flight* | Original chapter not obtained; cited by academic sources. Verify publication details and original spin-decay/force data. |
| Quintavalla (2002), *A generally applicable model for the aerodynamic behavior of golf balls*, Science and Golf IV | Located through journal references, not read. Seek original coefficient conventions and validation. |
| Penner (2002), *The run of a golf ball*, DOI 10.1139/p02-035 | [Author PDF](https://raypenner.com/golf-run.pdf) surfaced in search but direct browsing timed out. Revisit effective-contact-angle model against later bounce evidence. |
| Penner (2002), *The physics of putting*, DOI 10.1139/p01-137 | [Author PDF](https://raypenner.com/golf-putting.pdf) underlies existing notes; this pass timed out. Re-extract assumptions, slope and cup model rather than rely on old summaries. |
| USGA (2012), Stimpmeter instruction booklet | [Official PDF](https://www.usga.org/content/dam/usga/pdf/imported/StimpmeterBookletFINAL.pdf) returned 403. Inspect measurement protocol and release conditions. |
| USGA/R&A (2021), proposed bounce model for optimum overall distance | [Official proposal page](https://www.usga.org/content/usga/home-page/equipment-standards/technical-library-for-equipment/2021-optimization-proposal.html); PDF blocked. Assess intended testing scope rather than treat it as a complete course model. |
| Roh and Lee (2010), *Golf ball landing, bounce and roll on turf* | Located in journal references; original paper still to inspect. Compare turf deformation and Stimp treatment. |
| Sand-wedge particle simulation | [Publisher lead](https://www.witpress.com/elibrary/wit-transactions-on-modelling-and-simulation/41/15225). Bibliography/full method pending; investigate a reduced bunker-launch surrogate rather than simulating every grain. |
| Uneven lies and hole capture | Seek slope-specific experiments, Holmes' original cup model and modern replication; separate player biomechanics from ball dynamics. |

## Search and progress record

### 2026 October 3 initial pass

- Searched academic/publisher/university sources for golf aerodynamics, lift/drag/spin decay,
  compliant turf bounce, rough/grass contact, bunker simulation and slope-dependent lies.
  Followed McPhee and Biber bibliographies to original studies and the bounce dataset.
- Inspected accessible full-text sections for modern flight and contact studies; recorded abstract-only
  reviews/experiments separately. Checked the bounce paper's correction and journal/preprint dates.
- Re-inspected pinned Fuse code; pinned OpenFairway's current README. Read official EA, Trackman
  and SKYTRAK descriptions and excluded forum claims from model conclusions.
- Captured input constraints, candidate models and a proposed validation matrix. The next research
  pass should obtain coefficient/data coverage, inspect bounce supplementary files, deepen bunker and
  putting/cup work, and audit a second engine's actual equations/tests. No engine has been selected.
