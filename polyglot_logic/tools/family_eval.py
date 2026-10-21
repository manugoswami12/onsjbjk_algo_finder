#!/usr/bin/env python3
"""AP13 v3 held-out FAMILY-level evaluation (doc 08) on the same frozen Rosetta files
as rosetta_eval.py, against benchmark/rosetta_family_truth.json (written before the
first family run). The exact level stays in rosetta_eval.py; the two are never mixed.

Per file, all deepest family paths of all its functions are collected:
  exact    - a path equals an accepted path
  broader  - no exact path, a path is a proper prefix of an accepted path (true, less specific)
  wrong    - no path agrees with any accepted path
  none     - no family at all
strict precision counts a file only if EVERY returned path agrees (prefix or equal).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_run import ROOT, ToolError  # noqa: E402
from family_scan import answers as families  # noqa: E402  (one answer per file, doc 09)
from rosetta_eval import files  # noqa: E402

TRUTH = ROOT / 'benchmark' / 'rosetta_family_truth.json'


def split_of(task, lang, f):
    """Deterministic dev/test split by the file's Rosetta-relative path."""
    import hashlib
    h = hashlib.sha256(f'{task}/{lang}/{f.name}'.encode()).digest()[0]
    return 'dev' if h % 2 == 0 else 'test'


def agrees(path, accepted):
    return any(a[:len(path)] == path for a in accepted)


def grade(paths, accepted):
    if not paths:
        return 'none', False
    exact = any(p in accepted for p in paths)
    ok = [agrees(p, accepted) for p in paths]
    if exact:
        return 'exact', all(ok)
    if any(ok):
        return 'broader', all(ok)
    return 'wrong', False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rosetta', type=Path, default=ROOT / 'store' / 'rosetta')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--split', choices=('all', 'dev', 'test'), default='all',
                    help='dev = files whose path hash is even (inspected while tuning); test = odd (never inspected)')
    a = ap.parse_args()
    truth = json.loads(TRUTH.read_text(encoding='utf-8'))['tasks']
    jobs = [(task, lang, f) for task in truth for lang, f in files(a.rosetta, task)
            if a.split == 'all' or (split_of(task, lang, f) == a.split)]

    def run(job):
        try:
            return families(job[2]), None
        except (ToolError, ValueError, OSError, RecursionError) as exc:
            return None, str(exc)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        results = list(pool.map(run, jobs))
    stats = defaultdict(lambda: defaultdict(int))
    for (task, lang, f), (fam, err) in zip(jobs, results):
        keys = ('ALL', 'lang:' + lang, 'task:' + task)
        for k in keys:
            stats[k]['files'] += 1
        if err:
            for k in keys:
                stats[k]['error'] += 1
            print(f'ERROR|{task}|{lang}|{f.name}|{err[:150]}')
            continue
        paths = sorted({tuple(p) for ps in fam.values() for p in ps})
        outcome, all_ok = grade([list(p) for p in paths], truth[task])
        for k in keys:
            stats[k][outcome] += 1
            stats[k]['strict_ok'] += all_ok
            stats[k]['paths'] += len(paths)
        print(f"{task}|{lang}|{f.name}|{outcome}|{'strict' if all_ok else ''}|"
              + ' ; '.join('>'.join(p) for p in paths))

    def row(k):
        s = stats[k]
        ans = s['exact'] + s['broader'] + s['wrong']
        return (f"{k:44s} files={s['files']:4d} exact={s['exact']:3d} broader={s['broader']:3d} "
                f"wrong={s['wrong']:3d} none={s['none']:4d} errors={s['error']:2d} "
                f"strict_ok={s['strict_ok']:3d} paths/answer={s['paths'] / max(ans, 1):.2f}")
    print('\n=== AP13 v3 HELD-OUT FAMILY RESULTS ===')
    for k in ['ALL'] + sorted(k for k in stats if k.startswith('lang:')) + \
            sorted(k for k in stats if k.startswith('task:')):
        print(row(k))
    s = stats['ALL']
    ans = s['exact'] + s['broader'] + s['wrong']
    print(f"\nFAMILY PRECISION strict (every path agrees / answered) = {s['strict_ok']}/{ans}"
          f" = {s['strict_ok'] / max(ans, 1):.1%}")
    print(f"FAMILY PRECISION lenient (some path agrees / answered) = {s['exact'] + s['broader']}/{ans}"
          f" = {(s['exact'] + s['broader']) / max(ans, 1):.1%}")
    print(f"FAMILY RECALL (some path agrees / files) = {s['exact'] + s['broader']}/{s['files']}"
          f" = {(s['exact'] + s['broader']) / max(s['files'], 1):.1%}"
          f"   of which leaf-exact = {s['exact']}")
    print('Family answers are candidate categories, never algorithm identity (doc 08).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
