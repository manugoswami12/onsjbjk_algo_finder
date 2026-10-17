"""Held-out precision/recall of v0.2 on real files (source parsed only, never executed).

usage: python eval_heldout.py <checkout root> [benchmark/heldout_truth.json]
A file's answer is the union of its functions' routes minus `unknown`.
  positive: correct if the expected branch is in the answer; WRONG if answered without it
  negative: WRONG if answered with anything beyond the allowed broad branches
One SWI-Prolog call for all files; a file Python cannot parse counts as UNKNOWN.
"""
import json
import sys
from pathlib import Path

from run_v2 import ROOT, load, route_live


def main():
    root = Path(sys.argv[1])
    truth = json.loads(Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'benchmark' / 'heldout_truth.json')
                       .read_text(encoding='utf-8'))
    allowed = set(truth['_allowed_on_negative'])
    files, analyses, owner, notes = list(truth['files'].items()), [], [], {}
    for rel, _ in files:
        try:
            found = load(root / rel)
        except SyntaxError as exc:
            notes[rel] = 'not parseable: ' + str(exc).split(' (')[0]
            found = []
        analyses += found
        owner += [rel] * len(found)
    routes = route_live(analyses) if analyses else {}
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
            outcome = 'ok' if expected in got else ('WRONG' if got else 'UNKNOWN')
            correct += outcome == 'ok'
        print(f"{rel:38s} {str(expected):30s} {outcome:9s} {','.join(sorted(got)) or '-'} {notes.get(rel, '')}")
    print(f"\nPRECISION = correct / answered = {correct}/{answered} = {correct / max(answered, 1):.1%}")
    print(f"RECALL    = correct / positives = {correct}/{positives} = {correct / max(positives, 1):.1%}")
    print(f"WRONG ON NEGATIVES = {wrong_neg} of {len(files) - positives}")


if __name__ == '__main__':
    main()
