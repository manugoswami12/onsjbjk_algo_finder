"""Independent AP12 SQLite ledger and Prolog fact artifacts (never alter AP11 tables)."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3

SCHEMA = '''
CREATE TABLE IF NOT EXISTS source_file (
 git_commit TEXT NOT NULL, relative_path TEXT NOT NULL,
 source_sha256 TEXT NOT NULL, exact_status TEXT NOT NULL,
 exact_count INTEGER NOT NULL, fallback_status TEXT NOT NULL,
 fact_path TEXT NOT NULL DEFAULT '', fact_sha256 TEXT NOT NULL DEFAULT '',
 error TEXT NOT NULL DEFAULT '', PRIMARY KEY(git_commit,relative_path)
);
CREATE TABLE IF NOT EXISTS observation (
 git_commit TEXT NOT NULL, relative_path TEXT NOT NULL, ordinal INTEGER NOT NULL,
 function_name TEXT NOT NULL, candidate_routes_json TEXT NOT NULL,
 evidence_json TEXT NOT NULL, limitations_json TEXT NOT NULL,
 PRIMARY KEY(git_commit,relative_path,ordinal),
 FOREIGN KEY(git_commit,relative_path) REFERENCES source_file(git_commit,relative_path)
);
CREATE INDEX IF NOT EXISTS ix_ap12_route ON observation(git_commit,relative_path);
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextmanager
def db_open(store: Path):
    store.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(store / 'ap12_fallback.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(SCHEMA)
        with db:
            yield db
    finally:
        db.close()


def fact_filename(relative: str, commit: str) -> str:
    return digest((commit + '\0' + relative).encode('utf8')) + '.pl'


def validated_file(store: Path, row) -> None:
    if not row['fact_path']:
        if row['fact_sha256']:
            raise ValueError('fact hash with no path: ' + row['relative_path'])
        return
    path = store / row['fact_path']
    if not path.resolve().is_relative_to((store / 'ap12_facts').resolve()):
        raise ValueError('AP12 facts path leaves trusted directory')
    if not path.is_file() or digest(path.read_bytes()) != row['fact_sha256']:
        raise ValueError('AP12 facts missing or modified: ' + row['relative_path'])


def save(store: Path, commit: str, relative: str, source_hash: str,
         exact_status: str, exact_count: int, fallback_status: str,
         facts: str, observations: list[dict], error: str = ''):
    """Write facts once, then commit the file and its function observations atomically."""
    parent = store / 'ap12_facts'
    parent.mkdir(parents=True, exist_ok=True)
    fact_path = 'ap12_facts/' + fact_filename(relative, commit) if facts else ''
    fact_hash = digest(facts.encode('utf8')) if facts else ''
    if facts:
        target = store / fact_path
        data = facts.encode('utf8')
        if target.exists():
            if digest(target.read_bytes()) != fact_hash:
                raise ValueError('conflicting immutable fallback facts: ' + relative)
        else:
            temporary = target.with_suffix('.pl.tmp')
            temporary.write_bytes(data)
            temporary.replace(target)
    row = dict(git_commit=commit,relative_path=relative,source_sha256=source_hash,
               exact_status=exact_status,exact_count=exact_count,
               fallback_status=fallback_status,fact_path=fact_path,
               fact_sha256=fact_hash,error=error[:1200])
    with db_open(store) as db:
        existing = db.execute('SELECT * FROM source_file WHERE git_commit=? AND relative_path=?',
                              (commit,relative)).fetchone()
        if existing:
            if dict(existing) != row:
                raise ValueError('immutable AP12 file row differs: ' + relative)
            validated_file(store, existing)
            old_observations = [dict(x) for x in db.execute(
                'SELECT * FROM observation WHERE git_commit=? AND relative_path=? ORDER BY ordinal',
                (commit,relative))]
            wanted = [observation_row(commit,relative,j,o) for j,o in enumerate(observations,1)]
            if old_observations != wanted:
                raise ValueError('immutable AP12 observation rows differ: ' + relative)
            return
        db.execute('INSERT INTO source_file VALUES (?,?,?,?,?,?,?,?,?)',tuple(row.values()))
        for j, observation in enumerate(observations, 1):
            item = observation_row(commit,relative,j,observation)
            db.execute('INSERT INTO observation VALUES (?,?,?,?,?,?,?)', tuple(item.values()))


def observation_row(commit, relative, j, ob):
    return dict(git_commit=commit,relative_path=relative,ordinal=j,
                function_name=ob['function'],
                candidate_routes_json=json.dumps(ob['routes'],sort_keys=True),
                evidence_json=json.dumps(ob['evidence'],sort_keys=True),
                limitations_json=json.dumps(ob['limitations'],sort_keys=True))
