"""Learning test (doc 04): learn new algorithms from Python, recognise them in unseen Lisp, C, Haskell.

usage: python eval_learn.py <rosetta checkout> --learn            (learn from the Python training files)
       python eval_learn.py <rosetta checkout> --lang Common-Lisp|C|Haskell|hard
Frozen key benchmark/learn_truth.json. A unit is a file; its answer is the learned labels of its root
functions (tagged learned:Rule). Success per language: precision and recall >= 80 %.
"""
import argparse
import json
import subprocess
from pathlib import Path

import ecl_logic
import learn_apply
from run_v2 import ROOT

ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError, subprocess.SubprocessError)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('rosetta', type=Path)
    p.add_argument('--learn', action='store_true')
    p.add_argument('--lang', choices=['Common-Lisp', 'C', 'Haskell', 'hard'])
    a = p.parse_args()
    key = json.loads((ROOT / 'benchmark' / 'learn_truth.json').read_text(encoding='utf-8'))
    if a.learn:
        train = {a.rosetta / f: None for f in key['train']['negatives']}
        train.update({a.rosetta / f: lab for f, lab in key['train']['hard_case_positives'].items()})
        train.update({a.rosetta / f: lab for f, lab in key['train']['positives'].items()})
        count = learn_apply.learn(train)
        print(f'learned from {len(train)} Python files ({sum(1 for v in count.values() if v)} with streams) '
              f'-> {learn_apply.RULES}')
        return
    if a.lang == 'hard':
        return hard_cases(a, key)
    units, labels = key['tests'][a.lang]['units'], set(key['new_tasks'].values())
    correct = answered = positives = wrong_neg = 0
    for rel, expected in sorted(units.items()):
        try:
            found = learn_apply.apply(a.rosetta / rel)
        except ERRORS as exc:
            print(f'  ({rel}: {type(exc).__name__}: {str(exc)[:100]})')
            found = []
        got = {lab for _, lab, _ in found} & labels
        rules = sorted({f'learned:{lab}:{r}' for _, lab, r in found if lab in got})
        if expected is None:
            bad = bool(got)
            outcome, wrong_neg, answered = ('WRONG' if bad else 'ok(neg)'), wrong_neg + bad, answered + bad
        else:
            positives += 1
            answered += bool(got)
            outcome = 'ok' if expected in got else ('WRONG' if got else 'UNKNOWN')
            correct += outcome == 'ok'
        print(f"{rel.split('/')[-1][:44]:44s} {str(expected)[:22]:22s} {outcome:8s} {' '.join(rules) or '-'}")
    prec, rec = correct / max(answered, 1), correct / max(positives, 1)
    print(f'\nlearned from Python, tested on {a.lang}: {len(units)} units')
    print(f'PRECISION = {correct}/{answered} = {prec:.1%}')
    print(f'RECALL    = {correct}/{positives} = {rec:.1%}')
    print(f'WRONG ON NEGATIVES = {wrong_neg} of {len(units) - positives}')
    print('STAGE', 'PASS' if prec >= 0.8 and rec >= 0.8 else 'FAIL')
    return None


def hard_cases(a, key):
    """Known tasks the normal process misses: the normal answer first, then the learned rules."""
    for rel, expected in sorted(key['hard_cases'].items()):
        path = a.rosetta / rel
        fams = ecl_logic.families(path)
        normal = {b for v in fams.values() for _, b in v} - {'none'}
        learned = {lab for _, lab, _ in learn_apply.apply(path)} if not normal else set()
        print(f"{rel.split('/')[-1]:44s} {expected:16s} normal={sorted(normal) or '-'} learned={sorted(learned) or '-'}")


if __name__ == '__main__':
    main()
