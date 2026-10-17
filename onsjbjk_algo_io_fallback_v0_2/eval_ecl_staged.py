"""Staged test of Common Lisp via ECL C and Prolog logic tracing (ecl_logic.py) + prolog/route_v2.pl.

usage: python eval_ecl_staged.py <rosetta checkout> <dir with programming-algorithms-lisp> --stage 3|15|55|101
Frozen key benchmark/ecl_staged_truth.json: a rosetta unit is a whole file (answer = union of its
functions), a book unit is one function. Success: precision and recall >= 80 %.
"""
import argparse
import json
import subprocess
from pathlib import Path

import ecl_logic
from run_v2 import ROOT, route_live
from static_trace import Analysis


def unit_analysis(unit, rosetta, book, cache):
    kind, ref = unit.split(':', 1)
    rel, _, fname = ref.partition('::')
    path = (rosetta / rel) if kind == 'rosetta' else (book / rel)
    if path not in cache:
        try:
            cache[path] = ecl_logic.families(path)
        except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:   # ECL / SWI-Prolog failure: no answer
            print(f'  ({unit}: {type(exc).__name__}: {str(exc)[:120]})')
            cache[path] = {}
    an = Analysis(unit, [])
    for name, fams in cache[path].items():
        if kind == 'book' and name != fname.lower():
            continue
        for fam, branch in fams:
            an.add(f"family('{fam}')", 1)
            if branch != 'none':
                an.add(f'learned({branch})', 1)
    return an


def main():
    p = argparse.ArgumentParser()
    p.add_argument('rosetta', type=Path)
    p.add_argument('book', type=Path)
    p.add_argument('--stage', required=True, choices=['3', '15', '55', '101'])
    a = p.parse_args()
    key = json.loads((ROOT / 'benchmark' / 'ecl_staged_truth.json').read_text(encoding='utf-8'))
    allowed, units = set(key['_allowed_on_negative']), key['stages'][a.stage]
    cache = {}
    analyses = [unit_analysis(u, a.rosetta, a.book, cache) for u in units]
    routes = route_live(analyses)
    correct = answered = positives = wrong_neg = 0
    for i, unit in enumerate(units, 1):
        expected = key['units'][unit]
        got = set(routes[f'f{i}']) - {'unknown'}
        if expected is None:
            bad = got - allowed
            outcome, wrong_neg, answered = ('WRONG' if bad else 'ok(neg)'), wrong_neg + bool(bad), answered + bool(bad)
        else:
            positives += 1
            answered += bool(got)
            acc = set(expected) if isinstance(expected, list) else {expected}
            outcome = 'ok' if acc & got else ('WRONG' if got else 'UNKNOWN')
            correct += outcome == 'ok'
        fams = sorted(f[8:-2] for f in analyses[i - 1].evidence if f.startswith('family('))
        print(f"{unit.split('/')[-1][:46]:46s} {str(expected)[:28]:28s} {outcome:8s} "
              f"{','.join(sorted(got)) or '-'}  families={fams}")
    prec, rec = correct / max(answered, 1), correct / max(positives, 1)
    print(f"\nCommon-Lisp via ECL logic tracing, stage {a.stage}: {len(units)} units")
    print(f"PRECISION = {correct}/{answered} = {prec:.1%}")
    print(f"RECALL    = {correct}/{positives} = {rec:.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(units) - positives}")
    print('STAGE', 'PASS' if prec >= 0.8 and rec >= 0.8 else 'FAIL')


if __name__ == '__main__':
    main()
