# Golf ball physics research plan

Approved by the user on 2026-10-03. Research supports a more immersive, lightweight browser golf
simulator with a 2D course view. The goal is physically grounded motion with explicit approximations.
The [research log](BALL_PHYSICS_RESEARCH.md) records evidence, candidate models and open questions.
This plan authorizes research; it does not select an engine or implement new physics.

## Questions and order

| Workstream | Questions |
| --- | --- |
| Inputs and provenance | Which launch measurements reach TraceLoft? Which fields are missing, estimated or provider-modeled? How do launch simulation and reported-endpoint animation differ? |
| Ball flight | Model gravity, drag, lift, spin axis/decay, wind and air properties. Find validated coefficient data across driver, iron, wedge and low-speed flight. |
| Landing and bounce | Model impact speed/angle/spin, surface compliance, restitution, friction, repeated hops and the transition into ground travel. |
| Ground travel | Model slip, rolling, surface resistance, slopes, moisture/firmness and transitions between surfaces. |
| Starting lies | Separate club/grass/sand interactions before launch from landing-surface effects. Investigate rough depth, ball exposure, bunker conditions and uneven stances without double-applying penalties. |
| Putting and cups | Extend the existing flat-green work to launch/skid, slope, speed-dependent hole capture and lip-outs after the full-shot foundation. |
| Simulator approaches | Compare official commercial documentation and inspectable open-source implementations; identify simplifications, validation and implementation costs. |

Research proceeds through input audit, scientific foundation, simulator comparison, candidate-model
assessment, and validation design. Full-shot flight and ground interaction come first; putting follows.

## Evidence and search method

- Prioritize peer-reviewed journals, academic proceedings, university repositories and governing-body
  experiments. Use narrative reviews to discover original experiments, then inspect the originals.
- Search from foundational work through recent publications. Follow references/citations for conflicting
  findings, changing ball construction and improved measurement methods.
- Use official vendor documentation for vendor behavior and source code for implementation behavior.
  Neither category establishes experimental accuracy. Forum claims are leads, not model parameters.
- Record publication date separately from upload, indexing and correction dates. Pin inspected code
  to a commit. Check relevant corrections and distinguish preprints from journal versions.
- Record access depth: metadata only, abstract only, selected full-text sections, or full text.
  Do not derive coefficients from inaccessible material or extend a study beyond its conditions.
- Keep original summaries concise. Link papers/data rather than copying articles into the repository.
  Record data/code licensing before any later implementation or redistribution.

## Research entry format

Every reviewed source records its citation/DOI or stable URL, year, type and access depth; question,
method and conditions; useful findings/equations with units where inspected; limitations;
implications for TraceLoft; confidence in applicability; and next action. Unread leads remain separate.
Use **evidence**, **inference**, **proposal** and **unverified** locally, rather than treating an entire
document as established science. High confidence in a reported experiment is distinct from confidence
that its parameters generalize to our courses.

## Deliverables and acceptance

1. Maintain an annotated bibliography and dated search log, with access gaps and contrary evidence.
2. Audit launch-data completeness, unit conventions and course geometry requirements.
3. Compare a transparent physics baseline, calibrated empirical options and richer models by accuracy,
   inputs, runtime cost, reproducibility and maintenance. Recommend a staged implementation separately.
4. Define analytic checks, held-out experimental comparisons and repeatable browser benchmarks.
   Validate carry, lateral error, apex, flight time, landing velocity/spin, bounce and final rollout.
5. Preserve Python authority for accepted round outcomes and measured source values. Browser animation
   presents saved trajectories; visual timing, skipped animation and reduced motion cannot change score.

Completion of an initial literature pass is not calibration or proof of simulator accuracy. No runtime
or physical-device performance claim follows until an isolated implementation is benchmarked.
