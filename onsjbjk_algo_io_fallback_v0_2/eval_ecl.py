"""Function-level test of Common Lisp through ECL C witnesses (ecl_witness.py) and prolog/route_v2.pl.

usage: python eval_ecl.py <dir with programming-algorithms-lisp> [--stage clean|all]
  clean: the 3 functions of the frozen key never used before; all: every function in the key.
"""
import argparse
import json
from pathlib import Path

import ecl_witness
from run_v2 import ROOT, route_live
from static_trace import Analysis


def main():
    p = argparse.ArgumentParser()
    p.add_argument('repos', type=Path)
    p.add_argument('--stage', default='clean', choices=['clean', 'all'])
    a = p.parse_args()
    truth = json.loads((ROOT / 'benchmark' / 'crosslang_ext_truth.json').read_text(encoding='utf-8'))
    spec, allowed = truth['Common-Lisp'], set(truth['_allowed_on_negative'])
    used = set(spec['retired_sample3']) | {k for s in spec['retired_samples'] for k in s} | set(spec['sample3'])
    names = sorted(set(spec['functions']) - used) if a.stage == 'clean' else sorted(spec['functions'])
    found = {}
    for rel in sorted({k.split('::')[0] for k in names}):
        for lname, an in ecl_witness.analyse_lisp(a.repos / spec['root'] / rel):
            found[f'{rel}::{lname.replace("_", "-")}'] = an
    analyses = [found.get(k.lower(), Analysis(k, [])) for k in names]
    routes = route_live(analyses)
    correct = answered = positives = wrong_neg = 0
    for i, key in enumerate(names, 1):
        expected = spec['functions'][key]
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
        print(f"{key:48s} {str(expected)[:30]:30s} {outcome:8s} {','.join(sorted(got)) or '-'}  "
              f"facts={sorted(analyses[i - 1].evidence)}")
    print(f"\nCommon-Lisp via ECL, stage {a.stage}: {len(names)} functions")
    print(f"PRECISION = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(names) - positives}")


if __name__ == '__main__':
    main()
