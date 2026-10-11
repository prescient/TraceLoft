# Architecture improvements — 2026-10-10

The supplied review recommends incremental improvements to Python/SQLite/the web interface.
Preserve server-owned scoring, independent acquisition, immutable evidence and outcome pins,
transactional recovery and existing UI/navigation. Review measurements are isolated stress probes,
not production latency claims. Verify each concern against current code before changing it.

## Work order and acceptance

1. **Recalculation cache:** reconstruct each selected session once per staging batch. Preserve
   membership, frozen inputs, outputs and publication guards. Regression checks the five-attempt
   fixture and existing calculation lifecycle tests.
2. **Incremental persistence:** append attempts and update changed session/attempt fields in the
   same receipt transaction. Unchanged historical attempts must receive no writes. Corrections,
   inclusions, immutable context/results and rollback must still behave identically. Measure database
   field writes using isolated data, not wall-clock thresholds.
3. **Revision-based live state:** idle connections should receive no repeated full history. Fetch
   snapshots on initial connection/recovery and use small revision notifications for changes.
   Discard stale/out-of-order responses, retain reconnect/ownership/recording feedback and avoid
   losing unfinished browser edits on shot updates. Review tablet/phone and controller regressions.
4. **Feature contracts:** central registry for identity, settings validation, creation/restoration and
   capabilities, then browser mount/update/dispose. Retain existing drill IDs, routes and DTOs.
5. **Analytical query boundary:** shared parameterized SQL scope/lineage, bounded detail reads and
   full-query summaries/CSV. Preserve missingness, inclusion counts, numerical AND predicates,
   source/estimate basis, ownership and robust quartiles; pagination must not truncate statistics.
6. **Frozen migrations and verification:** numbered immutable SQL snapshots with transactional
   upgrades/backups/reconciliation, explicit lifecycle/scoring invariants, a repeatable verification
   command and browser controller regression coverage. At the user's request (2026-10-11) the
   repository was formatted once in an isolated formatting-only commit, listed in
   `.git-blame-ignore-revs`, so behavior changes never share a diff with formatting.

## Future product ideas

Server-shared dynamic analysis workspaces, calculation-provider contracts, operational timing/save/
backup diagnostics, managed swing media and a thin desktop host remain separate feature work.
Desktop/video are already in the backlog; none require mixing TraceCapture into this repository.

Implementation progress, measurements and limits are recorded in [WORK_LOG](../WORK_LOG.md).
This document is a work plan, not a claim that all six stages have shipped.

Stages 1–2 are implemented: staging reconstructs a session once per batch; scorers append only the
new attempt, and state/correction saves synchronize changed typed leaves. The append path validates
historical identities and relies on scorer-owned immutable history; corrections use the general
save path. Cache entries publish after the outer transaction commits. Prefix validation, collection
aggregation and general correction hashing still grow with session size; writes to unchanged
historical attempt fields do not.

Stage 3's notification/controller foundation is implemented. Idle polling examines bounded service
status and a committed database-change counter, never trajectories or summaries. Protocol 2 sends
small revision notices and the browser coalesces state fetches, ignores stale/disposed requests and
reconnects. Runner/animation repaints retain draft text, caret/focus, expansion and scroll; existing
range selections remain in their view model. Old clients receive changed-only snapshots; new clients
also support an older server during an upgrade. Full-history state fetches on changes still exist:
incremental shot deltas, lazy trajectories and bounded detail remain follow-up work, along with
feature mount/update/dispose rather than whole-runner repainting.

Event-loop isolation (2026-10-11): revision checks use `PRAGMA data_version` on a separate
read-only connection and never take the writer lock. State requests read golfer rows the same way.
Analysis, export, backups, calculation previews/history, collection analysis, the Sessions list and
Play preview/recommendations read a private WAL snapshot (`Store.reading()`) on worker threads.
Calculation staging plans from a snapshot and re-plans under the lock only if a commit intervened.
Post-session backups run on a thread joined at shutdown. `read_session` and `hydrate_session` use
a fixed number of queries per session instead of several per attempt. A write transaction on another
thread still delays event-loop *writes* (shot intake) until it commits, so keep writes short.

Stage 6's repeatable verification command is available as `python verify.py`, with automatic project
venv selection, both suites, nonzero failure exit and external logs/report including commit and dirty
tree state. This supplements controller/backend regressions and manual browser/device checks;
it does not claim to automate every browser journey. Frozen migration files remain pending.
