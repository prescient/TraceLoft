# TraceLoft → rēlā connector

This optional DLL implements rēlā's published **Other** plugin contract. It receives the existing
TraceLoft capture worker's ball-only GSPro Open Connect JSON on **127.0.0.1:922** and emits a final
measurement through `OnShotEnded`. It does not split TraceLoft/Capture into separate applications,
alter capture, or add a second database writer. Local recording remains in the existing service.

## Build and install

Requires a .NET SDK (8 can build this net6.0-windows library). The running rēlā application provides
the matching runtime contract; the NuGet package is compile-time metadata only.

```powershell
dotnet build integrations/rela/TraceLoft.Rela.csproj -c Release
dotnet run --project integrations/rela/tests/ProtocolChecks.csproj -c Release
```

Close rēlā, then copy **only** `bin/Release/net6.0-windows/TraceLoft.Rela.dll` beside `rela.exe`.
Do not copy `relaDevicePlugin.dll`, reference assemblies or test binaries. Keep a single external
Other connector installed: the host discovers the first eligible implementation.
Reopen rēlā, choose **Other**, then **Search**. Search starts the localhost listener; the device
only reports connected after the first valid protocol packet. A listening socket alone is not a
connected producer. The connector uses a fixed localhost port in this first implementation.

## Connection check (no shots)

With TraceLoft capture stopped, run from the repository:

```powershell
.venv\Scripts\python.exe integrations/rela/probe_rela.py
```

Expected: `heartbeat acknowledged; no shot sent`, and rēlā temporarily reports Other connected.
Ready stays false. After the probe disconnects, the device returns to disconnected/waiting.
This sends no ball event, writes no TraceLoft records and does not validate the simulator output.

## Live path

1. Open the destination simulator and its supported connector/input.
2. In rēlā choose that simulator and Connect. Installed settings currently use localhost **999**
   for Infinite Tees or **921** for GSPro; confirm the destination is actually listening.
3. In TraceLoft Capture use host **127.0.0.1**, port **922**, and explicitly enable **GSPro sending**
   (the existing label names the wire format). Start capture through the normal web service.
4. Select Search in rēlā if its input listener is not already running. Observe both connections.
5. Compare a real full swing and a putt across original readings, rēlā and the destination before
   relying on this path. Disable rēlā Shot Intelligence/interpolation and short-putt HLA clamp for
   that baseline comparison if you want unmodified transport.
6. For putting, use **Force Putting** in rēlā and confirm **PUTTING / PT**. For full swings switch
   back with **Force Normal**. The adapter does not infer putt mode from a low ball speed.

Verified locally on 2026-10-02 with rēlā **0.1.1.62**: DLL discovery, three acknowledged no-shot
heartbeats, real bridge connection and live putt final-event dispatch. Both rēlā connections show
Connected. TraceLoft is configured for 922 with live capture running; rēlā output uses 999. Putting
mode is selected and Shot Intelligence/interpolation plus HLA clamp have been turned off for raw
validation. Example bridge shot 13 dispatched at 5.2 mph, HLA -1.9°, VLA 0° with no inferred club
metrics. Infinite Tees subsequently displayed captured shot 19's exact **4.4 mph / -0.90° HLA /
0.00° VLA**, with zero back/side spin and **8.54 ft simulated total roll**. Live putting is verified
through both hops. Genuine full-swing and sparse-spin validation remain pending.

TraceLoft deliberately resets sending to off when its service restarts; re-enable it explicitly.
An active TraceLoft **demo** session will not count real shots. Use a real Practice session when
you want live shots included in a drill, in addition to the capture log.

The bridge still sends a five-second heartbeat. A silent client times out after fifteen seconds;
disconnection clears ready/ball state. The connector acknowledges accepted status/dispatch locally,
**not** simulator receipt. TraceLoft currently reports socket sending, not end-to-end delivery.
The input port must not equal rēlā's output port. Do not run the probe alongside live capture.

## Contract and limits

- APIversion `1`, Units `Yards`: speed mph, distances yards, angles degrees, spin rpm. No conversion.
  Metric units and club telemetry are rejected rather than silently misinterpreted.
- Copies speed, HLA, VLA, backspin, sidespin, total spin, spin axis and carry. Requires speed/HLA/VLA;
  zeros for legitimate putting angles are valid. Does not synthesize shots or distances.
- The host's core ball fields are **non-nullable decimal**. Omitted spin/carry fields therefore remain
  the host's zero defaults; Notes lists supplied fields. This API cannot preserve missing vs zero for
  those downstream fields. Original TraceLoft measurements remain intact. Host interpolation may
  interpret zeros as missing; check actual downstream behavior before using sparse putting data.
- Final-only events use `UsesTelemetryFinalShotPath=true`; no duplicate OnBallData/OnShot event.
  Mode/hand changes are reflected in the host but are not sent back to the capture source. No club
  auto-tagging, putt detection from ball speed, historical replay, remote access or persistence.
- Duplicate/non-increasing shot numbers are suppressed **within a connection**. A fresh connection
  permits a reset counter because the existing bridge can restart at zero. Cross-reconnect durable
  deduplication requires a richer producer/session identity; the current bridge never retries shots.
- Input is bounded to 64 KiB with JSON depth 16. Fragmented/concatenated raw JSON is supported.
- The host API is versioned independently. Compilation against 1.0.0 does not prove compatibility
  with every rēlā build, final-only putting dispatch or Infinite Tees acceptance.

## Sources

- [Official Other connector API and lifecycle](https://github.com/eKsiSLe/rela-OtherLM)
- [Compile-time contract 1.0.0](https://www.nuget.org/packages/rela.OtherDevice.Abstractions/1.0.0)
- [rēlā user guide](https://docs.rela.golf/rela/user-guide/)

This connector is independently implemented against the public contract. No rēlā binary is patched
or redistributed. Use the launch monitor and simulator integrations for which you have access.
