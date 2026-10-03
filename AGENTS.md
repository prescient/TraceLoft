# Working on TraceLoft

These instructions apply throughout this repository. Follow the user's current instructions when
they change an established project preference; update the affected documentation to match.

## Before making changes

- Read [README.md](README.md) for architecture and operation, and the relevant entries in
  [BACKLOG.md](BACKLOG.md), [DECISIONS.md](DECISIONS.md) and [WORK_LOG.md](WORK_LOG.md).
- For storage/backup work, read [DATABASE_PROPOSAL.md](DATABASE_PROPOSAL.md) and
  [docs/DATABASE_OPERATIONS.md](docs/DATABASE_OPERATIONS.md); distinguish implemented core storage
  from proposed analytics and remote backups.
- For VDD source/calibration work, read [docs/VDD_CAPTURE.md](docs/VDD_CAPTURE.md); preserve independent
  profiles and verify both the capture geometry and glyph reads after changing display/table layout.
- For interface, navigation, drill, game or analysis work, read
  [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md) and [NAVIGATION.md](NAVIGATION.md) before implementing.
  Consult [designs/README.md](designs/README.md) and the selected dark studio concept for visual work.

## Product requirements

- Apply the design principles: readable latest-shot feedback, modular practice, explicit exits,
  distinct live/review identity, obvious recording state and clearly labeled estimates.
- Keep the Python service authoritative for shared capture and practice state. Preserve capture
  ownership and localhost access without pairing unless the user requests a change.
- Keep measured data and existing sessions intact. Use isolated data/service instances for
  state-changing verification; preserve active sessions when a necessary reload affects them.
- Make session deletion recoverable and keep crop/training backups outside session lifecycle actions.

## Finishing work

- Verify the affected user journeys, states and responsive layouts described in the design principles.
  Primary UI target: 13-inch / 12.9-inch iPad Pro landscape; retain desktop and phone support.
  Run tests appropriate to behavior changes; documentation-only edits need link/consistency checks.
- When navigation changes, update the map and guards in NAVIGATION.md and check the new paths in the app.
  Do not treat a prior audit as verification of later changes.
- Record progress and actual verification in WORK_LOG.md. Update affected operating/design documents
  and backlog statuses; distinguish implemented behavior from proposed or unverified features.
- Commit after each completed feature, once the relevant checks pass and documentation is updated.
  Include that feature's code, tests and documentation in a focused commit without waiting for a
  separate request. Keep unrelated changes and runtime data out of the commit, and report its hash.
