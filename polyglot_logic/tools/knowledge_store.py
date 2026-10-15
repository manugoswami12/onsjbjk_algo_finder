"""AP13 knowledge storage: learned reference clauses (.pl) + SQLite catalog.

The AP11 catalog is opened strictly read-only (sqlite URI mode=ro).
"""
from __future__ import annotations

import functools
import hashlib
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from env_run import REPO, ROOT

DEFAULT_STORE = ROOT / 'store'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS pattern (
 label TEXT PRIMARY KEY,
 language TEXT NOT NULL,
 source_path TEXT NOT NULL,
 function_name TEXT NOT NULL,
 branch TEXT NOT NULL,
 relations INTEGER NOT NULL,
 clause_path TEXT NOT NULL,
 pattern_sha256 TEXT NOT NULL,
 origin TEXT NOT NULL,
 ap11_label TEXT NOT NULL DEFAULT '',
 category TEXT NOT NULL DEFAULT '',
 review_status TEXT NOT NULL DEFAULT 'unreviewed'
   CHECK(review_status IN ('unreviewed','approved','rejected')),
 quality TEXT NOT NULL DEFAULT 'usable',
 grp TEXT NOT NULL DEFAULT '',
 also_source TEXT NOT NULL DEFAULT '',
 corpus_matches TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attempt (
 label TEXT PRIMARY KEY,
 status TEXT NOT NULL,
 reason TEXT NOT NULL DEFAULT ''
);
'''


@contextmanager
def connect(store: Path):
    """Commit/rollback and ALWAYS close (the AP11 Windows WinError 32 lesson)."""
    store.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(store / 'polyglot.sqlite3', timeout=20)
    try:
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        cols = {r[1] for r in conn.execute('PRAGMA table_info(pattern)')}
        for col, decl in (('quality', "TEXT NOT NULL DEFAULT 'usable'"), ('grp', "TEXT NOT NULL DEFAULT ''"),
                          ('also_source', "TEXT NOT NULL DEFAULT ''"),
                          ('corpus_matches', "TEXT NOT NULL DEFAULT ''")):
            if col not in cols:  # v1 catalogs gain the v2 columns, nothing is rewritten
                conn.execute(f'ALTER TABLE pattern ADD COLUMN {col} {decl}')
        with conn:
            yield conn
    finally:
        conn.close()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(store: Path, row: dict, clause: str) -> str:
    """Immutable: identical replay is 'already_present', a different clause is an error."""
    data = clause.encode('utf-8')
    digest = sha256(data)
    target = store / 'patterns' / (row['label'] + '.pl')
    with connect(store) as db:
        old = db.execute('SELECT pattern_sha256 FROM pattern WHERE label=?', (row['label'],)).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError('learned reference changed for existing label: ' + row['label'])
            return 'already_present'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        structure = clause.split(',', 1)[1] if ',' in clause else clause  # label removed
        row = dict(row, clause_path='patterns/' + target.name, pattern_sha256=digest,
                   grp=row.get('grp') or sha256(structure.encode('utf-8'))[:16])
        names = tuple(row)
        db.execute('INSERT INTO pattern (' + ','.join(names) + ') VALUES (' + ','.join('?' * len(names)) + ')',
                   tuple(row[n] for n in names))
        db.execute('INSERT OR REPLACE INTO attempt VALUES (?,?,?)', (row['label'], 'generated', ''))
    return 'generated'


def record_attempt(store: Path, label: str, status: str, reason: str = ''):
    with connect(store) as db:
        db.execute('INSERT OR REPLACE INTO attempt VALUES (?,?,?)', (label, status, reason[:600]))


def reference_files(store: Path, include_unreviewed: bool, branches=None,
                    qualities=('usable',)) -> list[Path]:
    if not (store / 'polyglot.sqlite3').is_file():
        return []
    with connect(store) as db:
        rows = db.execute('SELECT * FROM pattern').fetchall()
    out = []
    for r in rows:
        if r['review_status'] == 'rejected' or r['quality'] not in qualities:
            continue
        if r['review_status'] == 'unreviewed' and not include_unreviewed:
            continue
        path = store / r['clause_path']
        if not path.is_file() or sha256(path.read_bytes()) != r['pattern_sha256']:
            raise ValueError('missing or corrupted learned reference: ' + r['label'])
        out.append(path)
    return out


def metadata(store: Path) -> dict:
    if not (store / 'polyglot.sqlite3').is_file():
        return {}
    with connect(store) as db:
        return {r['label']: dict(r) for r in db.execute('SELECT * FROM pattern')}


def set_quality(store: Path, updates: dict):
    """label -> (quality, corpus_matches text). Only the validation columns change."""
    with connect(store) as db:
        for label, (quality, matches) in updates.items():
            db.execute('UPDATE pattern SET quality=?, corpus_matches=? WHERE label=?', (quality, matches, label))


def approve(store: Path, label: str, action: str):
    if action not in ('approved', 'rejected', 'unreviewed'):
        raise ValueError('review status must be approved, rejected or unreviewed')
    with connect(store) as db:
        if not db.execute('SELECT 1 FROM pattern WHERE label=?', (label,)).fetchone():
            raise ValueError('unknown label: ' + label)
        db.execute('UPDATE pattern SET review_status=? WHERE label=?', (action, label))


def status(store: Path) -> list[dict]:
    if not (store / 'polyglot.sqlite3').is_file():
        return []
    with connect(store) as db:
        rows = [dict(r) for r in db.execute(
            'SELECT branch, quality, review_status, count(*) AS count FROM pattern '
            'GROUP BY branch, quality, review_status')]
        rows += [dict(r) for r in db.execute(
            "SELECT 'attempts' AS kind, status, count(*) AS count FROM attempt GROUP BY status")]
    return rows


# ----- AP11 catalog, read-only ------------------------------------------------
def ap11_rows(ap11_store: Path, categories: tuple[str, ...], limit: int):
    db_path = ap11_store / 'references.sqlite3'
    if not db_path.is_file():
        raise ValueError(f'AP11 catalog not found: {db_path}')
    conn = sqlite3.connect(f'file:{db_path.as_posix()}?mode=ro', uri=True, timeout=20)
    try:
        conn.row_factory = sqlite3.Row
        sql = "SELECT label, category, relative_path, function_name FROM reference WHERE status='generated'"
        args = []
        if categories:
            sql += ' AND category IN (' + ','.join('?' * len(categories)) + ')'
            args += list(categories)
        sql += ' ORDER BY category, relative_path, function_name LIMIT ?'
        return [dict(r) for r in conn.execute(sql, args + [limit])]
    finally:
        conn.close()


def ap11_source_path(corpus: Path, relative: str) -> Path:
    """Reuse AP11's traversal/symlink-safe path check, unchanged."""
    root = str(REPO / 'algo_reference_corpus')
    if root not in sys.path:
        sys.path.insert(0, root)
    from ap11.source import source_path
    return source_path(corpus.resolve(), relative)


# ----- sound prefilter (inverted-index style) -------------------------------------
_OP = re.compile(r"'?op'?\('?([a-z_]+)'?,")
_CALL = re.compile(r"'?call'?\('?([^',\[\]()]+)'?,")
COMPARE = {'gt', 'ge', 'lt', 'le', 'eq', 'ne', 'not'}


def _features(text: str) -> frozenset:
    ops = set(_OP.findall(text))
    calls = {c for c in _CALL.findall(text) if c != '$self' and not c[:1].isupper() and c[:1] != '_'}
    return frozenset({'op:' + o for o in ops} | {'call:' + c for c in calls})


def fact_features(facts: str) -> frozenset:
    """Operators/calls a candidate can offer after canonicalisation (canon.pl)."""
    f = set(_features(facts))
    if any('op:' + o in f for o in COMPARE):          # direction / negation normalisation
        f |= {'op:' + o for o in COMPARE}
    if 'op:shr' in f:                                  # (lo + hi) >>> 1 -> div
        f.add('op:div')
    if f & {'op:add', 'op:sub'}:                       # index shift: swap(i-1, i) == swap(j, j+1)
        f |= {'op:add', 'op:sub'}
    return frozenset(f)


@functools.lru_cache(maxsize=None)
def ref_features(path: Path) -> frozenset:
    """Operators/calls a learned reference requires (variables never count)."""
    return _features(path.read_text(encoding='utf-8'))
