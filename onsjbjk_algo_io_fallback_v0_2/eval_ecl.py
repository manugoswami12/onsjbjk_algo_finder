"""Function-level test of Common Lisp through ECL C and prolog/route_v2.pl.

usage: python eval_ecl.py <dir with programming-algorithms-lisp> [--stage clean|all] [--method witness|families]
  clean: the 3 functions of the frozen key never used before; all: every function in the key.
  witness:  ECL C shape witnesses (ecl_witness.py)
  families: ECL C -> AP13 neutral facts -> Prolog logic tracing, the same rules as every language
            (ecl_logic.py: prolog/ecl_norm.pl + AP13 roles/families + prolog/family_to_v02.pl)
"""
import argparse
import json
from pathlib import Path

import ecl_logic
import ecl_witness
from run_v2 import ROOT, route_live
from static_trace import Analysis


def main():
    p = argparse.ArgumentParser()
    p.add_argument('repos', type=Path)
    p.add_argument('--stage', default='clean', choices=['clean', 'all'])
    p.add_argument('--method', default='witness', choices=['witness', 'families'])
    a = p.parse_args()
    truth = json.loads((ROOT / 'benchmark' / 'crosslang_ext_truth.json').read_text(encoding='utf-8'))
    spec, allowed = truth['Common-Lisp'], set(truth['_allowed_on_negative'])
    used = set(spec['retired_sample3']) | {k for s in spec['retired_samples'] for k in s} | set(spec['sample3'])
    names = sorted(set(spec['functions']) - used) if a.stage == 'clean' else sorted(spec['functions'])
    found = {}
    for rel in sorted({k.split('::')[0] for k in names}):
        path = a.repos / spec['root'] / rel
        if a.method == 'witness':
            for lname, an in ecl_witness.analyse_lisp(path):
                found[f'{rel}::{lname.replace("_", "-")}'] = an
        else:
            for lname, fams in ecl_logic.families(path).items():
                an = found.setdefault(f'{rel}::{lname}', Analysis(lname, []))
                for fam, branch in fams:
                    an.add(f"family('{fam}')", 1)
                    if branch != 'none':
                        an.add(f'learned({branch})', 1)
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
    print(f"\nCommon-Lisp via ECL ({a.method}), stage {a.stage}: {len(names)} functions")
    print(f"PRECISION = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(names) - positives}")


if __name__ == '__main__':
    main()
