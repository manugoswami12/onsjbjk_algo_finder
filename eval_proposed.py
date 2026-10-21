"""Test of the proposed class branches (doc 04 section 18.3), kept separate from the pipeline. The pipeline's own
answers (benchmark/ta_answers.json, benchmark/ta_heldout.json) are kept as they are; a proposed branch
(prolog/proposed_branches.pl, written by tools_manual/write_branches.py from TheAlgorithms files) answers only a file
the pipeline left UNKNOWN, so no pipeline answer can change. A branch answers class C when the file is decided
new_version C (tools_manual/decide_new_or_known.py) and reaches the branch's node or one below it. On TheAlgorithms
files a branch counts only if it was learned from another file (leave-one-out).

usage: python eval_proposed.py HELD_DECIDED.json CORPUS_DECIDED.json   -> benchmark/proposed_fallback.json, .md
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import learn_facts
from eval_classes import task_class
from ta_corpus import ROOT

PROGRAM = ROOT / 'prolog' / 'proposed_branches.pl'
SOURCES = ROOT / 'benchmark' / 'proposed_branches.json'
OUT, REPORT = ROOT / 'benchmark' / 'proposed_fallback.json', ROOT / 'benchmark' / 'proposed_fallback.md'


def applied(dec: dict) -> list[tuple[str, str]]:
    """[(branch node, class)] of the proposed branches that apply to a file decided new_version (Prolog)."""
    if dec.get('decision') != 'new_version' or not dec.get('nodes'):
        return []
    facts = [f'file_node({n!r}).'.replace('"', "'") for n in dec['nodes']] + [f"holds({dec['class']})."]
    with tempfile.TemporaryDirectory(prefix='v02_prop_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text('\n'.join(facts) + '\n', encoding='utf-8')
        out = learn_facts.env_run.swipl('proposed_main', [PROGRAM], [str(f)])
    return [tuple(line.split('|')[1:3]) for line in out if line.startswith('PROPOSED|')]


def answer(dec: dict, sources: dict, own: str | None = None) -> str | None:
    """The one class the applying branches name (branches learned only from `own` left out), else None."""
    cs = {c for n, c in applied(dec) if any(s != own for s in sources[f'{n}|{c}'])}
    return min(cs) if len(cs) == 1 else None


def main():
    held_dec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    corpus_dec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    held = json.loads((ROOT / 'benchmark' / 'ta_heldout.json').read_text(encoding='utf-8'))
    corpus = json.loads((ROOT / 'benchmark' / 'ta_answers.json').read_text(encoding='utf-8'))
    sources = json.loads(SOURCES.read_text(encoding='utf-8'))
    rows, score = {}, defaultdict(lambda: defaultdict(int))
    for rel, res in sorted(held.items()):
        lang, want = rel.split('/')[2], task_class(res['task'])
        br = answer(held_dec.get(rel, {}), sources)
        got = res.get('got')
        if got:
            kind, ok = 'pipeline', got == res['task']
        elif br:
            kind, ok = 'branch', br == want
        else:
            kind, ok = 'unknown', None
        rows[rel] = {'task': res['task'], 'pipeline': got, 'branch': br, 'answer': kind, 'correct': ok,
                     'branch_correct': None if br is None else br == want}
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s[kind] += 1
            if ok is not None:
                s['ok' if ok else 'wrong'] += 1
            if br is not None:
                s['br_fired'] += 1
                s['br_ok' if br == want else 'br_wrong'] += 1
    corpus_rows = {}
    for rel, d in sorted(corpus_dec.items()):
        br = answer(d, sources, own=rel)
        if br:
            corpus_rows[rel] = {'label': corpus.get(rel, {}).get('got'), 'branch': br, 'pipeline_answered': bool(corpus.get(rel, {}).get('got'))}
    OUT.write_text(json.dumps({'heldout': rows, 'corpus': corpus_rows}, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# Proposed class branches (doc 04 section 18.3): held-out Rosetta files', '',
             ('The pipeline answer is kept; a proposed branch (prolog/proposed_branches.pl, learned from TheAlgorithms '
              'files) answers only a file the pipeline left UNKNOWN. Separate from the pipeline (eval_proposed.py).'), '',
             ('| language | files | pipeline answers | branch answers (new) | correct / wrong | precision | recall | '
              'branch fired (all files) | branch right / wrong |'), '|---|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        lines.append(f"| {key} | {s['n']} | {s['pipeline']} | {s['branch']} | {s['ok']} / {s['wrong']} | "
                     f"{s['ok'] / max(s['ok'] + s['wrong'], 1):.1%} | {s['ok'] / s['n']:.1%} | {s['br_fired']} | "
                     f"{s['br_ok']} / {s['br_wrong']} |")
    new = [(r, x) for r, x in rows.items() if x['answer'] == 'branch']
    lines += ['', f'## Held-out files answered by a branch ({len(new)})', '']
    lines += [f"- {r}: {x['branch']} ({'right' if x['correct'] else 'WRONG'}), task {x['task']}" for r, x in new]
    bad = [(r, x) for r, x in rows.items() if x['branch_correct'] is False]
    lines += ['', f'## Branch wrong on any held-out file, answered or not ({len(bad)})', '']
    lines += [f"- {r}: {x['branch']}, task {x['task']}" for r, x in bad]
    lines += ['', f'## TheAlgorithms files a branch learned from other files applies to ({len(corpus_rows)})', '']
    lines += [f"- {r}: {x['branch']} (pipeline answer {x['label']})" for r, x in corpus_rows.items()]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
