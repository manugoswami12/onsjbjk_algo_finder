"""Test of the class fallback (doc 04 section 18), kept separate from the pipeline: on the held-out Rosetta files,
the answers of eval_ta.py (benchmark/ta_heldout.json) are kept, and where a file is UNKNOWN the class relations
(ta_classes.py, prolog/class_specs.pl) name its class. Scored at two levels:
  algorithm  the answer names the task's algorithm (bubble sort for a bubble sort)
  class      the answer names what the task computes (sorting for any sort; a named algorithm counts as its class)
A file that runs, satisfies no class relation and gets no algorithm answer is a new class.

usage: python eval_classes.py CORPUS ROSETTA     -> benchmark/class_fallback.json, benchmark/class_fallback.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import crosslang_frontends
import ta_classes
import ta_corpus
from ta_corpus import ROOT

HELDOUT = ROOT / 'benchmark' / 'ta_heldout.json'
OUT, REPORT = ROOT / 'benchmark' / 'class_fallback.json', ROOT / 'benchmark' / 'class_fallback.md'

# what each Rosetta task computes (its class relation); tasks whose input or output is not on the battery (strings,
# matrices, moves) have none: their class is the task itself, answered at the algorithm level only
TASK_CLASS = {'Binary-search': 'search', 'Greatest-common-divisor': 'gcd', 'Least-common-multiple': 'lcm',
              'Factorial': 'factorial', 'Fibonacci-sequence': 'fibonacci', 'Sieve-of-Eratosthenes': 'primes_upto',
              'Primality-by-trial-division': 'prime_check', 'Perfect-numbers': 'perfect_number',
              'Sum-digits-of-an-integer': 'digit_sum', 'Hailstone-sequence': 'collatz',
              'Palindrome-detection': 'palindrome_check', 'Luhn-test-of-credit-card-numbers': 'luhn',
              'N-queens-problem': 'n_queens_count'}


def task_class(task: str) -> str:
    return 'sorting' if task.startswith('Sorting-algorithms-') else TASK_CLASS.get(task, task)


def main():
    corpus, rosetta = Path(sys.argv[1]), Path(sys.argv[2])
    crosslang_frontends.install(lisp_sbcl=False)
    held = json.loads(HELDOUT.read_text(encoding='utf-8'))
    labels = ta_corpus.files(corpus)
    groups = ta_corpus.groups(labels.values())

    def one(rel):
        try:
            rs = ta_classes.runs(rosetta / rel)
            cs, run = ta_classes.classes(rosetta / rel, rs), ta_classes.runnable(rosetta / rel, rs)
        except ta_classes.ERRORS:
            cs, run = {}, False
        return rel, sorted({c for v in cs.values() for c in v}), run
    with ThreadPoolExecutor(max_workers=4) as pool:
        found = {rel: (cs, run) for rel, cs, run in pool.map(one, sorted(held))}
    # the class of an answer that names a corpus label: the class relations on that label's corpus file
    label_files = defaultdict(list)
    for rel, lab in labels.items():
        label_files[ta_corpus.group(lab, groups)].append(rel)
    answer_class = {}

    def class_of_answer(g):
        if g.startswith('Sorting-algorithms-') or g in TASK_CLASS:
            return task_class(g)
        if g not in answer_class:
            cs = set()
            for rel in label_files.get(g, []):
                for v in ta_classes.classes(corpus / rel).values():
                    cs |= v
            answer_class[g] = min(cs) if len(cs) == 1 else g
        return answer_class[g]
    rows, score = {}, defaultdict(lambda: defaultdict(int))
    for rel, res in sorted(held.items()):
        task, lang = res['task'], rel.split('/')[2]
        want = task_class(task)
        cs, run = found[rel]
        algo = res.get('got')
        if algo:
            got_class, how = class_of_answer(algo), 'algorithm'
        elif len(cs) == 1:
            got_class, how = cs[0], 'class_relation'
        else:
            got_class, how = None, ('ambiguous_class' if cs else 'new_class' if run else 'not_run')
        rows[rel] = {'task': task, 'algorithm_answer': algo, 'classes': cs, 'class_answer': got_class, 'how': how}
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s['a_ok' if algo == task else 'a_wrong' if algo else 'a_unknown'] += 1
            s['c_ok' if got_class == want else 'c_wrong' if got_class else 'c_unknown'] += 1
            s[how] += 1
    OUT.write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# Class fallback test (doc 04 section 18): held-out Rosetta files', '',
             ('The algorithm answers of eval_ta.py are kept; an UNKNOWN file is answered by the class relations '
              '(prolog/class_specs.pl) when exactly one holds. Class level: the answer names what the task computes '
              '(a named algorithm counts as its class). Separate from the pipeline (eval_classes.py).'), '',
             ('| language | files | algorithm: correct / wrong / UNKNOWN | precision | recall | class: correct / wrong / '
              'UNKNOWN | precision | recall | answered by class relation | new class (runs, no relation) |'),
             '|---|---|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        ap = s['a_ok'] / max(s['a_ok'] + s['a_wrong'], 1)
        cp = s['c_ok'] / max(s['c_ok'] + s['c_wrong'], 1)
        lines.append(f"| {key} | {s['n']} | {s['a_ok']} / {s['a_wrong']} / {s['a_unknown']} | {ap:.1%} | "
                     f"{s['a_ok'] / s['n']:.1%} | {s['c_ok']} / {s['c_wrong']} / {s['c_unknown']} | {cp:.1%} | "
                     f"{s['c_ok'] / s['n']:.1%} | {s['class_relation']} | {s['new_class']} |")
    wrong = [(r, x) for r, x in rows.items() if x['class_answer'] and x['class_answer'] != task_class(x['task'])]
    lines += ['', f'## Wrong at the class level ({len(wrong)})', '']
    lines += [f"- {r}: {x['class_answer']} ({x['how']}), task {x['task']}" for r, x in wrong]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
