"""Adapters that let v0.2 use the ORIGINAL AP13 learners (polyglot_logic, imported read-only)
next to the new learn_v2.py, so all of them can be compared on the same data.

  ap13dir  AP13 learn-dir: every training function traced and stored as an exact Prolog
           logic reference (scratch store, never polyglot_logic/store); scan = leaf MATCH
  iocat    AP13 io_catalog: behaviour catalog of the training functions (Prolog normal form run
           on a fixed battery inside SWI-Prolog; the Python source itself never runs);
           a test function matches a reference with equal logic trace or equal outputs
Each learner returns, per test file, the branch labels of the training files it matched;
eval_heldout.py turns them into observed(F, learned(Label), Line) facts for route_v2.pl.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AP13_TOOLS = Path(__file__).resolve().parents[1] / 'polyglot_logic' / 'tools'
ERRORS = (RuntimeError, ValueError, OSError, RecursionError, KeyError, IndexError, TypeError,
          AttributeError, StopIteration, SyntaxError)


def _ap13():
    if str(AP13_TOOLS) not in sys.path:
        sys.path.insert(0, str(AP13_TOOLS))


def training_labels(truth_files):
    labels = {}
    for tf in truth_files:
        for rel, value in json.loads(Path(tf).read_text(encoding='utf-8'))['files'].items():
            label = value[0] if isinstance(value, list) else value
            labels[rel] = 'none' if label is None else label
    return labels


class Ap13Dir:
    def __init__(self, root: Path, truth_files, workers=4):
        _ap13()
        import cli
        import knowledge_store
        self.cli, self.ks = cli, knowledge_store
        self.labels = training_labels(truth_files)
        self.store = Path(tempfile.mkdtemp(prefix='v02_ap13store_'))

        def trace(rel):
            prefix = 'lg_' + ''.join(ch if ch.isalnum() else '_' for ch in rel.rsplit('.', 1)[0])[:60] + \
                '_' + hashlib.sha256(rel.encode()).hexdigest()[:8]
            try:
                lang, facts = cli.facts_text(root / rel)
                return rel, lang, cli.run_prolog('learn_all_main', facts, [prefix]), None
            except ERRORS as exc:
                return rel, None, None, exc
        counts = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for rel, lang, lines, exc in pool.map(trace, sorted(self.labels)):
                if exc is None:
                    try:
                        cli.store_learned(self.store, lang, rel, lines, counts)
                    except ERRORS:
                        pass
        with knowledge_store.connect(self.store) as db:
            self.ref_file = {r['label']: r['source_path'] for r in db.execute('SELECT label, source_path FROM pattern')}

    def labels_by_function(self, path: Path) -> dict[str, set[str]]:
        """{function name: labels of the training files whose exact traced logic it matches}."""
        import re
        try:
            _, facts = self.cli.facts_text(path)
            result = self.cli.scan(path, self.store, include_unreviewed=True, quiet=True)
        except ERRORS:
            return {}
        names = dict(re.findall(r"^func\('([^']*)','([^']*)'", facts, re.M))
        out: dict[str, set[str]] = {}
        for m in result['leaves']:
            if m['result'] == 'MATCH' and self.ref_file.get(m['label']) in self.labels:
                label = self.labels[self.ref_file[m['label']]]
                for fid in m['functions'].split(','):
                    if label != 'none' and fid in names:
                        out.setdefault(names[fid], set()).add(label)
        return out

    def labels_for(self, path: Path) -> set[str]:
        try:
            result = self.cli.scan(path, self.store, include_unreviewed=True, quiet=True)
        except ERRORS:
            return set()
        return {self.labels[self.ref_file[m['label']]] for m in result['leaves']
                if m['result'] == 'MATCH' and self.ref_file.get(m['label']) in self.labels} - {'none'}


class IoCatalog:
    def __init__(self, root: Path, truth_files, workers=4):
        _ap13()
        import io_catalog
        import io_trace
        self.ioc, self.iot = io_catalog, io_trace
        self.labels = training_labels(truth_files)

        def one(rel):
            try:
                return rel, io_catalog.describe(io_trace.run_functions(root / rel))
            except ERRORS:
                return rel, {}
        self.cat = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for rel, funs in pool.map(one, sorted(self.labels)):
                for name, d in funs.items():
                    if d['discriminative']:
                        self.cat[(rel, name)] = d

    def run_isolated(self, path: Path) -> dict:
        """All functions of a file in one interpreter run; if that run fails (one function can
        crash it), each function is run on its own so the others are not lost."""
        try:
            return self.iot.run_functions(path)
        except ERRORS:
            pass
        try:
            names = [n for n, _, _ in self.iot.normal_form(path)[1]]
        except ERRORS:
            return {}
        out = {}
        for n in names:
            try:
                out.update(self.iot.run_functions(path, functions={n}))
            except ERRORS:
                continue
        return out

    def describe(self, path: Path) -> dict:
        """The file's behaviour description per function ({} when it cannot be run)."""
        try:
            return self.ioc.describe(self.run_isolated(path))
        except ERRORS:
            return {}

    def labels_by_function(self, path: Path, me: dict | None = None) -> dict[str, set[str]]:
        """{function name: labels of the training references with equal behaviour}; me: the file's
        description when the caller already has it."""
        if me is None:
            me = self.describe(path)
        out: dict[str, set[str]] = {}
        for name, d in me.items():
            if not d['discriminative']:
                continue
            for (rel, _), ref in self.cat.items():
                if self.labels[rel] != 'none' and (self.ioc.compare(d, ref) in ('logic', 'io')
                                                   or shifted_sequence(d, ref)):
                    out.setdefault(name, set()).add(self.labels[rel])
        return out

    def labels_for(self, path: Path) -> set[str]:
        try:
            me = self.ioc.describe(self.run_isolated(path))
        except ERRORS:
            return set()
        out = set()
        for d in me.values():
            if not d['discriminative']:
                continue
            for (rel, _), ref in self.cat.items():
                if self.ioc.compare(d, ref) in ('logic', 'io'):
                    out.add(self.labels[rel])
        return out - {'none'}


SHIFT_MIN = 20     # equal positions required for a shifted-index sequence match


def shifted_sequence(a, b):
    """Integer sequences equal up to a one-step index shift (0- vs 1-based numbering, e.g.
    fib(0)=1 vs fib(0)=0): on the consecutive inputs n = 0..40, a(n) == b(n + k) for k = +1 or -1
    on at least SHIFT_MIN positions, none unequal, and not constant."""
    if a['sig'] != ['int'] or b['sig'] != ['int']:
        return False
    xa, xb = a['outputs'][:41], b['outputs'][:41]
    for k in (1, -1):
        pairs = [(xa[i], xb[i + k]) for i in range(41) if 0 <= i + k < 41
                 and xa[i] is not None and xb[i + k] is not None]
        if (len(pairs) >= SHIFT_MIN and all(p == q for p, q in pairs)
                and len({p for p, _ in pairs}) > 2 and not _arithmetic([p for p, _ in pairs])):
            return True
    return False


def _arithmetic(values):
    """An arithmetic progression (n, n+1, 2n, ...) equals its own shift plus a constant, so a shift
    match carries no evidence there."""
    try:
        xs = [int(v) for v in values]
    except ValueError:
        return False
    return len({b - a for a, b in zip(xs, xs[1:])}) <= 1


LEARNERS = {'ap13dir': Ap13Dir, 'iocat': IoCatalog}
