"""Function-level cross-language test on external codebases (benchmark/crosslang_ext_truth.json):
knowledge learned from labelled PYTHON files only; each test function gets the labels of the
Python references it matches (AP13 behaviour catalog and exact traced logic), routed by route_v2.pl.

usage: python eval_crosslang_ext.py <dir with the cloned repos> <train root> --lang Haskell --stage 3 --train T.json ...
"""
import argparse
import json
from pathlib import Path

import compare_learners
import crosslang_frontends
from run_v2 import ROOT, route_live
from static_trace import Analysis


def main():
    p = argparse.ArgumentParser()
    p.add_argument('repos', type=Path)
    p.add_argument('train_root', type=Path)
    p.add_argument('--truth', default=str(ROOT / 'benchmark' / 'crosslang_ext_truth.json'))
    p.add_argument('--lang', required=True, choices=['Haskell', 'Common-Lisp'])
    p.add_argument('--stage', default='3', choices=['3', 'all'])
    p.add_argument('--train', nargs='+', required=True)
    a = p.parse_args()
    truth = json.loads(Path(a.truth).read_text(encoding='utf-8'))
    spec = truth[a.lang]
    names = spec['sample3'] if a.stage == '3' else sorted(spec['functions'])
    allowed = set(truth['_allowed_on_negative'])
    crosslang_frontends.install()
    learners = {n: compare_learners.LEARNERS[n](a.train_root, a.train) for n in ('ap13dir', 'iocat')}
    by_file = {}
    for key in names:
        by_file.setdefault(key.split('::')[0], []).append(key)
    found = {}
    for rel in by_file:
        path = a.repos / spec['root'] / rel
        for lname, learner in learners.items():
            for fn, labels in learner.labels_by_function(path).items():
                for label in labels:
                    found.setdefault(f'{rel}::{fn}', {}).setdefault(label, []).append(lname)
    analyses = []
    for key in names:
        an = Analysis(key, [])
        for label in sorted(found.get(key, {})):
            an.add(f'learned({label})', 1)
        analyses.append(an)
    routes = route_live(analyses)
    correct = answered = positives = wrong_neg = 0
    print(f"{'function':48s} {'expected':28s} outcome   routes  [learner]")
    for i, key in enumerate(names, 1):
        expected = spec['functions'][key]
        got = set(routes[f'f{i}']) - {'unknown'}
        if expected is None:
            bad = got - allowed
            outcome = 'WRONG' if bad else 'ok(neg)'
            wrong_neg += bool(bad)
            answered += bool(bad)
        else:
            positives += 1
            answered += bool(got)
            accepted = set(expected) if isinstance(expected, list) else {expected}
            outcome = 'ok' if accepted & got else ('WRONG' if got else 'UNKNOWN')
            correct += outcome == 'ok'
        print(f"{key[-48:]:48s} {str(expected)[:28]:28s} {outcome:9s} {','.join(sorted(got)) or '-'}  {found.get(key, '')}")
    print(f"\n{a.lang} stage {a.stage}: {len(names)} functions")
    print(f"PRECISION = correct / answered = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = correct / positives = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(names) - positives}")


if __name__ == '__main__':
    main()
