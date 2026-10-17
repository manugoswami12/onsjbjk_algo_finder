"""Held-out precision/recall of v0.2 on real files (source parsed only, never executed).

usage: python eval_heldout.py <checkout root> [truth.json] [--kb kb/learned.json | --leave-one-out T.json ...]
A file's answer is the union of its functions' routes minus `unknown`.
  positive: correct if the expected branch (or one of a listed set) is in the answer; WRONG if answered without it
  negative: WRONG if answered with anything beyond the allowed broad branches
One SWI-Prolog call for all files; a file Python cannot parse counts as UNKNOWN.
"""
import json
import sys
from pathlib import Path

import argparse

import learn_v2
from run_v2 import ROOT, load, route_live


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('truth', nargs='?', default=str(ROOT / 'benchmark' / 'heldout_truth.json'))
    p.add_argument('--kb', default='none', help="learned KB json, or 'none' (default: witnesses only)")
    p.add_argument('--leave-one-out', nargs='+', metavar='TRUTH',
                   help='learn from these truth files, excluding the file under test each time')
    p.add_argument('--learner', nargs='+', default=[], choices=['ap13dir', 'iocat'],
                   help='original AP13 learners (compare_learners.py), trained on --train')
    p.add_argument('--train-root', type=Path, help='checkout of the training files (default: root)')
    p.add_argument('--train', nargs='+', default=[], metavar='TRUTH', help='labelled training files')
    p.add_argument('--popper-rules', help='SEPARATE Popper fallback rules (popper_fallback.py), applied only '
                   'to files the system above leaves UNKNOWN')
    a = p.parse_args()
    import compare_learners
    learners = [compare_learners.LEARNERS[n](a.train_root or a.root, a.train) for n in a.learner]
    root = a.root
    truth = json.loads(Path(a.truth).read_text(encoding='utf-8'))
    kb_all = None if a.kb == 'none' else learn_v2.load_kb(a.kb)
    allowed = set(truth['_allowed_on_negative'])
    files, analyses, owner, notes = list(truth['files'].items()), [], [], {}
    for rel, _ in files:
        try:
            kb = (learn_v2.learn(root, a.leave_one_out, exclude={rel}) if a.leave_one_out else kb_all)
            found = load(root / rel, kb)
            if found:
                for learner in learners:
                    for label in sorted(learner.labels_for(root / rel)):
                        found[0].add(f'learned({label})', 1)   # file-level answer: union of functions
        except (SyntaxError, ValueError) as exc:
            notes[rel] = 'not parseable: ' + str(exc).split(' (')[0]
            found = []
        analyses += found
        owner += [rel] * len(found)
    routes = route_live(analyses) if analyses else {}
    answer = {rel: set() for rel, _ in files}
    for i, rel in enumerate(owner, 1):
        answer[rel] |= set(routes['f' + str(i)]) - {'unknown'}
    if a.popper_rules:                      # separate fallback stage, second Prolog call
        import popper_fallback
        rules = popper_fallback.load_rules(a.popper_rules)
        fired = 0
        for rel, _ in files:
            if answer[rel] or rel not in owner:
                continue
            first = analyses[owner.index(rel)]
            for label in sorted(popper_fallback.labels_for((root / rel).read_text(encoding='utf-8-sig'), rules)):
                first.add(f'learned({label})', 1)
                fired += 1
                notes[rel] = (notes.get(rel, '') + ' popper').strip()
        if fired:
            routes = route_live(analyses)
            answer = {rel: set() for rel, _ in files}
            for i, rel in enumerate(owner, 1):
                answer[rel] |= set(routes['f' + str(i)]) - {'unknown'}
    correct = answered = positives = wrong_neg = 0
    print(f"{'file':38s} {'expected':30s} outcome   routes")
    for rel, expected in files:
        got = answer[rel]
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
        print(f"{rel:38s} {str(expected)[:30]:30s} {outcome:9s} {','.join(sorted(got)) or '-'} {notes.get(rel, '')}")
    print(f"\nPRECISION = correct / answered = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = correct / positives = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(files) - positives}")


if __name__ == '__main__':
    main()
