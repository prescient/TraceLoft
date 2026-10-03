"""Start/reuse the background web service, then open its local interface."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ready(port):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=1) as response:
            return json.load(response).get("app") in {"TraceLoft", "GolfData"}
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--resume-session", help=argparse.SUPPRESS)
    args = parser.parse_args()
    runtime_path = ROOT / "web_runtime.json"
    try:
        runtime = json.loads(runtime_path.read_text())
    except (OSError, ValueError):
        runtime = None
    live = runtime and ready(runtime["port"])
    if args.stop:
        if live:
            base = f"http://localhost:{runtime['port']}"
            urllib.request.urlopen(urllib.request.Request(base + "/api/service/stop", data=b"{}", headers={"Content-Type": "application/json"})).close()
        return
    if live and args.lan and not runtime["lan"]:
        raise SystemExit("The local service is running. Use Stop TraceLoft Web, then launch Web LAN.")
    if not live:
        if ready(8765):
            raise SystemExit("Port 8765 is already in use. Check the existing service before starting another.")
        python = ROOT / ".venv" / "Scripts" / "python.exe"
        if not python.exists():
            raise SystemExit("Install the web dependencies in .venv first; see README.md.")
        with (ROOT / "web_service.log").open("a", encoding="utf-8") as log:
            child = subprocess.Popen([str(python), "-B", "-u", str(ROOT / "web_app.py"), *(["--lan"] if args.lan else []),
                *(["--resume-session", args.resume_session] if args.resume_session else [])],
                cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW, stdout=log, stderr=log)
        for _ in range(100):
            if child.poll() is not None:
                raise SystemExit("Web service failed to start. See web_service.log.")
            if ready(8765):
                runtime = json.loads(runtime_path.read_text())
                break
            time.sleep(.1)
        else:
            raise SystemExit("Web service did not become ready. See web_service.log.")
    print(f"TraceLoft web: http://localhost:{runtime['port']}")
    if not args.no_open:
        webbrowser.open(f"http://localhost:{runtime['port']}/")


if __name__ == "__main__":
    main()
