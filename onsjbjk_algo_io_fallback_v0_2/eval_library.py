"""Test of the library-name fallback (doc 04 section 18.1), kept separate from the pipeline. It layers on the class
fallback test (benchmark/class_fallback.json): the algorithm answer of eval_ta.py is kept, then a class relation, then
a library name (ta_library.py), each only where the file is still UNKNOWN. A library name says what is computed, so it
counts at the class level; at the algorithm level only for a task that is that computation (Factorial, gcd), never for
a named sort.
Precision is also checked on every TheAlgorithms/Python file: a library answer there is listed with the file's label.

usage: python eval_library.py CORPUS ROSETTA    -> benchmark/library_fallback.json, benchmark/library_fallback.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import crosslang_frontends
import ta_corpus
import ta_library
from eval_classes import task_class
from ta_corpus import ROOT

CLASSES = ROOT / 'benchmark' / 'class_fallback.json'
OUT, REPORT = ROOT / 'benchmark' / 'library_fallback.json', ROOT / 'benchmark' / 'library_fallback.md'


def answer(path: Path) -> dict:
    try:
        return {fn: list(v) for fn, v in ta_library.answers(path).items()}
    except ta_library.ERRORS:
        return {}


def main():
    corpus, rosetta = Path(sys.argv[1]), Path(sys.argv[2])
    crosslang_frontends.install(lisp_sbcl=False)
    held = json.loads(CLASSES.read_text(encoding='utf-8'))
    labels = ta_corpus.files(corpus)
    with ThreadPoolExecutor(max_workers=4) as pool:
        lib_held = dict(zip(sorted(held), pool.map(lambda r: answer(rosetta / r), sorted(held))))
        lib_corpus = dict(zip(sorted(labels), pool.map(lambda r: answer(corpus / r), sorted(labels))))
    rows, score = {}, defaultdict(lambda: defaultdict(int))
    for rel, x in sorted(held.items()):
        task, lang = x['task'], rel.split('/')[2]
        want = task_class(task)
        algs = sorted({a for _, a in lib_held[rel].values()})
        lib = algs[0] if len(algs) == 1 else None
        got_class, how = x['class_answer'], x['how']
        algo = x['algorithm_answer']
        if got_class is None and lib:
            got_class, how = lib, 'library_name'
            algo = lib if not task.startswith('Sorting-algorithms-') else None
            algo_ok = lib == want
        else:
            algo_ok = algo == task
        rows[rel] = {'task': task, 'library': lib_held[rel], 'class_answer': got_class, 'how': how}
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s['a_ok' if algo and algo_ok else 'a_wrong' if algo else 'a_unknown'] += 1
            s['c_ok' if got_class == want else 'c_wrong' if got_class else 'c_unknown'] += 1
            s[how] += 1
            if lib_held[rel] and how != 'library_name':
                s['lib_not_needed'] += 1
    corpus_claims = {rel: {'label': labels[rel], 'library': v} for rel, v in lib_corpus.items() if v}
    OUT.write_text(json.dumps({'heldout': rows, 'corpus_claims': corpus_claims}, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    lines = ['# Library-name fallback test (doc 04 section 18.1)', '',
             ('Order: algorithm answer (eval_ta.py), then a class relation (class_specs.pl), then a library name '
              '(library_names.pl), each only where the file is still UNKNOWN. Separate from the pipeline '
              '(eval_library.py).'), '',
             ('| language | files | algorithm: correct / wrong / UNKNOWN | precision | recall | class: correct / wrong / '
              'UNKNOWN | precision | recall | answered by library name |'), '|---|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        ap = s['a_ok'] / max(s['a_ok'] + s['a_wrong'], 1)
        cp = s['c_ok'] / max(s['c_ok'] + s['c_wrong'], 1)
        lines.append(f"| {key} | {s['n']} | {s['a_ok']} / {s['a_wrong']} / {s['a_unknown']} | {ap:.1%} | "
                     f"{s['a_ok'] / s['n']:.1%} | {s['c_ok']} / {s['c_wrong']} / {s['c_unknown']} | {cp:.1%} | "
                     f"{s['c_ok'] / s['n']:.1%} | {s['library_name']} |")
    lib_rows = [(r, x) for r, x in rows.items() if x['how'] == 'library_name']
    lines += ['', f'## Held-out files answered by a library name ({len(lib_rows)})', '']
    lines += [f"- {r}: {x['class_answer']} via {x['library']} ({'correct' if x['class_answer'] == task_class(x['task']) else 'WRONG'})"
              for r, x in lib_rows]
    other = [(r, x) for r, x in rows.items() if x['library'] and x['how'] != 'library_name']
    lines += ['', f'## Held-out files with a library answer that was not needed (already answered) ({len(other)})', '']
    lines += [f"- {r}: {x['library']}, answered {x['class_answer']} ({x['how']}), task {x['task']}" for r, x in other]
    lines += ['', f'## TheAlgorithms/Python files with a library answer ({len(corpus_claims)})', '']
    lines += [f"- {r} (label {c['label']}): {c['library']}" for r, c in sorted(corpus_claims.items())]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
