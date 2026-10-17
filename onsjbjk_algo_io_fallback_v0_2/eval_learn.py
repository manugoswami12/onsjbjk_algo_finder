"""Learning test (doc 04): learn new algorithms from Python, recognise them in unseen Lisp, C, Haskell.

usage: python eval_learn.py <rosetta checkout> --learn [--staged]   (learn from the Python training files)
       python eval_learn.py <rosetta checkout> --lang Common-Lisp|C|Haskell|hard          (round 1)
       python eval_learn.py <rosetta checkout> --stage 3|15|55|101                       (round 2)
Frozen keys benchmark/learn_truth.json (round 1), benchmark/learn_staged_truth.json (round 2). A unit is a file; its answer is the learned branches that hold at
the deepest tree node it reaches (tagged learned:Label:Rule@Node), or, when none holds, the labels of the
training functions with equal input->output behaviour (tagged io). Success per language: precision and recall >= 80 %.
"""
import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path

import compare_learners
import crosslang_frontends
import ecl_logic
import learn_apply
from run_v2 import ROOT

ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError, subprocess.SubprocessError)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('rosetta', type=Path)
    p.add_argument('--learn', action='store_true')
    p.add_argument('--freeze', action='store_true')
    p.add_argument('--staged', action='store_true', help='round 2: learn from the staged key\'s training files')
    p.add_argument('--lang', choices=['Common-Lisp', 'C', 'Haskell', 'hard'])
    p.add_argument('--stage', choices=['3', '15', '55', '101'])
    a = p.parse_args()
    key = json.loads((ROOT / 'benchmark' / 'learn_truth.json').read_text(encoding='utf-8'))
    staged = json.loads((ROOT / 'benchmark' / 'learn_staged_truth.json').read_text(encoding='utf-8'))
    if a.freeze:
        return freeze(a.rosetta, key)
    if a.learn:
        train_key = (staged if a.staged else key)['train']
        train = {a.rosetta / f: None for f in train_key['negatives']}
        train.update({a.rosetta / f: lab for f, lab in train_key['hard_case_positives'].items()})
        train.update({a.rosetta / f: lab for f, lab in train_key['positives'].items()})
        if a.staged:                              # augmented Python examples (doc 04 section 11)
            train.update({ROOT / f: lab for f, lab in augment().items()})
        count = learn_apply.learn(train)
        print(f'learned from {len(train)} Python files ({sum(1 for v in count.values() if v)} with streams) '
              f'-> {learn_apply.RULES}')
        return None
    if a.lang == 'hard':
        return hard_cases(a, key)
    if a.stage:
        units = {u: staged['units'][u] for u in staged['stages'][a.stage]}
        return score(a.rosetta, units, set(key['new_tasks'].values()), io_references(a.rosetta, staged),
                     f'stage {a.stage} (Python, Common-Lisp, C, Haskell)')
    return score(a.rosetta, key['tests'][a.lang]['units'], set(key['new_tasks'].values()),
                 io_references(a.rosetta, key), a.lang)


def answer(path, labels, io):
    """(labels, tags, learnable): the learned labels holding at the file's deepest node, else the io
    fallback; learnable: the labels some learned rule could recognise in this file (a branch at its node,
    or a runnable Python reference while the file itself has a behaviour). None when the file has no
    algorithm of its own (a Lisp file defining no function: output zero)."""
    if path.suffix == '.lisp' and ecl_logic.NOCODE in ecl_logic.families(path):
        return None
    me = io.describe(path)                        # the file's input->output behaviour (AP13 io_catalog)
    try:
        by_fn = io.labels_by_function(path, me)
    except ERRORS:
        by_fn = {}
    io_labels = {lab for v in by_fn.values() for lab in v} & labels
    try:
        nodes, found, branch_at = learn_apply.apply(path, io_labels=io_labels)
    except ERRORS as exc:
        print(f'  ({path.name}: {type(exc).__name__}: {str(exc)[:100]})')
        nodes, found, branch_at = [], [], set()
    runnable = {io.labels[rel] for rel, _ in io.cat} if any(d['discriminative'] for d in me.values()) else set()
    learnable = (branch_at | runnable) & labels
    got = {lab for _, lab, _ in found} & labels
    tags = [f"[{' '.join(nodes) or 'root'}]"] + sorted(f'learned:{lab}:{r}@{c or "root"}' for c, lab, r in found)
    if len(got) > 1:                              # several learned rules hold: no guess
        return set(), tags + ['ambiguous'], learnable
    if got:
        return got, tags, learnable
    return io_labels, tags + sorted(f'io:{lab}' for lab in io_labels), learnable   # the input->output fallback


def score(rosetta, units, labels, io, title):
    """Precision over every answer; recall over the learnable positives (doc 04 section 10: without a
    usable Python example nothing can be learned), the full-key recall printed beside it."""
    correct = answered = positives = wrong_neg = ignored = learnable_pos = learnable_ok = 0
    not_learnable = []
    for rel, expected in units.items():
        res = answer(rosetta / rel, labels, io)
        name = rel.split('/')[-1][:44]
        if res is None:
            ignored += 1
            print(f"{name:44s} {str(expected)[:22]:22s} ignored(0) no algorithm in the file")
            continue
        got, tags, learnable = res
        if expected is None:
            bad = bool(got)
            outcome, wrong_neg, answered = ('WRONG' if bad else 'ok(neg)'), wrong_neg + bad, answered + bad
        else:
            positives += 1
            answered += bool(got)
            outcome = 'ok' if expected in got else ('WRONG' if got else 'UNKNOWN')
            correct += outcome == 'ok'
            if expected in learnable:
                learnable_pos += 1
                learnable_ok += outcome == 'ok'
            else:
                not_learnable.append(name)
                tags = tags + ['not-learnable']
        print(f"{name:44s} {str(expected)[:22]:22s} {outcome:8s} {' '.join(tags) or '-'}")
    prec, rec = correct / max(answered, 1), learnable_ok / max(learnable_pos, 1)
    print(f'\nlearned from Python, tested on {title}: {len(units)} units, {ignored} ignored (no algorithm)')
    print(f'PRECISION = {correct}/{answered} = {prec:.1%}')
    print(f'RECALL    = {learnable_ok}/{learnable_pos} = {rec:.1%} (learnable positives)')
    print(f'RECALL (full key) = {correct}/{positives} = {correct / max(positives, 1):.1%}')
    print(f'NOT LEARNABLE = {len(not_learnable)}: {", ".join(not_learnable) or "-"}')
    print(f'WRONG ON NEGATIVES = {wrong_neg} of {len(units) - positives - ignored}')
    print('STAGE', 'PASS' if prec >= 0.8 and rec >= 0.8 else 'FAIL')


def freeze(rosetta, key, seed=20261019):
    """Staged key, written once before any learning: about a third of each new task's Python files is held
    out as unseen Python tests (a task with one file stays training only), with as many Python negatives
    from other tasks that are not training negatives; with the Lisp, C and Haskell test files of the round-1
    key, positives and negatives shuffled (seeded) and interleaved; stages are the first 3/15/55/101 units."""
    out = ROOT / 'benchmark' / 'learn_staged_truth.json'
    if out.exists():
        raise SystemExit(f'{out} is frozen')
    rng = random.Random(seed)
    by_task = {}
    for rel, lab in sorted(key['train']['positives'].items()):
        by_task.setdefault(lab, []).append(rel)
    held = {rel: lab for lab, fs in sorted(by_task.items()) for rel in rng.sample(fs, len(fs) // 3)}
    if any(len(fs) >= 2 and not set(fs) & set(held) for fs in by_task.values()):
        held.update({fs[0]: lab for lab, fs in by_task.items() if len(fs) >= 2 and not set(fs) & set(held)})
    tasks = set(key['new_tasks']) | {r.split('/')[1] for r in key['train']['hard_case_positives']}
    # unseen negatives: the Python files of 30 seeded other tasks of the checkout (sparse: fetched here)
    names = subprocess.run(['git', '-C', str(rosetta), 'ls-tree', '--name-only', 'HEAD', 'Task/'], check=True,
                           capture_output=True, text=True).stdout.split()
    present = {p.parts[-3] for p in (rosetta / 'Task').glob('*/Python')}
    picked = rng.sample(sorted(n for n in names if n.split('/')[1] not in tasks | present), 30)
    subprocess.run(['git', '-C', str(rosetta), 'sparse-checkout', 'add', *[f'{n}/Python' for n in picked]], check=True)
    others = sorted(p.relative_to(rosetta).as_posix() for n in picked for p in (rosetta / n).glob('Python/*.py'))
    units = {**held, **{rel: None for rel in rng.sample(others, len(held))}}
    for lang in ('Common-Lisp', 'C', 'Haskell'):
        units.update(key['tests'][lang]['units'])
    pos, neg = sorted(u for u in units if units[u]), sorted(u for u in units if not units[u])
    rng.shuffle(pos)
    rng.shuffle(neg)
    order = [u for pair in zip(pos, neg) for u in pair] + pos[len(neg):] + neg[len(pos):]   # every stage ~half positive
    staged = {
        '_source': 'Staged learning test (docs/04_LEARNING_DESIGN.md, round 2). Learned from Python only: the '
                   'round-1 training files minus the held-out Python tests. Units: the held-out Python files of '
                   'the 12 new tasks plus as many unseen Python negatives, and the Common-Lisp, C and Haskell test '
                   'units of benchmark/learn_truth.json. Stages are the first 3/15/55/101 units of seeded '
                   'shuffles of the positives and negatives, interleaved. Frozen and committed before any learning.',
        'seed': seed,
        'train': {'positives': {r: lab for r, lab in key['train']['positives'].items() if r not in held},
                  'negatives': key['train']['negatives'],
                  'hard_case_positives': key['train']['hard_case_positives']},
        'units': {u: units[u] for u in order},
        'stages': {str(n): order[:n] for n in (3, 15, 55, 101)},
    }
    out.write_text(json.dumps(staged, indent=1) + '\n', encoding='utf-8')
    print(f'{out}: {len(held)} held-out Python positives, {len(units)} units')


def io_references(rosetta, key):
    """AP13 behaviour catalog of the Python training positives (their Prolog normal form is run in
    SWI-Prolog on a fixed battery; nothing of the source runs). Haskell's behaviour front end is GHC Core;
    Lisp keeps AP13's own translator."""
    crosslang_frontends.install(lisp_sbcl=False)
    labels = {**key['train']['hard_case_positives'], **key['train']['positives']}
    if key.get('stages'):                         # the staged key: with the augmented examples (absolute paths)
        labels.update({str(ROOT / f): lab for f, lab in augment().items()})
    with tempfile.TemporaryDirectory(prefix='v02_io_') as td:
        truth = Path(td) / 'train.json'
        truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
        return compare_learners.IoCatalog(rosetta, [truth])


def augment():
    """{repo-relative path: label} of the augmented Python training examples (benchmark/learn_augment.json)."""
    return json.loads((ROOT / 'benchmark' / 'learn_augment.json').read_text(encoding='utf-8'))['files']


def hard_cases(a, key):
    """Known tasks the normal process misses: the normal answer first, then the learned rules."""
    for rel, expected in sorted(key['hard_cases'].items()):
        path = a.rosetta / rel
        fams = ecl_logic.families(path)
        normal = {b for v in fams.values() for _, b in v} - {'none'}
        learned = {lab for _, lab, _ in learn_apply.apply(path)[1]} if not normal else set()
        print(f"{rel.split('/')[-1]:44s} {expected:16s} normal={sorted(normal) or '-'} learned={sorted(learned) or '-'}")


if __name__ == '__main__':
    main()
