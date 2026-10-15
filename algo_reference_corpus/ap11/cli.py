"""AP11 standalone CLI; operate from its sibling directory, never from frozen AP10."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bridge import frozen_root
from .database import approve, connect, summary
from .ingest import ingest
from .recognize import scan
from .source import DEFAULT_CATEGORIES, revision

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / 'store'
DEFAULT_CORPUS = ROOT / 'TheAlgorithms_Python'


def safe_store(store: Path, frozen: Path):
    dest = store.resolve()
    frozen = frozen.resolve()
    if dest == frozen or frozen in dest.parents:
        raise ValueError('AP11 store must NEVER be inside frozen AP10')
    if ROOT.resolve() not in (dest, *dest.parents):
        raise ValueError('AP11 store must stay under the new algo_reference_corpus folder')
    return dest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=DEFAULT_STORE)
    parser.add_argument('--ap10-root', type=Path, default=frozen_root())
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status', help='list SQLite ingestion and review counts')
    source = sub.add_parser('revision', help='show pinned local upstream commit')
    source.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    load = sub.add_parser('ingest', help='compile up to N corpus functions with frozen AP9')
    load.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    load.add_argument('--categories', nargs='+', default=list(DEFAULT_CATEGORIES))
    load.add_argument('--limit', type=int, default=30)
    load.add_argument('--max-source-kib', type=int, default=128)
    review = sub.add_parser('review', help='explicitly approve/reject a candidate identity')
    review.add_argument('label')
    review.add_argument('action', choices=('approved', 'rejected'))
    recognize = sub.add_parser('scan', help='recognize unknown source via frozen AP10')
    recognize.add_argument('source', type=Path)
    recognize.add_argument('--category')
    recognize.add_argument('--label', help='search one exact stored reference')
    recognize.add_argument('--include-unreviewed', action='store_true')
    recognize.add_argument('--limit', type=int, default=30)
    args = parser.parse_args(argv)
    try:
        store = safe_store(args.store, args.ap10_root)
        if args.command == 'revision':
            print('AP11_CORPUS_COMMIT:', revision(args.corpus))
        elif args.command == 'ingest':
            output = ingest(args.corpus, store, tuple(args.categories), args.limit,
                            args.max_source_kib, frozen=args.ap10_root)
            print('AP11_INGEST_REPORT:\n' + json.dumps(output, indent=2))
        elif args.command == 'status':
            with connect(store) as db:
                print('AP11_DATABASE:', store / 'references.sqlite3')
                print(json.dumps(summary(db), indent=2))
                for ref in db.execute('''SELECT label,category,relative_path,function_name,review_status
                                         FROM reference WHERE status='generated'
                                         ORDER BY category,relative_path LIMIT 40'''):
                    print('AP11_REFERENCE:', ' | '.join(str(x) for x in ref))
        elif args.command == 'review':
            with connect(store) as db:
                approve(db, args.label, args.action)
            print(f'AP11_REVIEWED: {args.label} -> {args.action}')
        elif args.command == 'scan':
            print(scan(store, args.source, args.category,
                       args.include_unreviewed, args.limit, args.ap10_root, args.label), end='')
        return 0
    except (OSError, ValueError, TypeError, TimeoutError) as exc:
        print(f'AP11_ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
