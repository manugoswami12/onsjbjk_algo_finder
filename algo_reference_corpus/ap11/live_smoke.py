"""Live Windows proof that an imported real reference is loadable and matchable."""
from __future__ import annotations

from pathlib import Path
import sys

from .cli import DEFAULT_CORPUS, DEFAULT_STORE
from .database import connect
from .recognize import scan
from .source import source_path


def main() -> int:
    with connect(DEFAULT_STORE) as conn:
        row = conn.execute("""SELECT * FROM reference WHERE status='generated'
                              ORDER BY category, relative_path, label LIMIT 1""").fetchone()
        if row is None:
            print('AP11_LIVE_ERROR: no generated references', file=sys.stderr)
            return 2
        src = source_path(DEFAULT_CORPUS, row['relative_path'])
        label = row['label']
    report = scan(DEFAULT_STORE, src, include_unreviewed=True, limit=1, label=label)
    print(report)
    if ('AP10_THREAD: ' + label) not in report:
        print('AP11_LIVE_ERROR: source-to-Prolog round-trip gave no self match', file=sys.stderr)
        return 2
    print('AP11 LIVE INGEST->SCAN SMOKE PASS (self match; NOT generalization).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
