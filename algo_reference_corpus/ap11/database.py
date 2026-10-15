"""SQLite knowledge catalog. Transactional metadata; generated Prolog kept as files."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = '''
CREATE TABLE IF NOT EXISTS reference (
 label TEXT PRIMARY KEY,
 language TEXT NOT NULL,
 repository TEXT NOT NULL,
 git_commit TEXT NOT NULL,
 category TEXT NOT NULL,
 relative_path TEXT NOT NULL,
 function_name TEXT NOT NULL,
 function_path TEXT NOT NULL DEFAULT '',
 region TEXT NOT NULL DEFAULT 'body',
 ordinal INTEGER NOT NULL DEFAULT 0,
 source_sha256 TEXT NOT NULL DEFAULT '',
 ast_sha256 TEXT NOT NULL DEFAULT '',
 pattern_sha256 TEXT NOT NULL DEFAULT '',
 structural_sha256 TEXT NOT NULL DEFAULT '',
 clause_path TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL CHECK(status IN ('generated','skipped','error')),
 review_status TEXT NOT NULL DEFAULT 'unreviewed'
   CHECK(review_status IN ('unreviewed','approved','rejected')),
 reason TEXT NOT NULL DEFAULT '',
 UNIQUE(language, repository, git_commit, relative_path, function_name, region, ordinal)
);
CREATE INDEX IF NOT EXISTS ix_reference_category ON reference(category, status, review_status);
CREATE INDEX IF NOT EXISTS ix_reference_structure ON reference(structural_sha256);
'''


@contextmanager
def connect(store: Path) -> Iterator[sqlite3.Connection]:
    """Open a transaction AND close the SQLite handle on every exit path.

    sqlite3.Connection's own ``with`` only commits/rolls back: it does not
    close the handle. On Windows this leaves references.sqlite3 locked when
    TemporaryDirectory tries to remove the store. All AP11 callers already
    use ``with connect(store) as db`` and therefore need no other changes.
    """
    store.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(store / 'references.sqlite3', timeout=20)
    try:
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        with conn:
            yield conn
    finally:
        conn.close()


def add(conn: sqlite3.Connection, row: dict) -> bool:
    """Append immutable row; exact replay is harmless, conflicting replay fails."""
    existing = conn.execute('SELECT * FROM reference WHERE label=?', (row['label'],)).fetchone()
    if existing:
        if dict(existing) != row:
            # Review may have been updated separately and must not be undone.
            adjusted = dict(existing)
            adjusted['review_status'] = row['review_status']
            if adjusted != row:
                raise ValueError('immutable reference identity changed: ' + row['label'])
        return False
    names = tuple(row)
    sql = ('INSERT INTO reference (' + ','.join(names) + ') VALUES ('
           + ','.join('?' for _ in names) + ')')
    with conn:
        conn.execute(sql, tuple(row[n] for n in names))
    return True


def get(conn: sqlite3.Connection, label: str):
    return conn.execute('SELECT * FROM reference WHERE label=?', (label,)).fetchone()


def approve(conn: sqlite3.Connection, label: str, action: str) -> bool:
    if action not in ('approved', 'rejected'):
        raise ValueError('review status must be approved or rejected')
    row = get(conn, label)
    if row is None or row['status'] != 'generated':
        raise ValueError('cannot review missing or ungenerated label: ' + label)
    with conn:
        conn.execute('UPDATE reference SET review_status=? WHERE label=?', (action, label))
    return True


def summary(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute('''
      SELECT category, status, review_status, count(*) AS count
      FROM reference GROUP BY category, status, review_status
      ORDER BY category, status, review_status''')]
