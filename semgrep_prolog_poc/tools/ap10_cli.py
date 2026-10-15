#!/usr/bin/env python3
"""AP10 opt-in reference catalog and mixed-code recognition. AP9 untouched.

learn LABEL PY_FILE FUNCTION: deterministic Semgrep -> existing AP9 reference clause.
scan  PY_FILE: enumerate all stored references and report their matches and
                 shared syntactic loops using SWI-Prolog.

Use .json Semgrep captures in either role for replay without Semgrep.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from reference_pattern import compile_reference, compile_candidates
from ap10_reference_bundle import bundle_references
from typed_ast_codec import strict_load

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / 'out' / 'ap10'
LABEL = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,63}\Z')


def capture(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise ValueError(f'missing source: {source}')
    if source.suffix.lower() != '.py':
        strict_load(source)
        return source
    semgrep = shutil.which('semgrep')
    if not semgrep:
        raise ValueError('semgrep not found: activate ons_ruleskg')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open('w', encoding='utf-8') as handle:
            done = subprocess.run([semgrep, 'show', 'dump-ast', '--json', str(source)],
                                  stdout=handle, stderr=subprocess.PIPE, text=True,
                                  env={**os.environ, 'SEMGREP_SEND_METRICS': 'off'},
                                  timeout=90, check=False)
        if done.returncode:
            raise ValueError('Semgrep returned failure: ' + done.stderr.strip()[-600:])
        strict_load(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def read_catalog(store: Path) -> list[dict]:
    path = store / 'catalog.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('catalog must be a JSON list')
    for item in data:
        if not isinstance(item, dict) or not LABEL.fullmatch(item.get('label', '')):
            raise ValueError('invalid catalog item')
        if item.get('clause') != f"{item['label']}.pl":
            raise ValueError('invalid catalog clause name')
    return data


def learn(store: Path, label: str, source: Path, function: str, ordinal: int) -> None:
    if not LABEL.fullmatch(label):
        raise ValueError('label must be an ASCII identifier (max 64 characters)')
    store.mkdir(parents=True, exist_ok=True)
    catalog = read_catalog(store)
    if any(i['label'] == label for i in catalog):
        raise ValueError(f'label already exists: {label}; references are immutable')
    ast = capture(source, store / f'{label}.json')
    clause = store / f'{label}.pl'
    # Compiler is the ORIGINAL AP9 generator, unchanged. All references use
    # body to maintain concrete function-instance identity during composition.
    meta = compile_reference(ast, label, function, 'body', ordinal, clause)
    catalog.append({'label': label, 'clause': clause.name,
                    'reference_function': function, 'region': 'body', 'ordinal': ordinal,
                    'source': str(source), 'metadata': meta})
    temporary = store / 'catalog.json.tmp'
    temporary.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    temporary.replace(store / 'catalog.json')
    print(f'AP10_LEARNED: {label} from {function}; reference={clause}')


def scan(store: Path, source: Path) -> int:
    catalog = read_catalog(store)
    if not catalog:
        raise ValueError('no references: use RUN_AP10.cmd learn first')
    swipl = shutil.which('swipl')
    if not swipl:
        raise ValueError('swipl not found: set PATH=A:\\swipl\\bin;%PATH%')
    ast = capture(source, store / 'target.json')
    candidate = store / 'target.pl'
    count = compile_candidates(ast, ('body',), candidate)
    print(f'AP10_SCAN: references={len(catalog)} functions={count}', flush=True)
    # Prolog must see ALL reference_pattern/4 clauses from ONE consulted
    # source. Consulting many separate files redefines the predicate and
    # risks losing earlier references. Keep the AP9-generated files intact.
    bundle = bundle_references(
        [(entry['label'], store / entry['clause']) for entry in catalog],
        store / 'all_references.pl')
    cmd = [swipl, '-q', '-f', 'none',
           '-s', str(ROOT / 'prolog' / 'reference_match.pl'),
           '-s', str(ROOT / 'prolog' / 'ap10_threads.pl'),
           '-s', str(bundle),
           '-s', str(candidate), '-g', 'main_ap10', '-t', 'halt']
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=120,
                            check=False)
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        raise ValueError(f'SWI-Prolog execution failed (exit {result.returncode})')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--store', type=Path, default=DEFAULT_STORE)
    sub = ap.add_subparsers(dest='command', required=True)
    learning = sub.add_parser('learn', help='add an immutable reference from new code')
    learning.add_argument('label')
    learning.add_argument('source', type=Path)
    learning.add_argument('function')
    learning.add_argument('--ordinal', type=int, default=0)
    scanning = sub.add_parser('scan', help='find all learned references in mixed code')
    scanning.add_argument('source', type=Path)
    args = ap.parse_args()
    try:
        if args.command == 'learn':
            learn(args.store, args.label, args.source, args.function, args.ordinal)
        else:
            return scan(args.store, args.source)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as exc:
        print(f'AP10 ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
