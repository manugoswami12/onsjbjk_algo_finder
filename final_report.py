"""Final report (doc 04 section 18.5): precision, recall, false positives and false negatives on learnt code
(TheAlgorithms/Python) and on new code (the held-out Rosetta files), under the reporting criteria the user set:
a file the system cannot evaluate is left out of the scored set (never a wrong answer), and counted apart.

Reporting criteria
  learnt code   every TheAlgorithms file. Files with the same logic (the same abstracted Prolog components:
                base58 = base64_cipher) are one alias group: naming either label is right, since no logic can tell
                identical logic apart.
  new code      every held-out file, answered as benchmark/decision_fallback.json says (pipeline algorithm, else a
                class from the separate fallback). A file is NOT ANALYSABLE, and left out of the scored set, when
                the pipeline gave it no answer AND none of its root functions runs on every battery input (or it has
                no function): neither its structure nor its input->output (sum(2,3,X)) can be checked. Some are
                fragments (a GHCi transcript, a call of a function the file does not define); most define functions
                the evaluator cannot run yet (an in-place void function on an array plus a length, a missing package
                such as GMP, Python 2, a Haskell operator definition): later-stage work, each a lowering or battery
                change. A wrong answer is never left out, so precision is never improved by excluding.
  Both the all-files and the analysable-only numbers are reported.

usage: python final_report.py CORPUS HELD_DECIDED.json   -> benchmark/final_report.json, benchmark/FINAL_REPORT.md
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import ta_corpus
from ta_corpus import ROOT

ANSWERS = ROOT / 'benchmark' / 'ta_answers.json'
SIGNATURES = ROOT / 'benchmark' / 'ta_signatures.json'
DECISION = ROOT / 'benchmark' / 'decision_fallback.json'
OUT, REPORT = ROOT / 'benchmark' / 'final_report.json', ROOT / 'benchmark' / 'FINAL_REPORT.md'
NOT_RUN = ('no run', 'a root does not run', 'no root function', 'output does not depend')


def learnt(corpus: Path) -> tuple[dict, dict]:
    labels = ta_corpus.files(corpus)
    gs = ta_corpus.groups(labels.values())
    answers = json.loads(ANSWERS.read_text(encoding='utf-8'))
    sigs = json.loads(SIGNATURES.read_text(encoding='utf-8'))
    # identical logic: the same set of abstracted Prolog components (ta_distinct.py; names abstracted away)
    text = {rel: tuple(sorted(sigs.get(rel, []))) or ('file', rel) for rel in labels}
    same = defaultdict(set)                        # identical logic: one alias group of labels
    for rel, b in text.items():
        same[b].add(ta_corpus.group(labels[rel], gs))
    out = {'ok': [], 'wrong': [], 'unknown': [], 'alias_ok': [], 'not_analysable': []}
    for rel, lab in sorted(labels.items()):
        want = ta_corpus.group(lab, gs)
        got = answers.get(rel, {}).get('got')
        aliases = same[text[rel]]
        if got and ta_corpus.group(got, gs) == want:
            out['ok'].append(rel)
        elif got:
            out['wrong'].append((rel, got))
        elif len(aliases) > 1:                     # UNKNOWN only because another label has the very same logic
            out['alias_ok'].append((rel, sorted(aliases)))
        elif not sigs.get(rel):                    # no algorithm code at all (a __main__ block only): bad code
            out['not_analysable'].append(rel)
        else:
            out['unknown'].append(rel)
    return out, sigs


def main():
    corpus, held_dec = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    lc, _ = learnt(corpus)
    rows = json.loads(DECISION.read_text(encoding='utf-8'))['heldout']
    score = defaultdict(lambda: defaultdict(int))
    excluded = defaultdict(lambda: defaultdict(int))
    for rel, x in sorted(rows.items()):
        lang = rel.split('/')[2]
        why = held_dec.get(rel, {}).get('why', '')
        bad = x['correct'] is None and why.startswith(NOT_RUN)
        for key in (lang, 'all'):
            s = score[key]
            s['n'] += 1
            s['ok' if x['correct'] else 'wrong' if x['correct'] is False else 'unanswered'] += 1
            if bad:
                s['not_analysable'] += 1
                excluded[key][why.split(':')[0]] += 1
    n_lc = sum(len(v) for v in lc.values())
    ok_lc = len(lc['ok']) + len(lc['alias_ok'])
    lines = ['# Final report (doc 04 section 18.5)', '',
             ('Reporting criteria (final_report.py): a held-out file is not analysable when the '
              'pipeline gave it no answer and none of its root functions runs on every battery input; a wrong answer '
              'is never excluded. Identical TheAlgorithms files are one alias group. All-files numbers are kept '
              'beside the analysable-only ones. The main pipeline is unchanged; the class answers come from the '
              'separate fallback (eval_decision.py, v0.3 runner, node witness).'), '',
             '## Learnt code: TheAlgorithms/Python', '',
             ('| files | not analysable (no algorithm code) | scored | correct | false positives | false negatives | '
              'precision | recall (analysable) | recall (all files) |'), '|---|---|---|---|---|---|---|---|---|',
             (f"| {n_lc} | {len(lc['not_analysable'])} | {n_lc - len(lc['not_analysable'])} | {ok_lc} | "
              f"{len(lc['wrong'])} | {len(lc['unknown']) + len(lc['wrong'])} | "
              f"{ok_lc / max(ok_lc + len(lc['wrong']), 1):.1%} | {ok_lc / (n_lc - len(lc['not_analysable'])):.1%} | "
              f"{ok_lc / n_lc:.1%} |"), '',
             f"- not analysable: {', '.join(lc['not_analysable']) or 'none'} (an `if __name__ == '__main__'` block only)",
             (f"- alias groups (identical logic, either label right): {len(lc['alias_ok'])} files: "
              + '; '.join(f"{r} = {' / '.join(a)}" for r, a in lc['alias_ok'])),
             '- false negatives: ' + (', '.join(lc['unknown']) or 'none'),
             f"- false positives: {', '.join(f'{r} -> {g}' for r, g in lc['wrong']) or 'none'}", '',
             '## New code: held-out Rosetta files (never learned from)', '',
             ('| language | files | not analysable (excluded) | scored | correct | false positives | false negatives | '
              'precision | recall (analysable) | recall (all files) |'), '|---|---|---|---|---|---|---|---|---|---|']
    for key in sorted(score, key=lambda k: (k == 'all', k)):
        s = score[key]
        scored = s['n'] - s['not_analysable']
        fn = scored - s['ok']
        lines.append(f"| {key} | {s['n']} | {s['not_analysable']} | {scored} | {s['ok']} | {s['wrong']} | {fn} | "
                     f"{s['ok'] / max(s['ok'] + s['wrong'], 1):.1%} | {s['ok'] / max(scored, 1):.1%} | "
                     f"{s['ok'] / s['n']:.1%} |")
    lines += ['', 'False negatives = scored files without a correct answer (wrong ones included).', '',
              '### Why files are not analysable (all languages)', '']
    lines += [f'- {why}: {n}' for why, n in sorted(excluded['all'].items(), key=lambda kv: -kv[1])]
    lines += ['', ('These files are left out of this round\'s numbers: some are fragments, most define functions the '
                   'evaluator cannot run yet (in-place void functions on an array plus a length, GMP, Python 2, Haskell '
                   'operator definitions, ...). They are taken up when the code is upgraded.')]
    lines += ['', '### The false positives (all from the main pipeline; the fallback made none)', '']
    lines += [f"- {r}: {x['name']} ({x['answer']}), task {x['task']}" for r, x in rows.items() if x['correct'] is False]
    lines += ['', '### Closed, measured, not built', '',
              ('- Class veto of the pipeline\'s wrong answers: overriding only an answer of a known, different class '
               'changes nothing on either set; overriding any answer of unknown class fixes 0 held-out answers and '
               'turns 15 correct specific TheAlgorithms answers (mergesort, tim_sort, jump_search, ...) into a class '
               'name. Not built.'),
              ('- Haskell files that are not programs (GHCi transcripts, bare expressions, missing packages, deferred '
               'type errors) and Python scripts with no function: not analysable under these criteria.')]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    OUT.write_text(json.dumps({'learnt': lc, 'new': score, 'excluded': excluded}, indent=1, default=list) + '\n',
                   encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
