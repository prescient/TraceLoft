"""A stand-in for GSPro Connect on this PC, for testing the relay without the real simulator.

It answers like GSPro does on the range (seen live on 2026-10-16): player information (201) when a
client connects, "Shot received successfully" (200) for each shot, then "ready" (202). Every packet
it receives is printed. --silent accepts connections but never answers, like GSPro off the range.

    .venv\\Scripts\\python tools\\fake_gspro.py --port 9921
"""

import argparse
import json
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_connect import Frames, wire  # noqa: E402

PLAYER = dict(Handed='RH', Club='DR', DistanceToTarget=250)


def serve(client, address, silent):
    print(f'connected: {address[0]}:{address[1]}', flush=True)
    if not silent:
        client.sendall(wire(dict(Code=201, Message='GSPro Player Information', Player=PLAYER)))
    frames = Frames()
    try:
        while data := client.recv(65536):
            for packet in frames.feed(data):
                options = packet.get('ShotDataOptions', {})
                if options.get('ContainsBallData'):
                    ball = packet.get('BallData', {})
                    club = packet.get('ClubData') if options.get('ContainsClubData') else None
                    print(f"shot {packet.get('ShotNumber')}: ball {json.dumps(ball)} club {json.dumps(club)}",
                          flush=True)
                    if not silent:
                        client.sendall(wire(dict(Code=200, Message='Shot received successfully')))
                        client.sendall(wire(dict(Code=202, Message='GSPro ready')))
                else:
                    print('heartbeat', flush=True)
    except OSError:
        pass
    finally:
        client.close()
        print('disconnected', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--port', type=int, default=9921)
    parser.add_argument('--silent', action='store_true', help='never answer (GSPro off the range)')
    args = parser.parse_args()
    sys.stdout.reconfigure(errors='replace')  # a cp1252 console cannot print every character
    server = socket.create_server(('127.0.0.1', args.port))
    print(f'fake GSPro listening on 127.0.0.1:{args.port}' + (' (silent)' if args.silent else ''), flush=True)
    while True:
        client, address = server.accept()
        threading.Thread(target=serve, args=(client, address, args.silent), daemon=True).start()


if __name__ == '__main__':
    main()
