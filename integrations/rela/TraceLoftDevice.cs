using relaDevicePlugin;

namespace TraceLoft.Rela;

public sealed class TraceLoftDevice : ILMDevice
{
    readonly OpenConnectInput input = new();
    public bool SessionConnected { get; private set; }
    public bool OtherIsReady { get; private set; }
    public bool OtherBallPresent { get; private set; }
    public bool OtherIsArmed => SessionConnected;
    public bool UsesTelemetryFinalShotPath => true;
    public string SupportedConnectionTypes => "Network";
    public long LastStatusUtcTicks { get; private set; }
    public event Action<DeviceShotData> OnBallData = delegate { };
    public event Action<DeviceShotData> OnShot = delegate { };
    public event Action<DeviceShotData> OnShotEnded = delegate { };
    public event Action<DeviceRawShot> OnRawShot = delegate { };
    public event Action<string> OnNotification = delegate { };
    public event Action<string> OnHandedChange = delegate { };
    public event Action<string> OnModeChange = delegate { };
    public event Action<string> OnError = delegate { };
    public event Action<string> OnNote = delegate { };

    public TraceLoftDevice()
    {
        input.Note += message => OnNote("[TraceLoft] " + message);
        input.ConnectionChanged += connected =>
        {
            SessionConnected = connected;
            if (!connected) OtherIsReady = OtherBallPresent = false;
            LastStatusUtcTicks = DateTime.UtcNow.Ticks;
            OnNotification(connected ? "[Other] Connected: TraceLoft Open Connect input." : "[Other] Disconnected: TraceLoft input; waiting for connection.");
        };
        input.PacketReceived += packet =>
        {
            LastStatusUtcTicks = DateTime.UtcNow.Ticks;
            OtherIsReady = packet.Ready; OtherBallPresent = packet.Ball;
            OnNotification($"[Other] BallStatus: ready={packet.Ready.ToString().ToLowerInvariant()} ball={packet.Ball.ToString().ToLowerInvariant()}");
            if (packet.Metrics is not { } metrics) return;
            var shot = new DeviceShotData
            {
                IsShotValid = true,
                Speed = metrics["Speed"], HLA = metrics["HLA"], VLA = metrics["VLA"],
                BackSpin = metrics.GetValueOrDefault("BackSpin"), SideSpin = metrics.GetValueOrDefault("SideSpin"),
                TotalSpin = metrics.GetValueOrDefault("TotalSpin"), SpinAxis = metrics.GetValueOrDefault("SpinAxis"),
                CarryDistance = metrics.GetValueOrDefault("CarryDistance"),
                // The host contract uses non-nullable decimals for these fields. Record
                // which were supplied; zero defaults are not measured zeros in TraceLoft.
                Notes = new List<string> { $"TraceLoft Open Connect shot {packet.Number}; speed mph, distance yards",
                    "Provided metrics: " + string.Join(",", metrics.Keys) }
            };
            OnShotEnded(shot);
            OnNote($"[TraceLoft] Final shot {packet.Number} emitted once; simulator delivery unconfirmed.");
        };
    }

    public void Init() => OnNote("[TraceLoft] Select Search to listen on 127.0.0.1:922.");
    public string GetDeviceName() => "TraceLoft Open Connect";
    public bool Discover() => Connect();
    public bool Connect() => input.Start();
    public bool Disconnect() { input.Dispose(); return true; }
    public bool Reconnect() { Disconnect(); return Connect(); }
    public bool SetRightHanded() { OnHandedChange("RH"); return true; }
    public bool SetLeftHanded() { OnHandedChange("LH"); return true; }
    public bool SetPuttingMode() { OnModeChange("PUTTING"); return true; }
    public bool SetChippingMode() { OnModeChange("CHIPPING"); return true; }
    public bool SetNormalMode() { OnModeChange("NORMAL"); return true; }
    // Ready is owned by the producer heartbeat; UI Arm must not invent ball readiness.
    public bool ResetReady() => SessionConnected;
    public bool ArmOnly() => SessionConnected;
}
