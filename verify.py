"""Run the backend/browser-helper suites and save a reproducible local report.

This command never contacts the running service. Tests use isolated fixtures;
manual browser/device checks remain a separate part of feature verification.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    # Windows consoles may use cp1252; Node's Unicode test markers must not
    # turn a passing suite into a reporting failure when output is redirected.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='Directory for logs/report; defaults outside the repository.')
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = (args.output_dir or Path(tempfile.gettempdir()) / 'traceloft-verification' / timestamp).resolve()
    output.mkdir(parents=True, exist_ok=True)
    candidates = (ROOT / '.venv/Scripts/python.exe', ROOT / '.venv/bin/python')
    python = next((str(path) for path in candidates if path.is_file()), sys.executable)
    node = shutil.which('node')
    if not node:
        parser.error('Node.js is required to run the browser-helper/controller tests.')
    commands = {
        'python': [python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        'javascript': [node, '--test', *[str(path.relative_to(ROOT)) for path in sorted((ROOT / 'tests').glob('*.mjs'))]],
    }
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=False)
    status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True, check=False)
    results = dict(started_at=timestamp, git_revision=revision.stdout.strip() if revision.returncode == 0 else None,
                   working_tree_dirty=bool(status.stdout.strip()) if status.returncode == 0 else None,
                   suites={}, browser_qa='Separate manual verification required for affected journeys/device layouts.')
    for suite, command in commands.items():
        print(f'Running {suite} checks...', flush=True)
        log = output / f'{suite}.log'
        with log.open('w', encoding='utf-8') as handle:
            result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
        results['suites'][suite] = dict(command=command, exit_code=result.returncode, log=str(log))
        print('\n'.join(log.read_text(encoding='utf-8', errors='replace').splitlines()[-10:]), flush=True)
    results['passed'] = all(suite['exit_code'] == 0 for suite in results['suites'].values())
    report = output / 'report.json'
    report.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'Verification report: {report}', flush=True)
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
