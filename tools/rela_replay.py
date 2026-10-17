"""Replay rēlā's real GSPro packets from its log into a TraceLoft input port, for testing (D74).

rēlā logs every packet it sends to GSPro as `SEND=> [ShotEnded] OUT_JSON {...}`. This sends those
packets, renumbered from 1, to a TraceLoft instance as rēlā would (a ready heartbeat first, then
each shot), and prints TraceLoft's replies. Use it only against a test instance: the shots are stored.

    .venv\\Scripts\\python tools\\rela_replay.py --port 931 --last 6
"""

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_connect import Frames, wire  # noqa: E402

LOG = Path(os.environ.get('LOCALAPPDATA', '')) / 'rela' / 'rela.log'
MARK = 'OUT_JSON '


def packets(path, last):
    shots = []
    for line in path.read_text('utf-8', errors='replace').splitlines():
        if MARK in line:
            shots.append(json.loads(line.split(MARK, 1)[1]))
    return shots[-last:] if last else shots


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--port', type=int, required=True, help='the test TraceLoft input port')
    parser.add_argument('--last', type=int, default=6, help='how many of the newest shots (0 = all)')
    parser.add_argument('--gap', type=float, default=1.0, help='seconds between shots')
    parser.add_argument('--log', type=Path, default=LOG)
    args = parser.parse_args()
    sys.stdout.reconfigure(errors='replace')  # a cp1252 console cannot print "rēlā"
    if args.port in (900, 921):
        raise SystemExit('Refusing ports 900/921: replay only into a test instance.')
    shots = packets(args.log, args.last)
    print(f'{len(shots)} rēlā packets from {args.log}', flush=True)
    sock = socket.create_connection(('127.0.0.1', args.port), 3)
    sock.settimeout(3)
    frames = Frames()

    def send(packet):
        """Send one packet and print replies up to TraceLoft's final answer (200/5xx; 201 is info)."""
        sock.sendall(wire(packet))
        while True:
            for reply in frames.feed(sock.recv(65536)):
                print(f"  ← {reply.get('Code')} {reply.get('Message', '')}", flush=True)
                if reply.get('Code') != 201:
                    return

    device = shots[0]['DeviceID'] if shots else 'rela'
    send(dict(DeviceID=device, Units='Yards', ShotNumber=0, APIversion='1',
              ShotDataOptions=dict(ContainsBallData=False, ContainsClubData=False, IsHeartBeat=True,
                                   LaunchMonitorIsReady=True, LaunchMonitorBallDetected=False)))
    for number, packet in enumerate(shots, 1):
        packet = dict(packet, ShotNumber=number)
        club = packet.get('ClubData') or {}
        print(f"→ shot {number}: {packet['BallData'].get('Speed')} mph, club {club.get('Speed')}", flush=True)
        send(packet)
        time.sleep(args.gap)
    sock.close()


if __name__ == '__main__':
    main()
