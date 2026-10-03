using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using TraceLoft.Rela;

int checks = 0;
void Check(bool value, string label) { if (!value) throw new Exception(label); ++checks; }
string Message(int n, bool heartbeat = false) => JsonSerializer.Serialize(new
{
    DeviceID = "TraceLoft isolated test", APIversion = "1", Units = "Yards", ShotNumber = n,
    BallData = new { Speed = 105.2m, HLA = -2.1m, VLA = 14.3m, BackSpin = 3100, SideSpin = -100, TotalSpin = 3101.6m, SpinAxis = -1.8m, CarryDistance = 165.4m },
    ShotDataOptions = new { ContainsBallData = !heartbeat, ContainsClubData = false, LaunchMonitorIsReady = true, LaunchMonitorBallDetected = false, IsHeartBeat = heartbeat }
});
Packet Parse(string text) { using var doc = JsonDocument.Parse(text); return OpenConnectProtocol.Parse(doc.RootElement); }
void Reject(string text, string label) { try { Parse(text); } catch { ++checks; return; } throw new Exception(label); }

var full = Message(1);
Check(Parse(full).Metrics!["HLA"] == -2.1m, "signed HLA retained");
Check(Parse(full).Metrics!["Speed"] == 105.2m, "mph retained");
Check(Parse(full).Metrics!["CarryDistance"] == 165.4m, "yards retained");
Check(Parse(Message(0, true)).Metrics == null, "heartbeat emits no shot");
Reject(full.Replace("Yards", "Meters"), "unsupported units");
Reject(full.Replace("105.2", "-1"), "negative speed");
Reject(full.Replace("\"Speed\"", "\"NoSpeed\""), "missing speed");
Reject(full.Replace("\"ContainsClubData\":false", "\"ContainsClubData\":true"), "unsupported club telemetry");
Reject(full.Replace("\"IsHeartBeat\":false", "\"IsHeartBeat\":true"), "ambiguous heartbeat");
Reject(full.Replace("\"ShotNumber\":1", "\"ShotNumber\":-1"), "negative shot number");
for (int split = 1; split < Encoding.UTF8.GetByteCount(full); ++split)
{
    var bytes = Encoding.UTF8.GetBytes(full);
    var pending = bytes.Take(split).ToArray();
    Check(!OpenConnectProtocol.Take(ref pending, out _), "fragment incomplete");
    pending = pending.Concat(bytes.Skip(split)).ToArray();
    Check(OpenConnectProtocol.Take(ref pending, out var doc), "fragment reassembled"); doc!.Dispose();
    Check(pending.Length == 0, "fragment consumed");
}
byte[] combined = Encoding.UTF8.GetBytes(full + "\n" + Message(2));
Check(OpenConnectProtocol.Take(ref combined, out var first), "first concatenated"); first!.Dispose();
Check(OpenConnectProtocol.Take(ref combined, out var second), "second concatenated"); second!.Dispose();

using var input = new OpenConnectInput();
int shots = 0, statuses = 0, connects = 0, disconnects = 0;
input.PacketReceived += p => { if (p.Metrics != null) Interlocked.Increment(ref shots); else Interlocked.Increment(ref statuses); };
input.ConnectionChanged += value => { if (value) Interlocked.Increment(ref connects); else Interlocked.Increment(ref disconnects); };
Check(input.Start(0), "start ephemeral loopback listener");
Check(input.Start(0), "idempotent start");
async Task<JsonElement> Read(TcpClient client)
{
    byte[] pending = Array.Empty<byte>();
    using var timeout = new CancellationTokenSource(3000);
    while (true)
    {
        var buffer = new byte[4096];
        int n = await client.GetStream().ReadAsync(buffer, timeout.Token);
        if (n == 0) throw new Exception("Connection closed before response");
        pending = pending.Concat(buffer.Take(n)).ToArray();
        if (OpenConnectProtocol.Take(ref pending, out var doc))
        { using (doc) return doc!.RootElement.Clone(); }
    }
}
async Task Send(TcpClient client, string text) => await client.GetStream().WriteAsync(Encoding.UTF8.GetBytes(text));
using (var client = new TcpClient())
{
    await client.ConnectAsync("127.0.0.1", input.Port);
    Check(connects == 0, "socket alone is not a protocol handshake");
    await Send(client, Message(0, true));
    Check((await Read(client)).GetProperty("Code").GetInt32() == 200, "heartbeat acknowledged");
    Check(shots == 0 && statuses == 1 && connects == 1, "heartbeat state only");
    await Send(client, full[..20]); await Send(client, full[20..]); await Read(client);
    Check(shots == 1, "fragmented shot once");
    await Send(client, full); await Read(client);
    Check(shots == 1, "duplicate ignored");
    await Send(client, Message(0)); await Read(client);
    Check(shots == 1, "stale shot ignored");
    await Send(client, Message(2)); await Read(client);
    Check(shots == 2, "next shot accepted");
    await Send(client, Message(3).Replace("Yards", "Meters"));
    Check((await Read(client)).GetProperty("Code").GetInt32() == 500, "unsupported packet rejected over wire");
    Check(shots == 2, "rejected shot not delivered");
}
using (var client = new TcpClient())
{
    await client.ConnectAsync("127.0.0.1", input.Port);
    await Send(client, Message(0, true)); await Read(client);
    Check(shots == 2, "reconnect does not replay");
    await Send(client, Message(1)); await Read(client);
    Check(shots == 3, "fresh producer counter allowed after reconnect");
}
input.Dispose();
Check(input.Start(0), "listener restarts");
input.Dispose();
Check(disconnects > 0, "disconnect state cleared");
Console.WriteLine($"PASS: {checks} checks (parser fragmentation, mapping, localhost transport, status, deduplication, rejection, restart).");
