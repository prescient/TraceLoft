using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace TraceLoft.Rela;

// Deliberately limited to the existing TraceLoft ball-only, yards/mph output.
// This is a local input adapter, not a general GSPro server or durable shot queue.
public sealed record Packet(int Number, bool Ready, bool Ball, Dictionary<string, decimal>? Metrics);

public static class OpenConnectProtocol
{
    public const int MaxBytes = 65536;
    public static Packet Parse(JsonElement root)
    {
        if (root.GetProperty("APIversion").GetString() != "1" || root.GetProperty("Units").GetString() != "Yards")
            throw new FormatException("Only APIversion 1 with Yards (mph speed) is supported.");
        if (string.IsNullOrWhiteSpace(root.GetProperty("DeviceID").GetString()))
            throw new FormatException("DeviceID is required.");
        int number = root.GetProperty("ShotNumber").GetInt32();
        if (number < 0) throw new FormatException("ShotNumber must be nonnegative.");
        var options = root.GetProperty("ShotDataOptions");
        bool ready = options.GetProperty("LaunchMonitorIsReady").GetBoolean();
        bool ball = options.GetProperty("LaunchMonitorBallDetected").GetBoolean();
        bool heartbeat = options.GetProperty("IsHeartBeat").GetBoolean();
        bool containsBall = options.GetProperty("ContainsBallData").GetBoolean();
        if (options.GetProperty("ContainsClubData").GetBoolean())
            throw new FormatException("Club telemetry is not supported by this adapter yet.");
        if (heartbeat && containsBall) throw new FormatException("A heartbeat cannot contain a shot.");
        if (!containsBall) return new Packet(number, ready, ball, null);
        var data = root.GetProperty("BallData");
        var metrics = new Dictionary<string, decimal>();
        foreach (string key in new[] { "Speed", "HLA", "VLA", "BackSpin", "SideSpin", "TotalSpin", "SpinAxis", "CarryDistance" })
            if (data.TryGetProperty(key, out var value)) metrics.Add(key, value.GetDecimal());
        foreach (string required in new[] { "Speed", "HLA", "VLA" })
            if (!metrics.ContainsKey(required)) throw new FormatException("Missing " + required);
        if (metrics["Speed"] <= 0 || metrics["Speed"] > 250 || Math.Abs(metrics["HLA"]) > 90 || Math.Abs(metrics["VLA"]) > 90)
            throw new FormatException("Ball speed or launch angle outside supported bounds.");
        foreach (string key in new[] { "BackSpin", "TotalSpin", "CarryDistance" })
            if (metrics.TryGetValue(key, out decimal value) && value < 0) throw new FormatException("Negative " + key);
        return new Packet(number, ready, ball, metrics);
    }

    // JSON objects can be fragmented or concatenated: TCP has no message boundaries.
    public static bool Take(ref byte[] pending, out JsonDocument? document)
    {
        var reader = new Utf8JsonReader(pending, false, new JsonReaderState(new JsonReaderOptions { MaxDepth = 16 }));
        if (!JsonDocument.TryParseValue(ref reader, out document)) return false;
        pending = pending.AsSpan((int)reader.BytesConsumed).ToArray();
        return true;
    }
}

public sealed class OpenConnectInput : IDisposable
{
    public const int DefaultPort = 0922; // rēlā output retains 921 (GSPro) or 999 (Infinite Tees).
    readonly object gate = new();
    TcpListener? listener;
    TcpClient? client;
    long generation;
    public event Action<Packet> PacketReceived = delegate { };
    public event Action<bool> ConnectionChanged = delegate { };
    public event Action<string> Note = delegate { };
    public int Port { get; private set; }

    public bool Start(int port = DefaultPort)
    {
        lock (gate)
        {
            if (listener != null) return true;
            try
            {
                listener = new TcpListener(IPAddress.Loopback, port);
                listener.Start(1);
                Port = ((IPEndPoint)listener.LocalEndpoint).Port;
                var current = listener;
                long epoch = ++generation;
                _ = Task.Run(() => Run(current, epoch));
                Note($"Listening on 127.0.0.1:{Port}; waiting for an Open Connect packet.");
                return true;
            }
            catch (Exception ex) { listener?.Stop(); listener = null; Note("Listener failed: " + ex.Message); return false; }
        }
    }

    void Run(TcpListener server, long epoch)
    {
        try
        {
            while (true)
            {
                using var peer = server.AcceptTcpClient();
                lock (gate) { if (epoch != generation) return; client = peer; }
                peer.ReceiveTimeout = 15000;
                peer.SendTimeout = 2000;
                var stream = peer.GetStream();
                byte[] pending = Array.Empty<byte>(), buffer = new byte[4096];
                int lastShot = -1;
                bool identified = false;
                string? producer = null;
                try
                {
                    while (true)
                    {
                        int size = stream.Read(buffer, 0, buffer.Length);
                        if (size == 0) break;
                        pending = pending.Concat(buffer.Take(size)).ToArray();
                        if (pending.Length > OpenConnectProtocol.MaxBytes) throw new FormatException("Input buffer exceeded 64 KiB.");
                        while (OpenConnectProtocol.Take(ref pending, out var document))
                        {
                            using (document)
                            {
                                var packet = OpenConnectProtocol.Parse(document!.RootElement);
                                string device = document.RootElement.GetProperty("DeviceID").GetString()!;
                                if (producer != null && producer != device) throw new FormatException("Producer changed within one connection.");
                                producer = device;
                                lock (gate)
                                {
                                    if (epoch != generation) return;
                                    if (!identified) { identified = true; ConnectionChanged(true); }
                                    if (packet.Metrics != null && packet.Number <= lastShot)
                                    {
                                        Reply(stream, 200, "Duplicate/stale shot ignored", packet.Number);
                                        continue;
                                    }
                                    // Final callback only; never replay shots on reconnect.
                                    PacketReceived(packet);
                                    if (packet.Metrics != null) lastShot = packet.Number;
                                }
                                Reply(stream, 200, packet.Metrics == null ? "Status accepted" : "Accepted by connector (not simulator acknowledgement)", packet.Number);
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    lock (gate)
                        if (epoch == generation)
                        {
                            Note("Client ended: " + ex.Message);
                            try { Reply(stream, 500, "Rejected or disconnected: " + ex.Message, 0); } catch { }
                        }
                }
                finally
                {
                    lock (gate) if (epoch == generation) { client = null; ConnectionChanged(false); }
                }
            }
        }
        catch (Exception ex)
        {
            lock (gate) if (epoch == generation) { Note("Listener stopped: " + ex.Message); server.Stop(); listener = null; ConnectionChanged(false); }
        }
    }

    static void Reply(NetworkStream stream, int code, string message, int number)
    {
        byte[] data = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new { Code = code, Message = message, ShotNumber = number }));
        stream.Write(data, 0, data.Length);
    }

    public void Dispose()
    {
        lock (gate)
        {
            ++generation;
            client?.Close(); client = null;
            listener?.Stop(); listener = null;
            ConnectionChanged(false);
        }
    }
}
