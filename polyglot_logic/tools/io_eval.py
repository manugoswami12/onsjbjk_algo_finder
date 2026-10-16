#!/usr/bin/env python3
"""AP13 v4 held-out evaluation of the RECALL engine (doc 10), separate from the
precision/coverage system (docs 07-09), on the same frozen Rosetta files and split.

Per file, every function is run as its Prolog normal form on the fixed battery and
compared with the behaviour catalog (io_catalog.py):
  SAME_LOGIC     equal logic traces + equal outputs  -> algorithm level
  SAME_FUNCTION  equal outputs only                  -> function (task) level
graded against benchmark/rosetta_truth.json (frozen): correct when a matching reference's
file is a ground-truth file of the task.
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
from io_catalog import compare, describe  # noqa: E402
from io_trace import run_functions  # noqa: E402

LANGS_RUN = {'Python', 'Rust', 'Java', 'C', 'R', 'Prolog', 'Common-Lisp'}   # PNF translator, or native (Prolog)


def file_answer(path: Path, cat: dict, by_sig: dict):
    try:
        me = describe(run_functions(path))
    except (ToolError, ValueError, OSError, RecursionError, KeyError, IndexError, TypeError,
            AttributeError, StopIteration) as exc:
        return {'outcome': 'ERROR', 'reason': str(exc)[:120]}
    logic, io = set(), set()
    ran = 0
    for name, d in me.items():
        ran += 1
        if not d['discriminative']:
            continue
        for ref in by_sig.get(tuple(d['sig']), []):
            c = compare(d, cat[ref])
            if c == 'logic':
                logic.add(ref)
            elif c == 'io':
                io.add(ref)
    if logic:
        return {'outcome': 'SAME_LOGIC', 'refs': sorted(logic)}
    if io:
        return {'outcome': 'SAME_FUNCTION', 'refs': sorted(io)}
    return {'outcome': 'NO_MATCH' if ran else 'NOT_RUNNABLE'}


def main() -> int:
    from family_eval import split_of
    from rosetta_eval import files
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rosetta', type=Path, required=True)
    ap.add_argument('--catalog', type=Path, required=True)
    ap.add_argument('--split', choices=('all', 'dev', 'test'), default='all')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    truth = json.loads((ROOT / 'benchmark' / 'rosetta_truth.json').read_text(encoding='utf-8'))['tasks']
    cat = {k: v for k, v in json.loads(a.catalog.read_text(encoding='utf-8')).items() if v['discriminative']}
    by_sig = defaultdict(list)
    for k, v in cat.items():
        by_sig[tuple(v['sig'])].append(k)
    jobs = [(t, l, f) for t in truth for l, f in files(a.rosetta, t)
            if (a.split == 'all' or split_of(t, l, f) == a.split)]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        results = list(pool.map(lambda j: file_answer(j[2], cat, by_sig) if j[1] in LANGS_RUN
                                else {'outcome': 'NO_TRANSLATOR'}, jobs))
    st = defaultdict(lambda: defaultdict(int))
    for (task, lang, f), r in zip(jobs, results):
        o = r['outcome']
        good = set(truth[task])
        ok = None
        if o in ('SAME_LOGIC', 'SAME_FUNCTION'):
            ok = any(ref.split('::')[0] in good for ref in r['refs'])
        for k in ('ALL', 'lang:' + lang, 'neg' if not good else 'pos'):
            st[k]['files'] += 1
            st[k][o] += 1
            if ok is not None:
                st[k][o + '_ok'] += ok
        refs = r.get('refs', [])
        print(f"{task}|{lang}|{f.name}|{o}|{'' if ok is None else ('ok' if ok else 'WRONG')}|"
              f"{len(refs)} refs: " + ', '.join(refs[:4]) + (r.get('reason') or ''))
    print('\n=== AP13 v4 RECALL ENGINE (Prolog normal form: logic trace, then input->output) ===')
    for k in ['ALL', 'pos', 'neg'] + sorted(x for x in st if x.startswith('lang:')):
        s = st[k]
        print(f"{k:16s} files={s['files']:4d} SAME_LOGIC={s['SAME_LOGIC']:3d}({s['SAME_LOGIC_ok']}) "
              f"SAME_FUNCTION={s['SAME_FUNCTION']:3d}({s['SAME_FUNCTION_ok']}) NO_MATCH={s['NO_MATCH']:3d} "
              f"NOT_RUNNABLE={s['NOT_RUNNABLE']:3d} NO_TRANSLATOR={s['NO_TRANSLATOR']:3d} ERROR={s['ERROR']:2d}")
    p, al = st['pos'], st['ALL']
    ans = al['SAME_LOGIC'] + al['SAME_FUNCTION']
    corr = al['SAME_LOGIC_ok'] + al['SAME_FUNCTION_ok']
    print(f"\nPRECISION (correct / answered) = {corr}/{ans} = {corr / max(ans, 1):.1%}"
          f"   logic {al['SAME_LOGIC_ok']}/{al['SAME_LOGIC']}  io {al['SAME_FUNCTION_ok']}/{al['SAME_FUNCTION']}")
    pc = p['SAME_LOGIC_ok'] + p['SAME_FUNCTION_ok']
    print(f"RECALL (correct / positive files) = {pc}/{p['files']} = {pc / max(p['files'], 1):.1%}")
    tr = p['files'] - p['NO_TRANSLATOR']
    print(f"RECALL on languages with a translator = {pc}/{tr} = {pc / max(tr, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {st['neg']['SAME_LOGIC'] + st['neg']['SAME_FUNCTION']} of {st['neg']['files']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
