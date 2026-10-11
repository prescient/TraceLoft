"""All-or-nothing import of pre-SQLite CSV/JSON files, preserving exact source evidence."""

import csv
import io
import json
import math
import re
from pathlib import Path

from storage import FIELDS, digest, encoded, identity, now


def legacy_files(root):
    root = Path(root)
    return (
        sorted(root.glob('shots*.csv'))
        + sorted((root / 'practice_sessions').glob('*.json'))
        + sorted((root / 'practice_sessions' / '.trash').glob('*.json'))
    )


def inspect_legacy(root):
    files = []
    for path in legacy_files(root):
        content = path.read_bytes()
        if path.suffix == '.csv':
            count = len(list(csv.DictReader(io.StringIO(content.decode('utf-8-sig')))))
        else:
            data = json.loads(content.decode('utf-8-sig'))
            count = len(data['shots'])
            if data['id'] != path.stem or not re.fullmatch('[0-9a-f]{32}', path.stem):
                raise ValueError(f'Invalid session identity in {path.name}.')
        files.append(
            dict(path=str(path.resolve()), sha256=digest(content), rows=count, bytes=len(content))
        )
    return files


def import_legacy(store, root):
    """All-or-nothing, exact-file evidence, repeat-safe import. Originals never rewritten."""
    inventory = inspect_legacy(root)
    before = {t: store.count(t) for t in ('ingest_events', 'shots', 'sessions', 'session_attempts')}
    with store.transaction():
        seen_csv = {
            r[0]
            for r in store.connection.execute(
                "SELECT hash FROM import_files WHERE path LIKE '%.csv'"
            )
        }
        for item in inventory:
            path = Path(item['path'])
            content = path.read_bytes()
            if digest(content) != item['sha256']:
                raise OSError('Legacy data changed during import; retry after stopping capture.')
            file_id = identity('file:' + str(path) + ':' + item['sha256'])
            existing = store.connection.execute(
                'SELECT 1 FROM import_files WHERE id=?', (file_id,)
            ).fetchone()
            if existing:
                continue
            # Changed originals are not silently imported a second time.
            if store.connection.execute(
                'SELECT 1 FROM import_files WHERE path=?', (str(path),)
            ).fetchone():
                raise ValueError(
                    f'{path.name} changed after import; reconcile before importing again.'
                )
            store.connection.execute(
                'INSERT INTO import_files VALUES(?,?,?,?,?)',
                (file_id, str(path), item['sha256'], content, now()),
            )
            if path.suffix == '.csv':
                if item['sha256'] in seen_csv:
                    continue
                seen_csv.add(item['sha256'])
                for ordinal, row in enumerate(
                    csv.DictReader(io.StringIO(content.decode('utf-8-sig'))), 1
                ):
                    vals = {}
                    for key in FIELDS:
                        raw = row.get(key)
                        try:
                            value = float(raw) if raw not in ('', None) else None
                            vals[key] = value if value is None or math.isfinite(value) else raw
                        except (ValueError, TypeError):
                            vals[key] = raw
                    note = row.get('note', '')
                    accepted = bool(re.match(r'^ok(?: \(no GSPro\))?(?:;|$)', note))
                    result = (
                        ('sent' if row.get('sent', '').lower() == 'true' else 'validated')
                        if accepted
                        else 'unknown'
                    )
                    event = dict(
                        session_id=row.get('session_id'),
                        seq=row.get('seq'),
                        source_time=row.get('time'),
                        club=row.get('club'),
                        vals=vals,
                        note=note,
                        result=result,
                        legacy_row=row,
                        sent_fields={k: v for k, v in row.items() if k.startswith('sent_')},
                    )
                    store.ingest(
                        event,
                        identity('csv:' + file_id + ':' + str(ordinal)),
                        'legacy_csv',
                        file_id,
                        ordinal,
                    )
            else:
                data = json.loads(content.decode('utf-8-sig'))
                store.save_session(data, imported=True, deleted=path.parent.name == '.trash')
        after = {t: store.count(t) for t in before}
        report = dict(
            created=now(),
            files=inventory,
            before=before,
            after=after,
            added={t: after[t] - before[t] for t in before},
            caveats=[
                'CSV acceptance requires explicit ok note or unique confirmed practice evidence.',
                'Unresolved colliding legacy keys remain separate shots/observations.',
                'Legacy CSV local timestamps have unknown timezone; original evidence is embedded.',
            ],
        )
        store.connection.execute(
            "INSERT OR REPLACE INTO metadata VALUES('legacy_import_complete',?)", (encoded(report),)
        )
        store.audit('database', 'legacy_import', report)
    return report
