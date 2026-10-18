"""TheAlgorithms/Python, every file (doc 04 section 17): learn each algorithm, test whether it was learned, and
list what needs a hand-written rule, with a prompt to write it.

usage: python eval_ta.py CORPUS --learn                      learn every labelled file -> prolog/learned_ta.pl
       python eval_ta.py CORPUS --run [--dir sorts ...]      answer every file -> benchmark/ta_answers.json
       python eval_ta.py CORPUS --heldout ROSETTA            answer the Rosetta files of the mapped tasks
       python eval_ta.py CORPUS --status                     T1/T2/T3 per label -> benchmark/ta_status.json,
                                                             benchmark/ta_result.md, benchmark/hand_rule_prompts.jsonl
The answer of a file is a group (ta_corpus.group): a built branch of the tree that names one algorithm, else the
learned branches holding at its deepest node with the write trace of their training files, else those holding with
the behaviour, else the input->output fallback; the first of these that names anything decides, and when it names
several groups the answer is UNKNOWN. Tests per label:
  T1 self       its own file is answered with its group (weak: the file's own behaviour is in the catalog)
  T2 confusion  no file of another group is answered with its group
  T3 held-out   the Rosetta files (any language) of its task are answered with its group (only mapped labels)
Candidate source never runs: the behaviour is the Prolog normal form run in SWI-Prolog (AP13 io_trace).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import compare_learners
import crosslang_frontends
import ecl_logic
import learn_apply
import ta_corpus
from ta_corpus import ROOT

RULES = ROOT / 'prolog' / 'learned_ta.pl'
BENCH = ROOT / 'benchmark'
ANSWERS, HELDOUT = BENCH / 'ta_answers.json', BENCH / 'ta_heldout.json'
STATUS, RESULT, PROMPTS = BENCH / 'ta_status.json', BENCH / 'ta_result.md', BENCH / 'hand_rule_prompts.jsonl'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError, subprocess.SubprocessError)
HELDOUT_LANGS = ('Python', 'C', 'Common-Lisp', 'Haskell')


class TaIo(compare_learners.IoCatalog):
    """AP13's behaviour catalog of the corpus, its references indexed by signature (same comparison)."""

    def __init__(self, corpus: Path, labels: dict[str, str], workers=4):
        with tempfile.TemporaryDirectory(prefix='v02_ta_') as td:
            truth = Path(td) / 'train.json'
            truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
            super().__init__(corpus, [truth], workers)
        self.by_sig = defaultdict(list)
        for key, ref in self.cat.items():
            self.by_sig[(tuple(ref['sig']), len(ref['outputs']))].append((key, ref))
        self.ints = [(k, r) for k, r in self.cat.items() if r['sig'] == ['int']]

    def labels_by_function(self, path, me=None):
        return self.labels_by_kind(path, me)[0]

    def labels_by_kind(self, path, me=None):
        """({function: labels with equal behaviour}, {function: labels with an equal write trace too ('logic')})."""
        if me is None:
            me = self.describe(path)
        out, traced = {}, {}
        for name, d in me.items():
            if not d['discriminative']:
                continue
            refs = self.by_sig[(tuple(d['sig']), len(d['outputs']))]
            for (rel, _), ref in refs:
                how = self.ioc.compare(d, ref)
                if how in ('logic', 'io'):
                    out.setdefault(name, set()).add(self.labels[rel])
                if how == 'logic':
                    traced.setdefault(name, set()).add(self.labels[rel])
            if d['sig'] == ['int']:
                for (rel, _), ref in self.ints:
                    if compare_learners.shifted_sequence(d, ref):
                        out.setdefault(name, set()).add(self.labels[rel])
        return out, traced


class TaLogic(compare_learners.Ap13Dir):
    """AP13 learn-dir over the corpus: every function's traced logic stored as an exact Prolog reference (scratch
    store); a file matches the labels of the references its functions match (AP13 scan, leaf MATCH). The scan names
    the matching functions by name (compare_learners.Ap13Dir.labels_by_function looks them up by id and finds none)."""

    def labels_matched(self, path: Path) -> set[str]:
        try:
            result = self.cli.scan(path, self.store, include_unreviewed=True, quiet=True)
        except ERRORS + compare_learners.ERRORS:
            return set()
        return {self.labels[self.ref_file[m['label']]] for m in result['leaves']
                if m['result'] == 'MATCH' and self.ref_file.get(m['label']) in self.labels} - {'none'}


def answer(path: Path, io: TaIo, labels: set[str], gs: dict[str, str], logic: TaLogic | None = None) -> dict:
    """{'got': group or None, 'why': built|learned|io|ambiguous|none|no_algorithm, ...} of one file."""
    if path.suffix == '.lisp' and ecl_logic.NOCODE in ecl_logic.families(path):
        return {'got': None, 'why': 'no_algorithm'}
    if path.suffix != '.lisp' and not learn_apply.learn_facts.defines_code(path):
        return {'got': None, 'why': 'no_algorithm'}
    try:
        by_fn, traced = io.labels_by_kind(path, io.describe(path))
    except ERRORS:
        by_fn, traced = {}, {}
    io_labels = {lab for v in by_fn.values() for lab in v} & labels
    trace_labels = {lab for v in traced.values() for lab in v} & labels
    logic_labels = logic.labels_matched(path) & labels if logic else set()
    try:
        hand = set()
        nodes, found, _, normal = learn_apply.apply(path, RULES, io_labels, trace_labels, logic_labels, hand)
    except ERRORS as exc:
        nodes, found, normal, hand = [], [], set(), set()
        print(f'  ({path.name}: {type(exc).__name__}: {str(exc)[:100]})', flush=True)
    built = {ta_corpus.group(b, gs) for b in normal | hand if b in ta_corpus.BUILT or b in labels}
    held = sorted({lab for _, lab, r in found if r == 'io'})
    held_trace = sorted({lab for _, lab, r in found if r in ('trace', 'logic')})
    out = {'nodes': nodes, 'built': sorted(built), 'held': held, 'held_trace': held_trace, 'io': sorted(io_labels),
           'logic': sorted(logic_labels)}
    # the most specific evidence that holds decides: a built branch; a learned branch with an exact trace (the write
    # trace of the training files' behaviour, or their exact traced logic: AP13 learn-dir); a learned branch with the
    # behaviour; the behaviour alone
    for why, cands in (('built', built), ('trace', {ta_corpus.group(h, gs) for h in held_trace}),
                       ('learned', {ta_corpus.group(h, gs) for h in held}),
                       ('io', {ta_corpus.group(i, gs) for i in io_labels})):
        if len(cands) == 1:
            return {**out, 'got': next(iter(cands)), 'why': why}
        if cands:
            return {**out, 'got': None, 'why': 'ambiguous', 'clash': sorted(cands), 'at': why}
    return {**out, 'got': None, 'why': 'none'}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def answer_all(units: dict[str, Path], corpus: Path, labels: dict[str, str], out: Path, workers: int):
    gs = ta_corpus.groups(labels.values())
    crosslang_frontends.install(lisp_sbcl=False)
    io = TaIo(corpus, labels, workers)
    with tempfile.TemporaryDirectory(prefix='v02_ta_') as td:
        truth = Path(td) / 'train.json'
        truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
        logic = TaLogic(corpus, [truth], workers)
    done = load(out)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (rel, res) in enumerate(pool.map(lambda kv: (kv[0], answer(kv[1], io, set(labels.values()), gs, logic)),
                                                sorted(units.items())), 1):
            done[rel] = res
            if n % 100 == 0:
                print(f'{n}/{len(units)}', flush=True)
                out.write_text(json.dumps(done, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    out.write_text(json.dumps(done, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{len(units)} answered -> {out}')


def heldout_units(rosetta: Path) -> dict[str, str]:
    """{rosetta-relative file: Rosetta task} for the mapped tasks' files in the languages answered."""
    out = {}
    for task, rels in ta_corpus.tasks().items():
        if not rels:
            continue
        for lang in HELDOUT_LANGS:
            for p in sorted((rosetta / 'Task' / task / lang).glob('*')):
                if p.suffix in ('.py', '.c', '.lisp', '.hs'):
                    out[p.relative_to(rosetta).as_posix()] = task
    return out


def status(labels: dict[str, str]):
    """T1/T2/T3 per label, the status table, and one hand-rule prompt per label not learned."""
    gs = ta_corpus.groups(labels.values())
    answers, held = load(ANSWERS), load(HELDOUT)
    by_label = defaultdict(list)
    for rel, lab in labels.items():
        by_label[lab].append(rel)
    claimed = defaultdict(list)                      # group -> files of other groups answered with it
    for rel, res in answers.items():
        if res.get('got') and rel in labels and res['got'] != ta_corpus.group(labels[rel], gs):
            claimed[res['got']].append(rel)
    task_files = defaultdict(list)
    for rel, res in held.items():
        task_files[res['task']].append((rel, res))
    rows = {}
    for lab, rels in sorted(by_label.items()):
        g = ta_corpus.group(lab, gs)
        res = [answers.get(r, {}) for r in rels]
        if all(x.get('why') == 'no_algorithm' for x in res):
            rows[lab] = {'files': rels, 'status': 'ignored', 'reason': 'no algorithm code'}
            continue
        if not all(x for x in res):
            rows[lab] = {'files': rels, 'status': 'not_run'}
            continue
        t2 = sorted(claimed.get(g, []))
        t3 = [(r, x.get('got')) for r, x in task_files.get(g, [])]
        t3_ok = sum(got == g for _, got in t3)
        t3_wrong = [(r, got) for r, got in t3 if got and got != g]
        why = sorted({x.get('why') for x in res})
        failed = [(r, x) for r, x in zip(rels, res) if x.get('got') != g]
        kinds = sorted({failure_kind(x) for _, x in failed}
                       | ({'claimed'} if t2 else set()) | ({'heldout'} if t3 and (t3_wrong or not t3_ok) else set()))
        if kinds:
            kind = 'not_learned'
        elif 'built' in why:
            kind = 'hand_rule'
        else:
            kind = 'learned_heldout' if t3 else 'learned_self'
        reason = '; '.join(filter(None, [
            'T1 ' + ', '.join(f"{r}: {x.get('why')}" + (f" {x.get('clash', [])[:6]}" if x.get('clash') else '')
                              for r, x in failed) if failed else None,
            f'T2 claimed by {len(t2)} other file(s): {t2[:5]}' if t2 else None,
            f'T3 {t3_ok}/{len(t3)} held-out, wrong {t3_wrong[:3]}' if 'heldout' in kinds else None])) or None
        rows[lab] = {'files': rels, 'group': g, 'status': kind, 'how': why, 'kinds': kinds,
                     'nodes': sorted({n for x in res for n in x.get('nodes', [])}),
                     'clash': sorted({c for _, x in failed for c in x.get('clash', [])}),
                     'T1': not failed, 'T2_false': t2, 'T3': f'{t3_ok}/{len(t3)}' if t3 else '-', 'reason': reason}
    STATUS.write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    write_prompts(rows)
    write_result(rows)


def failure_kind(x: dict) -> str:
    """Why a file is not answered with its label: no_logic (no tree node, no runnable behaviour), no_behaviour (a
    node but no behaviour to learn), clash (several labels hold), wrong (another label holds)."""
    if x.get('why') == 'ambiguous':
        return 'clash'
    if x.get('got'):
        return 'wrong'
    return 'no_behaviour' if x.get('nodes') else 'no_logic'


# one prompt per failure kind: run it for a label to write its rule by hand (one or two relations usually do)
KIND_PROMPTS = {
    'no_logic': "The logic of {files} is not traced: no tree node and no runnable behaviour. Dump its facts "
                "(prolog/tree_main.pl via learn_facts.tree_facts) and find the component the lowering drops or the tree "
                "has no branch for. If a front end drops it, extend the v0.2 subclass (imperative_logic.py, "
                "haskell_logic.py) so the same component gives the same term in every language; else add one family "
                "path in prolog/families_v02.pl for the component that makes it {label}.",
    'no_behaviour': "{files} reaches {nodes} but has no behaviour to learn (its normal form does not run on the "
                    "battery). Write one or two relations at {nodes} in prolog/families_v02.pl on the component that "
                    "makes it {label} (a relation over the normal form, never over spelling), map it in "
                    "prolog/family_to_v02.pl as {label}.",
    'clash': "{files} reaches {nodes}, where {clash} hold too with the same behaviour and write trace. Write one or two "
             "relations in prolog/families_v02.pl that hold on what makes it {label} and not on {clash} (read their "
             "files side by side: the loop shape, the exchanged positions, the recursion), map it in "
             "prolog/family_to_v02.pl as {label}.",
    'wrong': "{files} is answered with another label. Find the relation or learned branch that holds wrongly and "
             "tighten it with the component that the other algorithm has and {label} lacks.",
    'claimed': "Files of other algorithms ({claimed}) are answered as {label}. Tighten the rule that names {label} "
               "with a component those files lack; keep {files} recognised.",
    'heldout': "Rosetta implementations of {group} are not recognised ({t3}). Dump their facts next to {files}; where "
               "a front end gives a different term for the same component, fix the front end; else add one relation "
               "that holds on both forms.",
}
COMMON = (" Add an own Python positive, an own program in another language and a close negative to "
          "tests/test_uniform.py. Rerun `eval_ta.py CORPUS --run --dir {folder}` and `--status`; keep the rule only "
          "if no other label loses (T2) and the staged run (eval_learn.py --stage 101) does not drop.")


def prompt_for(lab, r):
    fill = {'label': lab, 'files': ' and '.join(r['files']), 'nodes': ', '.join(r['nodes']) or 'the root',
            'clash': ', '.join(r['clash'][:6]) or '-', 'claimed': ', '.join(r['T2_false'][:5]),
            'group': r['group'], 't3': r['T3'], 'folder': r['files'][0].split('/')[0]}
    return ' '.join(KIND_PROMPTS[k].format(**fill) for k in r['kinds']) + COMMON.format(**fill)


def write_prompts(rows):
    todo = {lab: r for lab, r in sorted(rows.items()) if r['status'] == 'not_learned'}
    PROMPTS.write_text(''.join(json.dumps({'label': lab, 'files': r['files'], 'nodes': r['nodes'], 'kinds': r['kinds'],
                                           'why': r['reason'], 'prompt': prompt_for(lab, r)}, sort_keys=True) + '\n'
                               for lab, r in todo.items()), encoding='utf-8')
    by_kind = defaultdict(list)
    for lab, r in todo.items():
        by_kind[r['kinds'][0]].append((lab, r))
    out = ['# Hand-rule prompts (TheAlgorithms/Python, doc 04 section 17)', '',
           ('Run these prompts in future to write rules by hand: for most labels one or two relations will work. '
           'Each label below was not learned (T1 own file, T2 no other file claims it, T3 held-out Rosetta files). '
           'Generated by `eval_ta.py --status`; the full prompt of every label is one line of '
           '`benchmark/hand_rule_prompts.jsonl`.'), '',
           '## Prompt per failure kind', '']
    for k, text in KIND_PROMPTS.items():
        out += [f'### {k} ({len(by_kind.get(k, []))} labels)', '', '> ' + text + COMMON, '']
    out += ['## Labels', '']
    for k in KIND_PROMPTS:
        if not by_kind.get(k):
            continue
        out += [f'### {k}', '', '| label | file(s) | node | clashes with |', '|---|---|---|---|']
        out += [f"| {lab} | {', '.join(r['files'])} | {', '.join(r['nodes']) or 'root'} | "
                f"{', '.join(r['clash'][:4])} |" for lab, r in by_kind[k]]
        out.append('')
    (ROOT / 'docs' / 'HAND_RULE_PROMPTS.md').write_text('\n'.join(out), encoding='utf-8')


def write_result(rows):
    per_dir = defaultdict(lambda: defaultdict(int))
    for r in rows.values():
        per_dir[r['files'][0].split('/')[0]][r['status']] += 1
    kinds = ('learned_heldout', 'learned_self', 'hand_rule', 'not_learned', 'ignored', 'not_run')
    total = {k: sum(d[k] for d in per_dir.values()) for k in kinds}
    out = ['# TheAlgorithms/Python: learned, hand rule, not learned (doc 04 section 17)', '',
           (f'Corpus TheAlgorithms/Python at {ta_corpus.COMMIT[:8]}; one label per file stem; '
           f'{len(rows)} labels. Generated by `eval_ta.py --status`; every label is in `ta_status.json`.'), '',
           ('T1 (its own file is answered with its label) is a weak test: the file\'s own behaviour is in the catalog. '
           'T2 (no other file is answered with it) and T3 (held-out Rosetta files, mapped tasks only) are the real '
           'tests. learned_heldout: T1, T2 and T3 pass; learned_self: T1 and T2 pass, no held-out file exists, so '
           'it is not shown to generalise; hand_rule: a built relation answers it and the tests pass.'), '',
           '| folder | ' + ' | '.join(kinds) + ' |', '|---|' + '---|' * len(kinds)]
    out += [f"| {d} | " + ' | '.join(str(per_dir[d][k]) for k in kinds) + ' |' for d in sorted(per_dir)]
    out += ['| **all** | ' + ' | '.join(f'**{total[k]}**' for k in kinds) + ' |', '']
    out += ['## Labels with a held-out test (T3)', '', '| label | status | T3 | reason |', '|---|---|---|---|']
    out += [f"| {lab} | {r['status']} | {r['T3']} | {r.get('reason') or ''} |" for lab, r in sorted(rows.items())
            if r.get('T3', '-') != '-']
    RESULT.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('\n'.join(out[: 9 + len(per_dir) + 2]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('--learn', action='store_true')
    p.add_argument('--run', action='store_true')
    p.add_argument('--dir', nargs='*', help='folders to (re)answer; all when absent')
    p.add_argument('--heldout', type=Path, metavar='ROSETTA')
    p.add_argument('--status', action='store_true')
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    labels = ta_corpus.files(a.corpus)
    if a.learn:
        count = learn_apply.learn({a.corpus / r: lab for r, lab in labels.items()}, RULES, a.workers,
                                  name=lambda path: path.relative_to(a.corpus).as_posix())
        print(f'learned from {len(labels)} files ({sum(1 for v in count.values() if v)} reach a tree node) -> {RULES}')
    if a.run:
        units = {r: a.corpus / r for r in labels if not a.dir or r.split('/')[0] in a.dir}
        answer_all(units, a.corpus, labels, ANSWERS, a.workers)
    if a.heldout:
        tasks = heldout_units(a.heldout)
        answer_all({r: a.heldout / r for r in tasks}, a.corpus, labels, HELDOUT, a.workers)
        held = load(HELDOUT)
        for r, t in tasks.items():
            held[r]['task'] = t
        HELDOUT.write_text(json.dumps(held, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    if a.status:
        status(labels)


if __name__ == '__main__':
    main()
