"""Mixed-algorithm answers (doc 04 section 18.6), kept separate from the pipeline: eval_ta.py, learn_apply.py and
the Prolog rules are used as they are, never edited. Two corrections to how behaviour (io) evidence is labelled:

  TheAlgorithms side  A match on a TheAlgorithms function names that file's label when the function is a root of the
                      file, or when no root of the file runs (the functions that run are then its algorithm). A root
                      of a file whose roots behave differently (primelib's is_perfect_number) is also named by the
                      single-algorithm files whose root behaves the same (perfect_number). A helper of a file whose
                      root runs (problem_020's factorial()) is named only by those single-algorithm files, and by
                      nothing when there is none.
  new-file side       When one of the new file's root functions (prolog/call_roots.pl) runs, only the roots decide
                      its main answer; labels found only on its helpers, including a built branch at a helper's tree
                      node, are reported as components: least-common-multiple-2.py is "main: not identified,
                      contains: gcd". When no root runs (a demo root that only prints), every function counts.

Both corrections apply to the io evidence (MixedIo) and to AP13's exact traced logic (MixedLogic: each stored pattern
records its source function). The tiers and their order are the pipeline's (eval_ta.decide), applied to the main
labels.

Two v0.3 fixes, also separate (doc 04 section 18.7): the tree with the branches of prolog/families_v03.pl
(prolog/tree_v03.pl, prolog/learn_apply_v03.pl: partition by recursion through variables, a sequence rewritten whole
in place), so a file reaches its algorithm's node and not a broad one where another label's branch is the only one;
and the Lisp loop's `finally` run after the loop (lisp_loop_v03.py). No TheAlgorithms file changes node under the v0.3
tree, so the learned branches (placed with the v0.2 tree) stay where they are.

usage: PYTHONPATH=.:tools_manual python mixed_answer.py CORPUS --heldout ROSETTA   -> benchmark/mixed_heldout.json
       PYTHONPATH=.:tools_manual python mixed_answer.py CORPUS --corpus           -> benchmark/mixed_corpus.json
"""
from __future__ import annotations

import argparse
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from decide_new_or_known import roots

import compare_learners
import crosslang_frontends
import eval_ta
import learn_facts
import lisp_loop_v03
import ta_corpus
from ta_corpus import ROOT

ROOTS = ROOT / 'benchmark' / 'corpus_roots.json'
TREE_V03 = ROOT / 'prolog' / 'tree_v03.pl'
APPLY_V03 = ROOT / 'prolog' / 'learn_apply_v03.pl'


def base(name: str) -> str:
    return name.split('$')[0]


class MixedIo(eval_ta.TaIo):
    """eval_ta.TaIo with each catalog entry named by the algorithm of its function, not of its file."""

    def __init__(self, corpus: Path, labels: dict[str, str], workers=4):
        super().__init__(corpus, labels, workers)
        file_roots = {rel: set(r) for rel, r in json.loads(ROOTS.read_text(encoding='utf-8')).items()}
        by_file = {}
        for (rel, name), ref in self.cat.items():         # the catalog holds the functions that run (discriminative)
            by_file.setdefault(rel, {})[name] = ref
        self.own = set()                            # (rel, name): a root of a single-algorithm file
        self.running_root = set()                   # files with a root that runs
        for rel, funs in by_file.items():
            rts = [n for n in funs if base(n) in file_roots.get(rel, set())]
            if rts:
                self.running_root.add(rel)
            if rts and all(self.same(funs[a], funs[b]) for a in rts for b in rts):
                self.own.update((rel, n) for n in rts)
        self.name_of = {}                           # (rel, name) -> labels of its algorithm
        for key, ref in self.cat.items():
            rel, name = key
            alike = {self.labels[o[0]] for o, oref in self.by_sig[(tuple(ref['sig']), len(ref['outputs']))]
                     if o in self.own and o[0] != rel and self.same(ref, oref)}
            if key in self.own:
                self.name_of[key] = {self.labels[rel]}
            elif base(name) in file_roots.get(rel, set()):   # a root of a file with several algorithms (primelib)
                self.name_of[key] = {self.labels[rel]} | alike
            elif rel not in self.running_root:      # no root runs: the functions that run are the file's algorithm
                self.name_of[key] = {self.labels[rel]}
            else:                                   # a helper (problem_020's factorial): its own algorithm only
                self.name_of[key] = alike

    def same(self, a: dict, b: dict) -> bool:
        return self.ioc.compare(a, b) in ('io', 'logic')

    def labels_by_kind(self, path, me=None):
        """As TaIo.labels_by_kind, with each match named by name_of instead of by its file's label."""
        if me is None:
            me = self.describe(path)
        out, traced = {}, {}
        for name, d in me.items():
            if not d['discriminative']:
                continue
            for key, ref in self.by_sig[(tuple(d['sig']), len(d['outputs']))]:
                how = self.ioc.compare(d, ref)
                if how in ('logic', 'io'):
                    out.setdefault(name, set()).update(self.name_of[key])
                if how == 'logic':
                    traced.setdefault(name, set()).update(self.name_of[key])
            if d['sig'] == ['int']:
                for key, ref in self.ints:
                    if compare_learners.shifted_sequence(d, ref):
                        out.setdefault(name, set()).update(self.name_of[key])
        return out, traced


class MixedLogic(eval_ta.TaLogic):
    """eval_ta.TaLogic (AP13's exact traced logic) with each match named by the algorithm of the TheAlgorithms
    function it came from (pattern.function_name), as MixedIo names an io match, and split by the new file's roots."""

    def attach(self, io: MixedIo, file_roots: dict[str, list[str]]):
        """Each stored pattern named as MixedIo names its function: by the io naming when the function runs, else by
        the file's label when it is a root or no root of the file runs, else (a helper) by nothing."""
        io_names = {}
        for (rel, name), names in io.name_of.items():
            io_names.setdefault((rel, base(name)), set()).update(names)
        self.name_of_ref = {}
        with self.ks.connect(self.store) as db:
            for label, rel, fn in db.execute('SELECT label, source_path, function_name FROM pattern'):
                key = (rel, base(fn))
                if rel not in self.labels:
                    continue
                if key in io_names:
                    self.name_of_ref[label] = io_names[key]
                elif base(fn) in file_roots.get(rel, []) or rel not in io.running_root:
                    self.name_of_ref[label] = {self.labels[rel]}
                else:
                    self.name_of_ref[label] = set()

    def labels_split(self, path: Path, is_root) -> tuple[set[str], set[str]]:
        """(labels matched on the new file's roots, labels matched only on its helpers)."""
        import re
        try:
            _, facts = self.cli.facts_text(path)
            result = self.cli.scan(path, self.store, include_unreviewed=True, quiet=True)
        except eval_ta.ERRORS + compare_learners.ERRORS:
            return set(), set()
        names = dict(re.findall(r"^func\('([^']*)','([^']*)'", facts, re.MULTILINE))
        main, comp = set(), set()
        for m in result['leaves']:
            if m['result'] != 'MATCH':
                continue
            labs = self.name_of_ref.get(m['label'], set()) - {'none'}
            fns = [names.get(fid, '') for fid in m['functions'].split(',')]
            (main if any(is_root(fn) for fn in fns) else comp).update(labs)
        return main, comp


def function_nodes(path: Path) -> dict[str, set[str]]:
    """{function: its tree nodes} (the v0.3 tree's NODE|Function|Path lines)."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}
    out = {}
    for line in learn_facts.swipl_facts('tree_main', TREE_V03, kind, text):
        if line.startswith('NODE|'):
            _, fn, node = line.split('|', 2)
            out.setdefault(fn, set()).add(node)
    return out


def built_by_node(path: Path, rules: Path, io_labels, trace_labels, logic_labels):
    """learn_apply.apply's evidence on the v0.3 tree, with each built/hand branch's tree node kept: ({node: {branch}},
    found, specific)."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}, [], set()
    with tempfile.TemporaryDirectory(prefix='v02_mix_') as td:
        io = Path(td) / 'io.pl'
        io.write_text(''.join(f"io_equal('{lab}').\n" for lab in sorted(io_labels))
                      + ''.join(f"io_trace_equal('{lab}').\n" for lab in sorted(trace_labels))
                      + ''.join(f"logic_equal('{lab}').\n" for lab in sorted(logic_labels)), encoding='utf-8')
        lines = learn_facts.swipl_facts('learn_apply_main', APPLY_V03, kind, text, str(rules), str(io))
    built = {}
    for line in lines:
        if line.startswith(('NORMAL|', 'HAND|')):
            _, node, b = line.split('|')[:3]
            built.setdefault(node, set()).add(b)
    found = [tuple(line.split('|')[1:]) for line in lines if line.startswith('LEARNED|')]
    specific = {line.split('|')[1] for line in lines if line.startswith('SPECIFIC|')}
    return built, found, specific


def answer(path: Path, io: MixedIo, labels: set[str], gs: dict[str, str], logic) -> dict:
    """{'got': main group or None, 'why', 'components': groups found only on helpers, ...}."""
    if path.suffix == '.lisp' and eval_ta.ecl_logic.NOCODE in eval_ta.ecl_logic.families(path):
        return {'got': None, 'why': 'no_algorithm', 'components': []}
    if path.suffix != '.lisp' and not learn_facts.defines_code(path):
        return {'got': None, 'why': 'no_algorithm', 'components': []}
    try:
        rts = roots(path)
    except Exception:                               # noqa: BLE001
        rts = set()
    try:
        me = io.describe(path)
        by_fn, traced = io.labels_by_kind(path, me)
    except eval_ta.ERRORS:
        me, by_fn, traced = {}, {}, {}
    # the roots decide when one of them runs; when none runs (a demo root that only prints: caesar_cipher.py's
    # brute_force) or no root is known, every function counts, as in the pipeline
    if not any(base(fn) in rts and d['discriminative'] for fn, d in me.items()):
        rts = set()
    is_root = (lambda fn: base(fn) in rts) if rts else (lambda fn: True)
    main_io = {lab for fn, v in by_fn.items() if is_root(fn) for lab in v} & labels
    comp_io = {lab for fn, v in by_fn.items() if not is_root(fn) for lab in v} & labels
    main_trace = {lab for fn, v in traced.items() if is_root(fn) for lab in v} & labels
    main_logic, comp_logic = logic.labels_split(path, is_root) if logic else (set(), set())
    logic_labels = main_logic & labels
    try:
        built, found, specific = built_by_node(path, eval_ta.RULES, main_io, main_trace, logic_labels)
        fnodes = function_nodes(path)
    except eval_ta.ERRORS:
        built, found, specific, fnodes = {}, [], set(), {}
    root_nodes = {n for fn, ns in fnodes.items() if is_root(fn) for n in ns}
    on_root = lambda node: (not rts) or node in root_nodes or not any(node in ns for ns in fnodes.values())
    main_built = {b for node, bs in built.items() if on_root(node) for b in bs}
    comp_built = {b for node, bs in built.items() if not on_root(node) for b in bs}
    out = {'nodes': sorted(root_nodes) if rts else sorted({n for ns in fnodes.values() for n in ns}),
           'held': sorted({lab for _, lab, r in found if r == 'io'}),
           'held_trace': sorted({lab for _, lab, r in found if r in ('trace', 'logic')}),
           'io': sorted(main_io), 'logic': sorted(logic_labels)}
    res = eval_ta.decide(out, main_built, specific, labels, gs)
    comps = {ta_corpus.group(c, gs) for c in (comp_io | comp_logic) & labels | {b for b in comp_built if b in ta_corpus.BUILT or b in labels}}
    res['components'] = sorted(comps - {res.get('got')})
    res['roots'] = sorted(rts)
    return res


def run(units: dict[str, Path], corpus: Path, out: Path, workers: int, extra: dict | None = None):
    labels = ta_corpus.files(corpus)
    gs = ta_corpus.groups(labels.values())
    crosslang_frontends.install(lisp_sbcl=False)
    lisp_loop_v03.install()
    io = MixedIo(corpus, labels, workers)
    with tempfile.TemporaryDirectory(prefix='v02_mix_') as td:
        truth = Path(td) / 'train.json'
        truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
        logic = MixedLogic(corpus, [truth], workers)
    logic.attach(io, json.loads(ROOTS.read_text(encoding='utf-8')))
    done = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, (rel, res) in enumerate(pool.map(
                lambda kv: (kv[0], answer(kv[1], io, set(labels.values()), gs, logic)), sorted(units.items())), 1):
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
    p.add_argument('--files', nargs='*', help='only these units (relative paths), for a manual check')
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    if a.heldout:
        tasks = eval_ta.heldout_units(a.heldout)
        units = {rel: a.heldout / rel for rel in tasks if not a.files or rel in a.files}
        run(units, a.corpus, ROOT / 'benchmark' / ('mixed_heldout_check.json' if a.files else 'mixed_heldout.json'),
            a.workers, tasks)
    if a.self_test:
        rels = ta_corpus.files(a.corpus)
        units = {rel: a.corpus / rel for rel in rels if not a.files or rel in a.files}
        run(units, a.corpus, ROOT / 'benchmark' / ('mixed_corpus_check.json' if a.files else 'mixed_corpus.json'),
            a.workers)


if __name__ == '__main__':
    main()
