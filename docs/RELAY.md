# Relay and source separation

## Everyday use

Launch TraceLoft. It listens automatically. Select the destination once in Relay; there is no Apply,
connection wizard or adapter installation. Off means record only. The destination and optional port
override persist in SQLite. Source readiness, local storage errors and simulator connectivity are
separate states; a simulator outage does not stop local recording.

## Wire contract

[GSPro Open Connect v1](https://gsprogolf.com/GSProConnectV1.html) is raw UTF-8 JSON over TCP.
TraceLoft binds localhost:900, accepts one producer at a time, handles fragmented/concatenated JSON,
and limits pending input to 256 KiB. Use periodic heartbeat packets while connected (idle timeout 20s).

```json
{"DeviceID":"My monitor","Units":"Yards","ShotNumber":1,"APIversion":"1",
 "BallData":{"Speed":4.2,"SpinAxis":0,"TotalSpin":0,"HLA":-0.4,"VLA":0},
 "ShotDataOptions":{"ContainsBallData":true,"ContainsClubData":false}}
```

The usual ball packet has ten required leaf fields across identity, BallData and the two Contains
flags, not nine. Units defaults to Yards; this version rejects other units. Speed is mph, launch
angles degrees and spin rpm. A complete BackSpin/SideSpin pair is accepted instead of total/axis.
Unknown readings are omitted, never synthesized as zero. ClubData is optional; ambiguous impact and
closure-rate units stay raw, as does SpeedAtImpact's distinct meaning. Supported normalized club
metrics are speed, attack, face, lie, loft and path. Source semantics remain provider-reported.

A no-ball heartbeat uses ContainsBallData=false, ContainsClubData=false, IsHeartBeat=true and optional
LaunchMonitorIsReady/LaunchMonitorBallDetected. It records no shot. Code 200 follows SQLite commit,
501 rejects invalid input, and 503 reports temporary storage/ownership failure. Code 201 carries
simulator player information when available. Two-way control is not a club auto-tagging feature.

Optional `TraceLoft` extension:
- ReceiptId, ProducerId, StreamId and CapturedAt (UTC ISO timestamp) give durable retry identity.
- Metrics carries documented internal normalized fields (see data/metric_mapping.normalized.v1.json).
- Source and Evidence preserve provenance and source readings.
- Context freezes practice_session_id, equipment_selection, range_context, collection_context and
  game_context. The latest Context is returned in every Code 200 under TraceLoft.Context.
- Recovered=true stores evidence without advancing a live drill or forwarding.

Ordinary Open Connect senders need none of these extensions. Same-connection duplicate shot numbers
with identical packets are acknowledged once; conflicting data is rejected. Standard Open Connect
has no cross-reconnect unique shot ID: a sender must not replay uncertain old shots after reconnect.
Extended stable receipt IDs make retries idempotent even after restart. Readings more than 15 seconds
old are stored but neither added to the active drill nor forwarded. Historical imports require their
own review workflow, still planned. Extra top-level vendor fields survive in raw_packet in SQLite.

## Forwarding

GSPro defaults to localhost:921; Infinite Tees to localhost:999. Only documented fields are forwarded,
with a relay-owned monotonically increasing ShotNumber per service run. Private extensions stay in
SQLite. The relay sends readiness heartbeats, reconnects automatically, and never queues/replays shots
for a disconnected simulator. Socket-write evidence is labeled unacknowledged: simulator Code 200 has
no shot identifier, so it cannot establish durable per-shot delivery. Avoid claiming exactly-once
simulator receipt. Local durable receipt and simulator response are separate evidence.

On 2026-10-03 the installed Infinite Tees listener acknowledged a direct no-shot heartbeat with Code
200 while rēlā was closed. This verifies its direct protocol endpoint, not real-shot trajectory or
scoring equivalence. Isolated fake peers verify both destination modes; genuine putt/full swing
acceptance and a real GSPro connection remain follow-up checks.

## Repository boundary

TraceLoft owns SQLite, practice, play, analytics and relay. TraceCapture privately owns screen/OCR,
calibration, glyphs/crops and a durable local outbox. Neither imports sibling code or accesses the
other application's files. The small protocol module is copied/versioned in each repository.
The original GolfData repository remains the private historical archive. Publish only the new
TraceLoft repository, after its separate release review; never publish the combined archive.
