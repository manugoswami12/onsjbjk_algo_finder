"""Cross-language test: knowledge learned from labelled PYTHON files, applied to other languages.

usage: python eval_crosslang.py <test root> <train root> --lang Common-Lisp --sample 3 --train T1.json ...
Front ends (crosslang_frontends.py): Haskell via GHC Core, Lisp via SBCL macro-expansion.
Only the language-independent channels apply (the v0.2 witnesses are Python-only):
  ap13dir  AP13 exact traced logic (tree-sitter lowering of Lisp / Haskell)
  iocat    AP13 behaviour catalog (Prolog normal form run in SWI-Prolog; Lisp yes, Haskell no translator)
Learned labels become observed(F, learned(L), 1) and are routed by prolog/route_v2.pl.
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
    p.add_argument('root', type=Path)
    p.add_argument('train_root', type=Path)
    p.add_argument('--truth', default=str(ROOT / 'benchmark' / 'crosslang_truth.json'))
    p.add_argument('--lang', required=True)
    p.add_argument('--sample', default='3')
    p.add_argument('--samples-key', default='samples_v2', help="'samples' (first draw) or 'samples_v2'")
    p.add_argument('--train', nargs='+', required=True)
    p.add_argument('--learner', nargs='+', default=['ap13dir', 'iocat'], choices=['ap13dir', 'iocat'])
    a = p.parse_args()
    truth = json.loads(Path(a.truth).read_text(encoding='utf-8'))
    allowed = set(truth['_allowed_on_negative'])
    crosslang_frontends.install()
    files = [(rel, truth['files'][rel]) for rel in truth[a.samples_key][a.lang][a.sample]]
    learners = {n: compare_learners.LEARNERS[n](a.train_root, a.train) for n in a.learner}
    analyses, via = [], {}
    for rel, _ in files:
        an = Analysis(rel, [])
        via[rel] = {}
        for name, learner in learners.items():
            for label in sorted(learner.labels_for(a.root / rel)):
                an.add(f'learned({label})', 1)
                via[rel].setdefault(label, []).append(name)
        analyses.append(an)
    routes = route_live(analyses)
    correct = answered = positives = wrong_neg = 0
    print(f"{'file':60s} {'expected':28s} outcome   routes  [learner]")
    for i, (rel, expected) in enumerate(files, 1):
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
        print(f"{rel:60s} {str(expected)[:28]:28s} {outcome:9s} {','.join(sorted(got)) or '-'}  {via[rel] or ''}")
    print(f"\n{a.lang} sample {a.sample}")
    print(f"PRECISION = correct / answered = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = correct / positives = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(files) - positives}")


if __name__ == '__main__':
    main()
