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

usage: python eval_decision.py HELD_DECIDED.json CORPUS_DECIDED.json [agree|node|none]
       -> benchmark/decision_fallback.json, .md (agree: node agreement, the default; node: the file reaches a node; none: no second witness)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import ta_corpus
from eval_classes import task_class
from ta_corpus import ROOT

HELDOUT = ROOT / 'benchmark' / 'ta_heldout.json'
LIBRARY = ROOT / 'benchmark' / 'library_fallback.json'
PROPOSED = ROOT / 'benchmark' / 'proposed_fallback.json'
ANSWERS = ROOT / 'benchmark' / 'ta_answers.json'
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
    if WITNESS == 'none':
        return True
    if WITNESS == 'node':
        return bool(dec.get('nodes'))
    return any(same_path(n, m) for f, ms in class_nodes.get(dec['class'], []) if f != own
               for m in ms for n in dec.get('nodes', []))


def answer(res: dict, dec: dict, lib: str | None, class_nodes: dict, branch: str | None = None) -> tuple[str, str | None]:
    """(kind, name) of the file's one answer, in order: algorithm, class (a class relation with its witness, a proposed
    branch, a library name), then the user's rule: a file that reaches a tree node where no rule matched is a variation
    of the family at that node (variation, or variation_root when it reaches only a root node); a file that reaches no
    tree node is an error or a new class (error_or_new)."""
    if res.get('got'):
        return 'algorithm', res['got']
    if dec.get('decision') == 'new_version' and node_agrees(dec, class_nodes):
        return 'class', dec['class']
    if branch:
        return 'class', branch
    if lib:
        return 'class', lib
    nodes = res.get('nodes') or []
    deep = [n for n in nodes if '>' in n]
    if deep:
        return 'variation', max(deep, key=lambda n: (n.count('>'), n))
    if nodes:
        return 'variation_root', min(nodes)
    return 'error_or_new', None


def main():
    held_dec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    corpus_dec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    held = json.loads(HELDOUT.read_text(encoding='utf-8'))
    lib = {r: x['library']['file'] for r, x in json.loads(LIBRARY.read_text(encoding='utf-8'))['heldout'].items()}
    branch = ({r: x['branch'] for r, x in json.loads(PROPOSED.read_text(encoding='utf-8'))['heldout'].items()}
              if PROPOSED.exists() else {})
    corpus_nodes = json.loads(ANSWERS.read_text(encoding='utf-8'))
    task_nodes = {t: [n for rel in rels for n in corpus_nodes.get(rel, {}).get('nodes', [])]
                  for t, rels in ta_corpus.tasks().items()}
    class_nodes = defaultdict(list)
    for rel, d in corpus_dec.items():
        if d.get('decision') == 'new_version':
            class_nodes[d['class']].append((rel, d.get('nodes', [])))
    rows, score = {}, defaultdict(lambda: defaultdict(int))
    for rel, res in sorted(held.items()):
        task, lang = res['task'], rel.split('/')[2]
        kind, name = answer(res, held_dec.get(rel, {}), lib.get(rel), class_nodes, branch.get(rel))
        if kind == 'algorithm':
            ok = name == task
        elif kind == 'class':
            ok = name == task_class(task)
        elif kind in ('variation', 'variation_root'):     # the family is right when TheAlgorithms files of the task
            ok = any(same_path(name, m) for m in task_nodes.get(task, []))   # reach a node on its path
        else:
            ok = None
        rows[rel] = {'task': task, 'answer': kind, 'name': name, 'correct': ok if kind in ('algorithm', 'class') else None,
                     'family_correct': ok if kind.startswith('variation') else None}
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s[kind] += 1
            if ok is not None:
                level = 'fam_' if kind.startswith('variation') else ''
                s[level + kind + ('_ok' if ok else '_wrong') if level else ('ok' if ok else 'wrong')] += 1
    claims = {rel: d['class'] for rel, d in corpus_dec.items()
              if d.get('decision') == 'new_version' and node_agrees(d, class_nodes, own=rel)}
    dropped = sorted(rel for rel, d in corpus_dec.items()
                     if d.get('decision') == 'new_version' and rel not in claims)
    OUT.write_text(json.dumps({'heldout': rows, 'corpus_class_claims': claims}, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    lines = ['# Answer for every held-out file (doc 04 section 18.2): held-out Rosetta files', '',
             ('Each file gets one answer, in order: the algorithm (eval_ta.py); its class (a class relation on runs over '
              'every battery input with a node witness, a proposed branch, or a library name); else the user\'s rule: a '
              'file that reaches a tree node where no rule matched is a variation of the family at that node, and a file '
              'that reaches no tree node is an error or a new class. Separate from the pipeline (eval_decision.py).'), '',
             ('Identified = algorithm or class. A family answer is right when TheAlgorithms files of the task reach a node '
              'on its path; it is reported apart and never counted as identified. A root family (numeric, '
              'sequence_query, sequence_transformation) holds 9+ tasks.'), '',
             ('| language | files | identified: correct / wrong | precision | recall | variation, deep node: right / wrong '
              '| variation, root node only: right / wrong | error or new class (no node) |'),
             '|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        prec = s['ok'] / max(s['ok'] + s['wrong'], 1)
        lines.append(f"| {key} | {s['n']} | {s['ok']} / {s['wrong']} | {prec:.1%} | {s['ok'] / s['n']:.1%} | "
                     f"{s['fam_variation_ok']} / {s['fam_variation_wrong']} | "
                     f"{s['fam_variation_root_ok']} / {s['fam_variation_root_wrong']} | {s['error_or_new']} |")
    wrong = [(r, x) for r, x in rows.items() if x['correct'] is False]
    lines += ['', f'## Wrong answers ({len(wrong)})', '']
    lines += [f"- {r}: {x['answer']} {x['name']}, task {x['task']}" for r, x in wrong]
    fam_wrong = [(r, x) for r, x in rows.items() if x['answer'] == 'variation' and x['family_correct'] is False]
    lines += ['', f'## Variation of a deep family, family wrong ({len(fam_wrong)})', '']
    lines += [f"- {r}: {x['name']}, task {x['task']}" for r, x in fam_wrong]
    news = [(r, x) for r, x in rows.items() if x['answer'] == 'error_or_new']
    lines += ['', (f'## Error or new class: reaches no tree node ({len(news)}; every held-out task is known, so each is a '
                   'program the lowering or interpreter cannot handle)'), '']
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
