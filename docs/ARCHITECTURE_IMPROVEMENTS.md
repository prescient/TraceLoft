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
   command and browser controller regression coverage. Formatting follows modules being changed;
   avoid a repo-wide mechanical rewrite obscuring behavior changes.

## Future product ideas

Server-shared dynamic analysis workspaces, calculation-provider contracts, operational timing/save/
backup diagnostics, managed swing media and a thin desktop host remain separate feature work.
Desktop/video are already in the backlog; none require mixing TraceCapture into this repository.

Implementation progress, measurements and limits are recorded in [WORK_LOG](../WORK_LOG.md).
This document is a work plan, not a claim that all six stages have shipped.
