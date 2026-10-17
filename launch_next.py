"""Start or stop the TraceLoft-next test copy (branch rela-direct) from the desktop shortcuts.

It runs apart from the real TraceLoft: its own database (%USERPROFILE%\\GolfData-next), web port
8775 and the input port saved on its Relay page. Stop asks the service to shut down cleanly, so an
active session is kept for the next start.
"""

import argparse
import json
import os
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8775
DATABASE = Path(os.environ['USERPROFILE']) / 'GolfData-next' / 'golfdata.sqlite3'


def ready():
    try:
        with urllib.request.urlopen(f'http://localhost:{PORT}/api/health', timeout=1) as response:
            return json.load(response).get('app') in {'TraceLoft', 'GolfData'}
    except (OSError, ValueError):
        return False


def stop():
    if not ready():
        print('TraceLoft-next is not running.')
        return
    urllib.request.urlopen(
        urllib.request.Request(
            f'http://localhost:{PORT}/api/service/stop',
            data=b'{}',
            headers={'Content-Type': 'application/json'},
        )
    ).close()
    for _ in range(100):
        if not ready():
            print('TraceLoft-next stopped.')
            return
        time.sleep(0.1)
    raise SystemExit('TraceLoft-next did not stop within 10 s. See web_service.log.')


def start(open_browser=True):
    if not ready():
        python = ROOT / '.venv' / 'Scripts' / 'python.exe'
        if not python.exists():
            raise SystemExit('Install the web dependencies in .venv first; see README.md.')
        DATABASE.parent.mkdir(exist_ok=True)
        env = dict(os.environ, GOLFDATA_DATABASE=str(DATABASE))
        env.pop('TRACELOFT_INPUT_PORT', None)  # use the input port saved on the Relay page
        with (ROOT / 'web_service.log').open('a', encoding='utf-8') as log:
            child = subprocess.Popen(
                [str(python), '-B', '-u', str(ROOT / 'web_app.py'), '--port', str(PORT)],
                cwd=ROOT,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=log,
                stderr=log,
            )
        for _ in range(150):
            if child.poll() is not None:
                raise SystemExit('TraceLoft-next failed to start. See web_service.log.')
            if ready():
                break
            time.sleep(0.1)
        else:
            raise SystemExit('TraceLoft-next did not become ready. See web_service.log.')
    print(f'TraceLoft-next: http://localhost:{PORT}')
    if open_browser:
        webbrowser.open(f'http://localhost:{PORT}/')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    if args.stop:
        stop()
    else:
        start(not args.no_open)


if __name__ == '__main__':
    main()
