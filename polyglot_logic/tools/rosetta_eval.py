#!/usr/bin/env python3
"""AP13 held-out evaluation on Rosetta Code (other people's code, 8 languages).

Rosetta Code text is GFDL-licensed: it is fetched (sparse, shallow git clone)
into store/rosetta and never committed.

  v1 mode (default): references learned only from the two AP13 Python examples,
                     tasks Bubble sort and Binary search (doc 03).
  v2 mode (--store): references learned from the WHOLE TheAlgorithms corpus by
                     `cli.py learn-dir`; ground truth benchmark/rosetta_truth.json
                     (written before the first run); all its tasks (doc 06).
Counts are measured, never tuned per file.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import knowledge_store as store_mod  # noqa: E402
from cli import learn, scan  # noqa: E402
from env_run import ROOT, ToolError, need, run  # noqa: E402
from report import identifications  # noqa: E402

REPO_URL = 'https://github.com/acmeism/RosettaCodeData.git'
TRUTH = ROOT / 'benchmark' / 'rosetta_truth.json'
LANGS = ['Python', 'Rust', 'Java', 'C', 'R', 'Haskell', 'Common-Lisp', 'Prolog']
EXT = {'Python': ('.py',), 'Rust': ('.rs',), 'Java': ('.java',), 'C': ('.c',), 'R': ('.r', '.R'),
       'Haskell': ('.hs',), 'Common-Lisp': ('.lisp',), 'Prolog': ('.pro', '.pl')}
V1_TASKS = {
    'Sorting-algorithms-Bubble-sort': ('comparison_driven_reordering', 'ref_bubble_py',
                                       ROOT / 'examples' / 'bubble' / 'bubble.py', 'bubble_sort'),
    'Binary-search': ('interval_lookup', 'ref_binary_py',
                      ROOT / 'examples' / 'binary_search' / 'binary_search.py', 'binary_search'),
}


def fetch(dest: Path, tasks):
    git = need('git')
    if not (dest / '.git').is_dir():
        done = run([git, 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', REPO_URL, str(dest)],
                   timeout=900)
        if done.returncode:
            raise ToolError('git clone failed: ' + done.stderr[-400:])
    done = run([git, '-C', str(dest), 'sparse-checkout', 'set', *[f'Task/{t}' for t in tasks]], timeout=900)
    if done.returncode:
        raise ToolError('git sparse-checkout failed: ' + done.stderr[-400:])


def files(rosetta, task):
    for lang in LANGS:
        folder = rosetta / 'Task' / task / lang
        for f in sorted(folder.glob('*')) if folder.is_dir() else []:
            if f.suffix in EXT[lang]:
                yield lang, f


def scan_safe(f, store):
    try:
        return scan(f, store, True, quiet=True), None
    except (ToolError, ValueError, OSError, RecursionError) as exc:
        return None, str(exc)


def evaluate_v1(rosetta):
    totals = {'files': 0, 'leaf_match': 0, 'family': 0, 'wrong_family': 0, 'false_match': 0, 'errors': 0}
    with tempfile.TemporaryDirectory(prefix='ap13_rosetta_') as td:
        store = Path(td)
        for branch, label, src, fn in V1_TASKS.values():
            learn(label, src, fn, store)
        others = {t[0] for t in V1_TASKS.values()}
        for task, (branch, label, _, _) in V1_TASKS.items():
            for lang, f in files(rosetta, task):
                totals['files'] += 1
                r, err = scan_safe(f, store)
                if err:
                    totals['errors'] += 1
                    print(f'ERROR|{task}|{lang}|{f.name}|{err}'[:200])
                    continue
                routes = set().union(*(set(x['routes']) for x in r['functions'])) if r['functions'] else set()
                matches = {x['label'] for x in r['leaves'] if x['result'] == 'MATCH'}
                totals['leaf_match'] += label in matches
                totals['false_match'] += bool(matches - {label})
                totals['family'] += branch in routes
                totals['wrong_family'] += bool(routes & (others - {branch}))
                print(f"{task}|{lang}|{f.name}|leaf={','.join(sorted(matches)) or 'none'}|routes={','.join(sorted(routes))}")
    print('AP13_ROSETTA: ' + ' '.join(f'{k}={v}' for k, v in totals.items()))


def evaluate_v2(rosetta, store, truth, workers=4):
    from concurrent.futures import ThreadPoolExecutor
    meta = store_mod.metadata(store)
    stats = defaultdict(lambda: defaultdict(int))  # key -> metric -> count
    wrong = []
    jobs = [(task, good, lang, f) for task, good in truth['tasks'].items() for lang, f in files(rosetta, task)]
    with ThreadPoolExecutor(max_workers=workers) as pool:   # scans are independent subprocesses
        results = list(pool.map(lambda j: scan_safe(j[3], store), jobs))
    for (task, good, lang, f), (r, err) in zip(jobs, results):
        keys = ('ALL', 'lang:' + lang, 'task:' + task, 'positive' if good else 'negative')
        for k in keys:
            stats[k]['files'] += 1
        if err:
            for k in keys:
                stats[k]['error'] += 1
            print(f'ERROR|{task}|{lang}|{f.name}|{err[:150]}')
            continue
        ids = identifications(r, meta)
        paths = [{meta[l]['source_path'] for l in labels} for _, labels in ids]
        ok = [bool(p & set(good)) for p in paths]
        outcome = 'unknown'
        lib_ok = set(r.get('library', [])) & set(truth.get('library', {}).get(task, []))
        if not ids and r.get('library'):  # library call/idiom only (reported separately)
            outcome = 'library_correct' if lib_ok else 'library_other'
        if ids:
            outcome = 'top1_correct' if ok[0] else ('any_correct' if any(ok) else 'top1_wrong')
            if not ok[0]:
                culprit = ids[0][1][0]
                wrong.append((task, lang, f.name, meta[culprit]['source_path'] + '::' + meta[culprit]['function_name']))
        for k in keys:
            stats[k][outcome] += 1
        top = ''
        if ids:
            lab = ids[0][1][0]
            top = meta[lab]['source_path'] + '::' + meta[lab]['function_name'] + f' (+{len(ids[0][1]) - 1} same)'
        print(f'{task}|{lang}|{f.name}|{outcome}|{top}')

    def row(k):
        s = stats[k]
        return (f"{k:44s} files={s['files']:4d} top1_correct={s['top1_correct']:3d} "
                f"correct_not_top1={s['any_correct']:3d} wrong={s['top1_wrong']:3d} "
                f"library_correct={s['library_correct']:3d} library_other={s['library_other']:3d} "
                f"unknown={s['unknown']:4d} errors={s['error']:2d}")
    print('\n=== AP13 v2 HELD-OUT RESULTS (references learned from the whole corpus) ===')
    for k in ['ALL', 'positive', 'negative'] + sorted(k for k in stats if k.startswith('lang:')) + \
            sorted(k for k in stats if k.startswith('task:')):
        print(row(k))
    a = stats['ALL']
    answered = a['top1_correct'] + a['top1_wrong'] + a['any_correct']
    pos = stats['positive']
    print(f"\nPRECISION (top-1 correct / answered) = {a['top1_correct']}/{answered}"
          f" = {a['top1_correct'] / answered:.1%}" if answered else '\nPRECISION: no answers')
    print(f"RECALL traced (top-1 correct / positive files) = {pos['top1_correct']}/{pos['files']}"
          f" = {pos['top1_correct'] / max(pos['files'], 1):.1%}")
    lib = pos['top1_correct'] + pos['library_correct']
    print(f"RECALL traced + library (correct / positive files) = {lib}/{pos['files']}"
          f" = {lib / max(pos['files'], 1):.1%}")
    print('\n=== WRONG TOP-1 IDENTIFICATIONS (culprit reference) ===')
    for w in wrong:
        print(' | '.join(w))
    return stats


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rosetta', type=Path, default=ROOT / 'store' / 'rosetta')
    p.add_argument('--store', type=Path, help='v2: catalog learned by learn-dir from the whole corpus')
    p.add_argument('--no-fetch', action='store_true')
    a = p.parse_args()
    truth = json.loads(TRUTH.read_text(encoding='utf-8'))
    tasks = list(truth['tasks']) if a.store else list(V1_TASKS)
    if not a.no_fetch:
        fetch(a.rosetta, tasks)
    if a.store:
        evaluate_v2(a.rosetta, a.store, truth)
    else:
        evaluate_v1(a.rosetta)
    print('Held-out evaluation: counts are measured, not tuned; UNKNOWN is preferred to guessing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
