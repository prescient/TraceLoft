"""Offline migration/restore and local snapshot/export commands for TraceLoft."""
import argparse
import contextlib
import hashlib
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

from storage import ROOT, SCHEMA_VERSION, Store, atomic_json, database_path, digest, import_legacy, inspect_legacy, now


class ServiceLease:
    """One Python service owns a database's shared drill state across processes."""
    def __init__(self, path):
        import os
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.with_suffix('.owner.lock').open('a+b')
        self.handle.seek(0)
        if os.fstat(self.handle.fileno()).st_size == 0:
            self.handle.write(b'1')
            self.handle.flush()
        try:
            self.handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            raise OSError('Another TraceLoft service owns this database. Stop it before migrating or starting another owner.') from exc

    def close(self):
        self.handle.close()


def preserve_legacy(root, directory):
    """Verified source archive before cutover; training crops retain their own backups."""
    root, directory = Path(root), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ('legacy-' + now().replace(':','').replace('.','') + '.zip')
    inventory = inspect_legacy(root)
    paths = [Path(item['path']) for item in inventory]
    paths += sorted(root.glob('config*.json')) + sorted(root.glob('glyphs*.npz'))
    manifest = {}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            content = path.read_bytes()
            name = path.relative_to(root).as_posix()
            manifest[name] = dict(sha256=digest(content),bytes=len(content))
            archive.writestr(name,content)
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as archive:
        for name,item in manifest.items():
            if digest(archive.read(name)) != item['sha256']:
                raise OSError('Legacy archive verification failed.')
    return target


def restore_snapshot(snapshot, target):
    """Restore only to a new destination; never replace the running database."""
    snapshot, target = Path(snapshot), Path(target)
    manifest = json.loads(snapshot.with_suffix('.manifest.json').read_text('utf-8'))
    if digest(snapshot.read_bytes()) != manifest['sha256']:
        raise ValueError('Backup checksum does not match its manifest.')
    if manifest['schema'] != SCHEMA_VERSION:
        raise ValueError('Use the matching application version for this backup.')
    with contextlib.closing(sqlite3.connect(f'{snapshot.resolve().as_uri()}?mode=ro',uri=True)) as source:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or source.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Backup integrity check failed.')
        if source.execute('PRAGMA user_version').fetchone()[0] != manifest['schema']:
            raise ValueError('Backup schema does not match the manifest.')
        for table,count in manifest['counts'].items():
            if table not in ('shots','ingest_events','sessions','session_attempts'):
                raise ValueError('Unknown backup count field.')
            if source.execute(f'SELECT count(*) FROM {table}').fetchone()[0] != count:
                raise ValueError('Backup reconciliation failed.')
    target.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation protects existing data, including a destination created during validation.
    with target.open('xb') as destination, snapshot.open('rb') as source:
        shutil.copyfileobj(source,destination)
        destination.flush()
        import os
        os.fsync(destination.fileno())
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('migrate','backup','export','restore'))
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--database',type=Path,default=None)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--snapshot',type=Path)
    args = parser.parse_args()
    path = args.database or database_path()
    if args.command == 'migrate' and args.dry_run:
        print(json.dumps(dict(dry_run=True,files=inspect_legacy(args.root)),indent=2))
        return
    if args.command == 'restore':
        if not args.snapshot or not args.output:
            parser.error('restore needs --snapshot and a new --output destination')
        print(restore_snapshot(args.snapshot,args.output))
        return
    if args.command != 'migrate' and not path.exists():
        parser.error('Database does not exist; migrate first.')
    lease = ServiceLease(path) if args.command == 'migrate' else None
    store = None
    try:
        if args.command == 'migrate':
            from web_service import desktop_capture_running
            if desktop_capture_running():
                raise OSError('Stop desktop capture before migrating.')
            archive = preserve_legacy(args.root,path.parent/'backups')
        store = Store(path)
        if args.command == 'migrate':
            report = import_legacy(store,args.root)
            report['legacy_archive'] = str(archive)
            report['sqlite_snapshot'] = str(store.backup())
            atomic_json(path.parent/'migration-report.json',report)
            print(json.dumps(report,indent=2))
        elif args.command == 'backup':
            print(store.backup(args.output))
        else:
            target = args.output or path.parent/'traceloft-export.zip'
            target.write_bytes(store.export())
            print(target)
    finally:
        if store:
            store.close()
        if lease:
            lease.close()


if __name__ == '__main__':
    main()
