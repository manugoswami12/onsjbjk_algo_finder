"""Four-way answer test (doc 04 section 18.2), kept separate from the pipeline. Each held-out file gets one answer:
  algorithm             eval_ta.py names the specific algorithm (benchmark/ta_heldout.json), kept as it is
  class                 a new version of a known class: on the file's root functions, run over every battery input,
                        one class relation holds (tools_manual/decide_new_or_known.py), and the file's tree node is on
                        the path of a node another TheAlgorithms file of that class reaches; or one library name
                        (benchmark/library_fallback.json)
  new_or_incorrect      the program runs on every battery input and no class relation holds: a new algorithm, or an
                        implementation the interpreter computes wrongly; we cannot tell which, and say so
  not_identified        it does not run on every input (or the check did not finish)
The class decision is also listed on every TheAlgorithms/Python file, to check it by hand for false positives.

usage: python eval_decision.py HELD_DECIDED.json CORPUS_DECIDED.json [agree|node]
       -> benchmark/decision_fallback.json, .md (agree: node agreement, the default; node: the file reaches a node)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import ta_corpus  # noqa: F401  (ROOT)
from eval_classes import task_class
from ta_corpus import ROOT

HELDOUT = ROOT / 'benchmark' / 'ta_heldout.json'
LIBRARY = ROOT / 'benchmark' / 'library_fallback.json'
OUT, REPORT = ROOT / 'benchmark' / 'decision_fallback.json', ROOT / 'benchmark' / 'decision_fallback.md'
WITNESS = sys.argv[3] if len(sys.argv) > 3 else 'agree'


def same_path(a: str, b: str) -> bool:
    """Two tree nodes on one path: equal, or one is an ancestor of the other."""
    return a == b or a.startswith(b + '>') or b.startswith(a + '>')


def node_agrees(dec: dict, class_nodes: dict[str, list[tuple[str, list[str]]]], own: str | None = None) -> bool:
    """The file's structure is a second witness for its class: one of its tree nodes is on the path of a node that
    another TheAlgorithms file of the same class reaches (own: the corpus file itself, left out). With WITNESS = 'node'
    the file need only reach some tree node (a class relation that held on a program with no structure at all, such as
    average_mode computed wrongly, is dropped; a class with no clean TheAlgorithms file keeps its answers)."""
    if WITNESS == 'node':
        return bool(dec.get('nodes'))
    return any(same_path(n, m) for f, ms in class_nodes.get(dec['class'], []) if f != own
               for m in ms for n in dec.get('nodes', []))


def answer(res: dict, dec: dict, lib: str | None, class_nodes: dict) -> tuple[str, str | None]:
    """(kind, name) of the file's one answer, in order: algorithm, class, new_or_incorrect, not_identified."""
    if res.get('got'):
        return 'algorithm', res['got']
    if dec.get('decision') == 'new_version' and node_agrees(dec, class_nodes):
        return 'class', dec['class']
    if lib:
        return 'class', lib
    if dec.get('decision') == 'new_algorithm':
        return 'new_or_incorrect', None
    return 'not_identified', None


def main():
    held_dec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    corpus_dec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    held = json.loads(HELDOUT.read_text(encoding='utf-8'))
    lib = {r: x['library']['file'] for r, x in json.loads(LIBRARY.read_text(encoding='utf-8'))['heldout'].items()}
    class_nodes = defaultdict(list)
    for rel, d in corpus_dec.items():
        if d.get('decision') == 'new_version':
            class_nodes[d['class']].append((rel, d.get('nodes', [])))
    rows, score = {}, defaultdict(lambda: defaultdict(int))
    for rel, res in sorted(held.items()):
        task, lang = res['task'], rel.split('/')[2]
        kind, name = answer(res, held_dec.get(rel, {}), lib.get(rel), class_nodes)
        if kind == 'algorithm':
            ok = name == task
        elif kind == 'class':
            ok = name == task_class(task)
        else:
            ok = None
        rows[rel] = {'task': task, 'answer': kind, 'name': name, 'correct': ok}
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s[kind] += 1
            if ok is not None:
                s['ok' if ok else 'wrong'] += 1
    claims = {rel: d['class'] for rel, d in corpus_dec.items()
              if d.get('decision') == 'new_version' and node_agrees(d, class_nodes, own=rel)}
    dropped = sorted(rel for rel, d in corpus_dec.items()
                     if d.get('decision') == 'new_version' and rel not in claims)
    OUT.write_text(json.dumps({'heldout': rows, 'corpus_class_claims': claims}, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    lines = ['# Four-way answer test (doc 04 section 18.2): held-out Rosetta files', '',
             ('Each file gets one answer: the algorithm (eval_ta.py), else its class (a class relation on runs over every '
              'battery input, or a library name), else "new or incorrect implementation" (runs fully, no relation), '
              'else "not identified". Separate from the pipeline (eval_decision.py).'), '',
             ('| language | files | algorithm | class | correct / wrong (algorithm + class) | precision | identified '
              '(recall) | new or incorrect | not identified | answered (any of the four but not identified) |'),
             '|---|---|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        prec = s['ok'] / max(s['ok'] + s['wrong'], 1)
        lines.append(f"| {key} | {s['n']} | {s['algorithm']} | {s['class']} | {s['ok']} / {s['wrong']} | {prec:.1%} | "
                     f"{s['ok'] / s['n']:.1%} | {s['new_or_incorrect']} | {s['not_identified']} | "
                     f"{(s['n'] - s['not_identified']) / s['n']:.1%} |")
    wrong = [(r, x) for r, x in rows.items() if x['correct'] is False]
    lines += ['', f'## Wrong answers ({len(wrong)})', '']
    lines += [f"- {r}: {x['answer']} {x['name']}, task {x['task']}" for r, x in wrong]
    news = [(r, x) for r, x in rows.items() if x['answer'] == 'new_or_incorrect']
    lines += ['', (f'## "New or incorrect implementation" ({len(news)}; every held-out task is known, so each is an '
                   'implementation we cannot check)'), '']
    lines += [f"- {r} (task {x['task']})" for r, x in news]
    by_class = defaultdict(list)
    for rel, c in claims.items():
        by_class[c].append(rel)
    lines += ['', f'## Class decisions on TheAlgorithms/Python files ({len(claims)}), to check by hand', '']
    for c in sorted(by_class):
        lines.append(f"- **{c}** ({len(by_class[c])}): " + ', '.join(sorted(by_class[c])))
    lines += ['', f'## Class decisions on TheAlgorithms/Python files dropped by node agreement ({len(dropped)})', '']
    lines += [f"- {r}: {corpus_dec[r]['class']}, nodes {corpus_dec[r].get('nodes')}" for r in dropped]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
