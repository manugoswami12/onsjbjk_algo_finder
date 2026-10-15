#!/usr/bin/env python3
"""AP13 held-out evaluation on Rosetta Code (other people's code, 8 languages).

Rosetta Code text is GFDL-licensed, so it is fetched (sparse, shallow git clone)
into store/rosetta and never committed. References are learned ONLY from the
AP13 Python examples, then every Rosetta file is scanned. Results are counted,
never tuned per file.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import learn, scan  # noqa: E402
from env_run import ROOT, ToolError, need, run  # noqa: E402

REPO_URL = 'https://github.com/acmeism/RosettaCodeData.git'
LANGS = ['Python', 'Rust', 'Java', 'C', 'R', 'Haskell', 'Common-Lisp', 'Prolog']
TASKS = {  # task -> (expected family branch, reference label, reference source, function)
    'Sorting-algorithms-Bubble-sort': ('comparison_driven_reordering', 'ref_bubble_py',
                                       ROOT / 'examples' / 'bubble' / 'bubble.py', 'bubble_sort'),
    'Binary-search': ('interval_lookup', 'ref_binary_py',
                      ROOT / 'examples' / 'binary_search' / 'binary_search.py', 'binary_search'),
}
EXT = {'Python': '.py', 'Rust': '.rs', 'Java': '.java', 'C': '.c', 'R': '.r', 'Haskell': '.hs',
       'Common-Lisp': '.lisp', 'Prolog': '.pro'}


def fetch(dest: Path):
    if (dest / 'Task').is_dir():
        return
    git = need('git')
    for argv in ([git, 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', REPO_URL, str(dest)],
                 [git, '-C', str(dest), 'sparse-checkout', 'set', *[f'Task/{t}' for t in TASKS]]):
        done = run(argv, timeout=600)
        if done.returncode:
            raise ToolError('git failed: ' + done.stderr[-400:])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rosetta', type=Path, default=ROOT / 'store' / 'rosetta')
    a = p.parse_args()
    fetch(a.rosetta)
    totals = {'files': 0, 'leaf_match': 0, 'family': 0, 'wrong_family': 0, 'false_match': 0, 'errors': 0}
    with tempfile.TemporaryDirectory(prefix='ap13_rosetta_') as td:
        store = Path(td)
        for branch, label, src, fn in TASKS.values():
            learn(label, src, fn, store)
        others = {t[0] for t in TASKS.values()}
        for task, (branch, label, _, _) in TASKS.items():
            for lang in LANGS:
                for f in sorted((a.rosetta / 'Task' / task / lang).glob('*' + EXT[lang])):
                    totals['files'] += 1
                    try:
                        r = scan(f, store, True, quiet=True)
                    except (ToolError, ValueError, OSError) as exc:
                        totals['errors'] += 1
                        print(f'ERROR|{task}|{lang}|{f.name}|{exc}'[:200])
                        continue
                    routes = set().union(*(set(x['routes']) for x in r['functions'])) if r['functions'] else set()
                    matches = {x['label'] for x in r['leaves'] if x['result'] == 'MATCH'}
                    totals['leaf_match'] += label in matches
                    totals['false_match'] += bool(matches - {label})
                    totals['family'] += branch in routes
                    totals['wrong_family'] += bool(routes & (others - {branch}))
                    print(f"{task}|{lang}|{f.name}|leaf={','.join(sorted(matches)) or 'none'}|"
                          f"routes={','.join(sorted(routes))}")
    print('AP13_ROSETTA: ' + ' '.join(f'{k}={v}' for k, v in totals.items()))
    print('Held-out evaluation: counts are measured, not tuned; UNKNOWN is preferred to guessing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
