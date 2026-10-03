"""Verify the local rēlā connector without emitting a shot or touching TraceLoft storage."""
import argparse
import json
import socket
import time


def probe(port=922, seconds=10):
    payload = dict(DeviceID="TraceLoft connection probe", Units="Yards", ShotNumber=0,
                   APIversion="1", ShotDataOptions=dict(ContainsBallData=False,
                   ContainsClubData=False, LaunchMonitorIsReady=False,
                   LaunchMonitorBallDetected=False, IsHeartBeat=True))
    with socket.create_connection(("127.0.0.1", port), timeout=3) as peer:
        peer.settimeout(3)
        end = time.monotonic() + seconds
        while True:
            peer.sendall(json.dumps(payload).encode("utf-8"))
            buffer = ""
            while True:
                data = peer.recv(4096)
                if not data:
                    raise RuntimeError("Connector closed before acknowledging the heartbeat")
                buffer += data.decode("utf-8")
                if len(buffer) > 65536:
                    raise RuntimeError("Oversized acknowledgement")
                try:
                    reply, _ = json.JSONDecoder().raw_decode(buffer.lstrip())
                    break
                except json.JSONDecodeError:
                    continue
            if reply.get("Code") != 200 or reply.get("Message") != "Status accepted":
                raise RuntimeError(f"Unexpected acknowledgement: {reply}")
            print(f"127.0.0.1:{port}: heartbeat acknowledged; no shot sent", flush=True)
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(5, remaining))
    print("Probe disconnected. This does not verify downstream simulator delivery.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=922)
    parser.add_argument("--seconds", type=float, default=10)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 0 <= args.seconds <= 60:
        parser.error("Port must be 1–65535 and seconds 0–60")
    try:
        probe(args.port, args.seconds)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"Connection test failed: {error}\nSelect Other → Search in rēlā after installing the connector.\n")
