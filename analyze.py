"""Name the algorithm of one or more source files with the whole pipeline (README: the one command).

usage: python analyze.py FILE [FILE ...]        (Python .py, C .c, Common Lisp .lisp, Haskell .hs)

For each file: the main pipeline's answer (eval_ta.answer: file rules, hand-built branches, traced logic, learned
branches, canonical logic, behaviour), and when it names nothing, the separate class check (decide_new_or_known,
v0.3 runner, as README section 4b). The source is never run; only its Prolog normal form is.

The first run learns TheAlgorithms/Python (data/TheAlgorithms-Python) and keeps what it learned in .cache/: the
behaviour catalogue and the two exact-logic stores. Later runs reuse it; it is rebuilt by itself when the code, the
Prolog rules or the data change (the cache key is a hash of them)."""
from __future__ import annotations

import hashlib
import json
import pickle
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tools_manual')]
CORPUS = ROOT / 'data' / 'TheAlgorithms-Python'
SUFFIXES = {'.py': 'Python', '.c': 'C', '.lisp': 'Common Lisp', '.lsp': 'Common Lisp', '.cl': 'Common Lisp',
            '.hs': 'Haskell'}
WHY = {'file_rule': 'it is the same code as a TheAlgorithms file',
       'built': 'a hand-built rule of the algorithm tree',
       'trace': 'its traced logic and behaviour match a learned algorithm at its tree node',
       'learned': 'a learned rule at its node of the algorithm tree (logic and behaviour)',
       'canonical': 'its traced logic matches a learned algorithm (canonical form)',
       'io': 'its input/output behaviour equals a learned algorithm',
       'ambiguous': 'several algorithms fit equally',
       'none': 'no rule and no behaviour match names it',
       'no_algorithm': 'it defines no algorithm code (a transcript, imports or a main block only)'}


def cache_key() -> str:
    h = hashlib.sha256()
    for pattern in ('*.py', 'prolog/*.pl', 'tools_manual/*.py', 'polyglot_logic/tools/*.py', 'polyglot_logic/prolog/*.pl'):
        for p in sorted(ROOT.glob(pattern)):
            h.update(p.relative_to(ROOT).as_posix().encode())
            h.update(p.read_bytes())
    manifest = ROOT / 'data' / 'MANIFEST.sha256'
    h.update(manifest.read_bytes() if manifest.exists() else b'')
    return h.hexdigest()[:16]


def learned(workers: int):
    """(TaIo, TaLogic, labels, groups): built once, then loaded from .cache/analyze/KEY."""
    import compare_learners
    import eval_ta
    import ta_corpus
    labels = ta_corpus.files(CORPUS)
    gs = ta_corpus.groups(labels.values())
    cache = ROOT / '.cache' / 'analyze' / cache_key()
    if not (cache / 'done').exists():
        print('First run: learning TheAlgorithms/Python (this takes a while, once) ...', flush=True)
        io = eval_ta.TaIo(CORPUS, labels, workers)
        with tempfile.TemporaryDirectory() as td:
            truth = Path(td) / 'train.json'
            truth.write_text(json.dumps({'files': labels}), encoding='utf-8')
            logic = eval_ta.TaLogic(CORPUS, [truth], workers)
        if cache.parent.exists():
            shutil.rmtree(cache.parent)                   # older keys: the code or data changed
        cache.mkdir(parents=True)
        (cache / 'io_cat.pkl').write_bytes(pickle.dumps(io.cat))
        shutil.copytree(logic.store, cache / 'logic_store')
        shutil.copytree(logic.canon.store, cache / 'canon_store')
        (cache / 'done').write_text('ok\n')
        print('Learned; kept in', cache.relative_to(ROOT), flush=True)
    compare_learners._ap13()
    import cli
    import io_catalog
    import io_trace
    import knowledge_store
    import logic_canon
    import report
    io = eval_ta.TaIo.__new__(eval_ta.TaIo)               # the catalogue as eval_ta.TaIo builds it, from the cache
    io.ioc, io.iot, io.labels, io.corpus = io_catalog, io_trace, labels, CORPUS
    io.cat = pickle.loads((cache / 'io_cat.pkl').read_bytes())
    io.by_sig = defaultdict(list)
    for key, ref in io.cat.items():
        io.by_sig[(tuple(ref['sig']), len(ref['outputs']))].append((key, ref))
    io.ints = [(k, r) for k, r in io.cat.items() if r['sig'] == ['int']]
    logic = eval_ta.TaLogic.__new__(eval_ta.TaLogic)      # the two exact-logic stores, from the cache
    logic.cli, logic.ks, logic.labels, logic.store = cli, knowledge_store, labels, cache / 'logic_store'
    canon = eval_ta.CanonicalLogic.__new__(eval_ta.CanonicalLogic)
    canon.cli, canon.ks, canon.report, canon.lc, canon.store = cli, knowledge_store, report, logic_canon, cache / 'canon_store'
    for view in (logic, canon):
        with knowledge_store.connect(view.store) as db:
            view.ref_file = {r['label']: r['source_path'] for r in db.execute('SELECT label, source_path FROM pattern')}
    logic.canon = canon
    return io, logic, labels, gs


def class_check(path: Path) -> str:
    """The separate fallback: a class relation on every test input of the file's root functions."""
    sys.argv.append('--v03')                              # decide_new_or_known reads it at import, as README 4b
    import decide_new_or_known
    d = decide_new_or_known.decide(path)
    if d['decision'] == 'new_version':
        return f"class: {d['class']} (what it computes, checked on its outputs; which variant is not claimed)"
    if d['decision'] == 'new_algorithm':
        return 'it runs, but matches nothing known: a new algorithm or an incorrect implementation'
    return f"UNKNOWN ({d.get('why', 'not decided')})"


def main(argv):
    files = [Path(a).resolve() for a in argv if not a.startswith('--')]
    if not files:
        print(__doc__.split('\n\n')[1])
        return 2
    bad = [f for f in files if not f.is_file() or f.suffix.lower() not in SUFFIXES]
    for f in bad:
        print(f'{f}: not a file of a supported language (.py .c .lisp .hs)')
    files = [f for f in files if f not in bad]
    if not files:
        return 2
    import crosslang_frontends
    crosslang_frontends.install(lisp_sbcl=False)
    import eval_ta
    io, logic, labels, gs = learned(workers=4)
    for f in files:
        res = eval_ta.answer(f, io, set(labels.values()), gs, logic)
        print(f'\n{f.name} ({SUFFIXES[f.suffix.lower()]})')
        if res.get('got'):
            print(f"  algorithm: {res['got']}")
            print(f"  because:   {WHY.get(res['why'], res['why'])}")
        else:
            reason = WHY.get(res['why'], res['why'])
            if res['why'] == 'ambiguous' and res.get('clash'):
                reason += ': ' + ', '.join(res['clash'][:6])
            print(f'  algorithm: not named ({reason})')
            print(f'  fallback:  {class_check(f)}')
        if res.get('nodes'):
            print(f"  tree node: {', '.join(res['nodes'][:3])}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
