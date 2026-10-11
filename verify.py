"""Run the backend/browser-helper suites and save a reproducible local report.

This command never contacts the running service. Tests use isolated fixtures;
manual browser/device checks remain a separate part of feature verification.

Node.js is found from --node, then TRACELOFT_NODE, then PATH, then the standard
Windows install folder. A missing required tool is reported as "not run" and the
verification fails rather than silently passing a partial run. The lint suite runs
when ruff (requirements-dev.txt) is installed and is reported but optional otherwise.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STANDARD_NODE = (Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'nodejs' / 'node.exe',)


def find_node(explicit=None, environ=os.environ, which=shutil.which, standard=STANDARD_NODE):
    """Return the first usable Node.js executable, or None."""
    for candidate in (explicit, environ.get('TRACELOFT_NODE')):
        if candidate:
            path = Path(candidate)
            if path.is_file():
                return str(path)
            raise FileNotFoundError(f'Node.js not found at {candidate}.')
    found = which('node')
    if found:
        return found
    return next((str(path) for path in standard if path.is_file()), None)


def find_python(root=ROOT):
    candidates = (root / '.venv/Scripts/python.exe', root / '.venv/bin/python')
    return next((str(path) for path in candidates if path.is_file()), sys.executable)


def git_state(root=ROOT, which=shutil.which):
    """Commit and dirty-tree state; None when git is unavailable."""
    git = which('git')
    if not git:
        return None, None
    revision = subprocess.run([git, 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=False)
    status = subprocess.run([git, 'status', '--porcelain'], cwd=root, capture_output=True, text=True, check=False)
    return (revision.stdout.strip() if revision.returncode == 0 else None,
            bool(status.stdout.strip()) if status.returncode == 0 else None)


def has_ruff(python):
    probe = subprocess.run([python, '-m', 'ruff', '--version'], capture_output=True, check=False)
    return probe.returncode == 0


def plan(python, node, ruff, root=ROOT):
    """Suites to run: name -> (command or None, required, reason when not run)."""
    scripts = [str(path.relative_to(root)) for path in sorted((root / 'tests').glob('*.mjs'))]
    return {
        'python': ([python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], True, None),
        'javascript': ([node, '--test', *scripts] if node else None, True,
                       None if node else 'Node.js not found; pass --node or set TRACELOFT_NODE.'),
        'lint': ([python, '-m', 'ruff', 'check', '.'] if ruff else None, False,
                 None if ruff else 'ruff not installed; see requirements-dev.txt.'),
    }


def passed(suites):
    return all(suite['exit_code'] == 0 for suite in suites.values()
               if suite['required'] or suite['status'] == 'ran')


def main(argv=None):
    # Windows consoles may use cp1252; Node's Unicode test markers must not
    # turn a passing suite into a reporting failure when output is redirected.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output-dir', type=Path, help='Directory for logs/report; defaults outside the repository.')
    parser.add_argument('--node', help='Path to node.exe when it is not on PATH.')
    args = parser.parse_args(argv)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = (args.output_dir or Path(tempfile.gettempdir()) / 'traceloft-verification' / timestamp).resolve()
    output.mkdir(parents=True, exist_ok=True)
    python = find_python()
    try:
        node = find_node(args.node)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    revision, dirty = git_state()
    results = dict(started_at=timestamp, git_revision=revision, working_tree_dirty=dirty, suites={},
                   browser_qa='Separate manual verification required for affected journeys/device layouts.')
    for suite, (command, required, reason) in plan(python, node, has_ruff(python)).items():
        if command is None:
            print(f'{suite} checks not run: {reason}', flush=True)
            results['suites'][suite] = dict(status='not_run', required=required, reason=reason,
                                            exit_code=None)
            continue
        print(f'Running {suite} checks...', flush=True)
        log = output / f'{suite}.log'
        with log.open('w', encoding='utf-8') as handle:
            result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
        results['suites'][suite] = dict(status='ran', required=required, command=command,
                                        exit_code=result.returncode, log=str(log))
        print('\n'.join(log.read_text(encoding='utf-8', errors='replace').splitlines()[-10:]), flush=True)
    results['passed'] = passed(results['suites'])
    report = output / 'report.json'
    report.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'Verification report: {report}', flush=True)
    print('PASSED' if results['passed'] else 'FAILED', flush=True)
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
