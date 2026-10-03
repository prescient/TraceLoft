# TraceLoft architecture decisions

## D48 — Independent application and direct Relay (2026-10-03)

TraceLoft and TraceCapture are sibling repositories with clean independent history. The combined
GolfData repository remains a private archive. TraceLoft contains no acquisition implementation.
Use GSPro Open Connect v1 on localhost:900 for input and optional direct localhost:921/999 output.
Do not require rēlā. Local persistence precedes acknowledgement, and forwarding cannot block storage
for more than its bounded write timeout. Preserve raw extensions and freeze shot-time context.

Use one auto-saving destination selector and remembered settings. No separate listening start/stop
step. Normal shutdown preserves the unfinished session and next launch restores it. Explicit session
end/abandon remains the user's action. Keep the existing SQLite path and immutable historical metrics.

## Carried-forward product decisions

- Python owns shared practice and SQLite; browser clients present/control it.
- Localhost needs no pairing. LAN mode is opt-in for trusted networks.
- White Vector surfaces, square controls, cobalt selection; circular club buttons remain.
- Robust club summaries use median/IQR, with sample counts and missing data distinct from zero.
- Original shots, source evidence and exclusions remain traceable; session deletion is recoverable.
- Models, demo shots and course artwork are explicitly distinguishable from measured outcomes.
- Full research and historical decisions remain in the private combined archive; current operation
  follows README, docs/RELAY.md and DESIGN_PRINCIPLES.md.
