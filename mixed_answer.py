"""Mixed-algorithm answers (doc 04 section 18.6), kept separate from the pipeline: eval_ta.py, learn_apply.py and
the Prolog rules are used as they are, never edited. Two corrections to how behaviour (io) evidence is labelled:

  TheAlgorithms side  A match on a TheAlgorithms function names that file's label only when the function is a root of
                      a single-algorithm file (every root of the file behaves the same: maths/factorial.py has
                      factorial and factorial_recursive). A helper (problem_020's factorial()) or a function of a
                      library file (primelib's is_perfect_number) is named by the single-algorithm files whose root
                      behaves the same (factorial, perfect_number), and by nothing when there is none.
  new-file side       Only the new file's root functions (prolog/call_roots.pl) decide its main answer. Labels found
                      only on its helpers, including a built branch at a helper's tree node, are reported as
                      components: least-common-multiple-2.py is "main: not identified, contains: gcd".

Both corrections apply to the io evidence (MixedIo) and to AP13's exact traced logic (MixedLogic: each stored pattern
records its source function). The tiers and their order are the pipeline's (eval_ta.decide), applied to the main
labels.

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
import learn_apply
import learn_facts
import ta_corpus
from ta_corpus import ROOT

ROOTS = ROOT / 'benchmark' / 'corpus_roots.json'


def base(name: str) -> str:
    return name.split('$')[0]


class MixedIo(eval_ta.TaIo):
    """eval_ta.TaIo with each catalog entry named by the algorithm of its function, not of its file."""

    def __init__(self, corpus: Path, labels: dict[str, str], workers=4):
        super().__init__(corpus, labels, workers)
        file_roots = json.loads(ROOTS.read_text(encoding='utf-8'))
        by_file = {}
        for (rel, name), ref in self.cat.items():
            by_file.setdefault(rel, {})[name] = ref
        self.own = set()                            # (rel, name): a root of a single-algorithm file
        for rel, funs in by_file.items():
            rts = [n for n in funs if base(n) in set(file_roots.get(rel, []))]
            if rts and all(self.same(funs[a], funs[b]) for a in rts for b in rts):
                self.own.update((rel, n) for n in rts)
        self.name_of = {}                           # (rel, name) -> labels of its algorithm
        for key, ref in self.cat.items():
            if key in self.own:
                self.name_of[key] = {self.labels[key[0]]}
            else:
                self.name_of[key] = {self.labels[o[0]] for o, oref in self.by_sig[(tuple(ref['sig']), len(ref['outputs']))]
                                     if o in self.own and self.same(ref, oref)}

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
        io_names = {}
        for (rel, name), names in io.name_of.items():
            io_names.setdefault((rel, base(name)), set()).update(names)
        own = {(rel, base(name)) for rel, name in io.own}
        self.name_of_ref = {}
        with self.ks.connect(self.store) as db:
            for label, rel, fn in db.execute('SELECT label, source_path, function_name FROM pattern'):
                key = (rel, base(fn))
                if rel not in self.labels:
                    continue
                if key in own or (key not in io_names and file_roots.get(rel) == [base(fn)]):
                    self.name_of_ref[label] = {self.labels[rel]}          # a root of a single-algorithm file
                else:
                    self.name_of_ref[label] = io_names.get(key, set())    # a helper or a library function

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
    """{function: its tree nodes} (the tree's NODE|Function|Path lines)."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}
    out = {}
    for line in learn_facts.swipl_facts('tree_main', learn_facts.TREE_MAIN, kind, text):
        if line.startswith('NODE|'):
            _, fn, node = line.split('|', 2)
            out.setdefault(fn, set()).add(node)
    return out


def built_by_node(path: Path, rules: Path, io_labels, trace_labels, logic_labels):
    """learn_apply.apply's evidence, with each built/hand branch's tree node kept: ({node: {branch}}, found, specific)."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}, [], set()
    with tempfile.TemporaryDirectory(prefix='v02_mix_') as td:
        io = Path(td) / 'io.pl'
        io.write_text(''.join(f"io_equal('{lab}').\n" for lab in sorted(io_labels))
                      + ''.join(f"io_trace_equal('{lab}').\n" for lab in sorted(trace_labels))
                      + ''.join(f"logic_equal('{lab}').\n" for lab in sorted(logic_labels)), encoding='utf-8')
        lines = learn_facts.swipl_facts('learn_apply_main', learn_apply.PROLOG / 'learn_apply.pl', kind, text,
                                        str(rules), str(io))
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
        by_fn, traced = io.labels_by_kind(path, io.describe(path))
    except eval_ta.ERRORS:
        by_fn, traced = {}, {}
    is_root = (lambda fn: base(fn) in rts) if rts else (lambda fn: True)   # no roots known: every function counts
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
