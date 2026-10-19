"""The pipeline's answer with only the v0.3 fixes (doc 04 section 18.7), kept separate from the pipeline: eval_ta.answer
exactly (its catalogs, naming, tiers and decision), with
  - the tree with the branches of prolog/families_v03.pl (learn_apply_v03.pl in place of learn_apply.pl), and
  - the behaviour-lowering fixes of lowering_v03.py (the Lisp loop's `finally`; C's x op= y).
No TheAlgorithms file changes tree node under the v0.3 tree, and TheAlgorithms is Python (neither lowering fix
applies), so its answers can only stay as they are; the corpus run checks that.

usage: PYTHONPATH=.:tools_manual python answer_v03.py CORPUS --heldout ROSETTA   -> benchmark/v03_heldout.json
       PYTHONPATH=.:tools_manual python answer_v03.py CORPUS --corpus           -> benchmark/v03_corpus.json
"""
from __future__ import annotations

import argparse
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import crosslang_frontends
import eval_ta
import learn_facts
import lowering_v03
import ta_corpus
from mixed_answer import APPLY_V03
from ta_corpus import ROOT


def apply_v03(path: Path, rules: Path, io_labels=(), trace_labels=(), logic_labels=(), hand=None, specific=None):
    """learn_apply.apply on the v0.3 tree: the same outputs, from prolog/learn_apply_v03.pl."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return [], [], set(), set()
    with tempfile.TemporaryDirectory(prefix='v03_io_') as td:
        io = Path(td) / 'io.pl'
        io.write_text(''.join(f"io_equal('{lab}').\n" for lab in sorted(io_labels))
                      + ''.join(f"io_trace_equal('{lab}').\n" for lab in sorted(trace_labels))
                      + ''.join(f"logic_equal('{lab}').\n" for lab in sorted(logic_labels)), encoding='utf-8')
        lines = learn_facts.swipl_facts('learn_apply_main', APPLY_V03, kind, text, str(rules), str(io))
    nodes = [line.split('|', 1)[1] for line in lines if line.startswith('NODE|')]
    branch_at = {line.split('|')[2] for line in lines if line.startswith('BRANCH_AT|')}
    normal = {line.split('|')[2] for line in lines if line.startswith('NORMAL|')}
    if hand is not None:
        hand.update(line.split('|')[2] for line in lines if line.startswith('HAND|'))
    if specific is not None:
        specific.update(line.split('|')[1] for line in lines if line.startswith('SPECIFIC|'))
    return nodes, [tuple(line.split('|')[1:]) for line in lines if line.startswith('LEARNED|')], branch_at, normal


def run(units: dict[str, Path], corpus: Path, out: Path, workers: int, extra: dict | None = None):
    labels = ta_corpus.files(corpus)
    gs = ta_corpus.groups(labels.values())
    crosslang_frontends.install(lisp_sbcl=False)
    lowering_v03.install()
    eval_ta.learn_apply.apply = apply_v03           # in this process only: eval_ta.answer calls it
    io = eval_ta.TaIo(corpus, labels, workers)
    with tempfile.TemporaryDirectory(prefix='v03_ta_') as td:
        truth = Path(td) / 'train.json'
        truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
        logic = eval_ta.TaLogic(corpus, [truth], workers)
    done = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (rel, res) in enumerate(pool.map(
                lambda kv: (kv[0], eval_ta.answer(kv[1], io, set(labels.values()), gs, logic)), sorted(units.items())), 1):
            done[rel] = {**res, **({'task': extra[rel]} if extra and rel in extra else {})}
            if n % 100 == 0:
                print(f'{n}/{len(units)}', flush=True)
    out.write_text(json.dumps(done, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{len(units)} answered -> {out}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('--heldout', type=Path, metavar='ROSETTA')
    p.add_argument('--corpus', dest='self_test', action='store_true')
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    if a.heldout:
        tasks = eval_ta.heldout_units(a.heldout)
        run({rel: a.heldout / rel for rel in tasks}, a.corpus, ROOT / 'benchmark' / 'v03_heldout.json', a.workers, tasks)
    if a.self_test:
        rels = ta_corpus.files(a.corpus)
        run({rel: a.corpus / rel for rel in rels}, a.corpus, ROOT / 'benchmark' / 'v03_corpus.json', a.workers)


if __name__ == '__main__':
    main()
