#!/usr/bin/env python3
"""AP13 v3.1: one explained outcome for every file (doc 09; judging rules in
benchmark/rosetta_outcome_note.md, written before the first run).

  IDENTIFIED | CONTAINS   unchanged exact matcher (cli.scan)
  FAMILY                  family layer answer (family_scan.answers)
  LIBRARY                 library call with a known family (library_families.py)
  NO_ALGORITHM_BODY       no loop, no recursion, no library family, nothing unmodelled
  UNKNOWN                 anything else, with the reason

  python tools/outcome.py <file> [--store S]
  python tools/outcome.py --rosetta <clone> --store S [--split dev|test|all]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import knowledge_store as store_mod  # noqa: E402
from cli import facts_text, scan  # noqa: E402
from env_run import ROOT, ToolError  # noqa: E402
from family_scan import answers  # noqa: E402
from library_families import LIBRARY_FAMILIES, STRONG  # noqa: E402
from report import identifications  # noqa: E402

TOPLEVEL_TRACED = {'python', 'r'}
# definitions in the SOURCE (checked on the parse tree, independently of the lowerers)
DEFINITION_NODES = {'function_definition', 'function_item', 'method_declaration', 'function_declaration',
                    'constructor_declaration', 'function', 'bind', 'signature', 'defun', 'lambda'}
# higher-order combinators are loops in another form: never "straight-line code"
COMBINATORS = {'map', 'filter', 'reduce', 'foldl', "foldl'", 'foldr', 'foldl1', 'foldr1', 'iterate', 'until',
               'zipWith', 'zipWith3', 'scanl', 'scanr', 'scanl1', 'unfoldr', 'mapAccumL', 'mapAccumR',
               'concatMap', 'mapcar', 'mapc', 'maplist', 'foldl', 'Reduce', 'sapply', 'lapply', 'vapply',
               'Map', 'Filter', 'forM_', 'mapM_', 'replicateM', 'iter', 'fold', 'for_each', 'stream'}
OUTPUT_ONLY = {'print_statement', 'macro_invocation', 'expression_statement'}          # languages whose lowerer traces top-level scripts
_FUNC = re.compile(r"^func\('([^']*)','((?:[^'\\]|\\.)*)',", re.M)
_RETCALL = re.compile(r"'call'\('((?:[^'\\]|\\.)*)'")
_CALL = re.compile(r"^call_at\('[^']*','((?:[^'\\]|\\.)*)',", re.M)


def source_definitions(path: Path) -> int:
    """Number of definition nodes in the parse tree (Prolog: clauses with a body)."""
    from parse_source import parse
    lang, data, root = parse(path)
    if root is None:
        return data.count(b':-')
    n, stack = 0, [root]
    while stack:
        x = stack.pop()
        n += x.type in DEFINITION_NODES
        if x.type == 'list' and x.children[1:2] and x.children[1].text in (b'defun', b'defmacro'):
            n += 1
        stack.extend(x.children)
    return n


def classify(path: Path, store: Path | None, meta: dict) -> dict:
    """The outcome of one source file."""
    try:
        _, facts = facts_text(path)
    except ToolError as exc:
        return {'outcome': 'UNKNOWN', 'reason': f'lowering error: {str(exc)[:120]}'}
    if store is not None and meta:
        r = scan(path, store, True, quiet=True)
        ids = identifications(r, meta)
        if ids:
            lab = ids[0][1][0]
            return {'outcome': 'IDENTIFIED', 'label': lab, 'group': ids[0][1],
                    'source': meta[lab]['source_path'] + '::' + meta[lab]['function_name']}
        contained = [x['label'] for x in r['leaves'] if x['result'] == 'CONTAINS']
    else:
        contained = []
    fam = answers(path)
    deep = sorted({tuple(p) for ps in fam.values() for p in ps if len(p) >= 2})
    shape = sorted({tuple(p) for ps in fam.values() for p in ps if len(p) == 1})
    if deep and len({p[0] for p in deep}) > 1:  # contradicting families: keep all, claim none
        return {'outcome': 'AMBIGUOUS', 'family': deep, 'functions': sorted(fam)}
    if deep:
        return {'outcome': 'FAMILY', 'family': deep, 'functions': sorted(fam)}
    if shape:                   # input -> output shape only: explained, never an algorithm answer
        return {'outcome': 'SHAPE', 'family': shape, 'functions': sorted(fam)}
    if contained:
        lab = contained[0]
        return {'outcome': 'CONTAINS', 'label': lab,
                'source': meta[lab]['source_path'] + '::' + meta[lab]['function_name']}
    defined = {n.split('.')[-1].split('/')[0] for _, n in _FUNC.findall(facts)}
    called = [c for c in _CALL.findall(facts) if c not in defined and c != '$self']
    # only names that ARE the algorithm (doc 09 R9): weak names (sum, max, reverse, index) were
    # wrong more often than right on dev even when returned
    lib_calls = sorted({c for c in called if c in LIBRARY_FAMILIES and c in STRONG})
    lib = sorted({tuple(LIBRARY_FAMILIES[c]) for c in lib_calls})
    if lib:
        return {'outcome': 'LIBRARY', 'family': lib, 'calls': lib_calls}
    has_loop = '\nloop(' in facts
    has_self = "'$self'" in facts
    unsupported = [u for u in re.findall(r"^unsupported\('[^']*','((?:[^'\\]|\\.)*)'", facts, re.M)
                   if u not in OUTPUT_ONLY]                 # printing hides no logic
    real_funcs = [n for _, n in _FUNC.findall(facts) if n not in ('<toplevel>', '<unreadable clause>')]
    if not real_funcs and source_definitions(path):
        return {'outcome': 'UNKNOWN', 'reason': 'definitions present but not lowered (unmodelled form)'}
    hof = sorted({c for c in called if c in COMBINATORS})
    if not has_loop and not has_self and hof:
        return {'outcome': 'UNKNOWN', 'reason': 'higher-order combinator not modelled: ' + ', '.join(hof[:3])}
    if not has_loop and not has_self and not unsupported:
        lang = re.search(r"^lang\('([^']*)'\)", facts, re.M)
        real = [n for _, n in _FUNC.findall(facts) if n not in ('<toplevel>', '<unreadable clause>')]
        if '\nstmt(' not in facts and not real and lang and lang.group(1) not in TOPLEVEL_TRACED:
            reason = 'no function definition (top-level forms of this language are not traced)'
        elif '\nstmt(' not in facts:
            reason = 'no executable statement (import or declaration only)'
        elif called:
            reason = 'only calls ' + ', '.join(sorted(set(called))[:6])
        else:
            reason = 'straight-line code, no loop or recursion'
        return {'outcome': 'NO_ALGORITHM_BODY', 'reason': reason}
    if unsupported:
        return {'outcome': 'UNKNOWN', 'reason': 'unmodelled construct: ' + ', '.join(sorted(set(unsupported))[:3])}
    return {'outcome': 'UNKNOWN', 'reason': 'traced loop/recursion matched no family branch'}


def agrees(paths, accepted):
    return bool(paths) and all(any(a[:len(p)] == list(p) for a in accepted) for p in paths)


def evaluate(rosetta: Path, store: Path, split: str, workers: int):
    from family_eval import split_of
    from rosetta_eval import files
    exact_truth = json.loads((ROOT / 'benchmark' / 'rosetta_truth.json').read_text(encoding='utf-8'))
    fam_truth = json.loads((ROOT / 'benchmark' / 'rosetta_family_truth.json').read_text(encoding='utf-8'))['tasks']
    meta = store_mod.metadata(store)
    negatives = {t for t, good in exact_truth['tasks'].items() if not good}
    jobs = [(t, l, f) for t in fam_truth for l, f in files(rosetta, t)
            if split == 'all' or split_of(t, l, f) == split]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda j: classify(j[2], store, meta), jobs))
    st = defaultdict(lambda: defaultdict(int))
    for (task, lang, f), r in zip(jobs, results):
        o = r['outcome']
        if o == 'IDENTIFIED':          # graded on the whole top structural group, as rosetta_eval.py
            good = set(exact_truth['tasks'][task])
            ok = any(meta[x]['source_path'] in good or meta[x].get('also_source') in good for x in r['group'])
        elif o in ('FAMILY', 'LIBRARY'):
            ok = agrees(r['family'], fam_truth[task])
        else:
            ok = None
        if o == 'SHAPE':                 # its own accuracy, outside precision and recall
            for k in ('ALL', 'lang:' + lang, 'neg' if task in negatives else 'pos'):
                st[k]['SHAPE_ok'] += agrees(r['family'], fam_truth[task])
        for k in ('ALL', 'lang:' + lang, 'neg' if task in negatives else 'pos'):
            st[k]['files'] += 1
            st[k][o] += 1
            if ok is not None:
                st[k]['answered'] += 1
                st[k]['correct'] += ok
                st[k][o + '_ok'] += ok
        detail = r.get('source') or ' ; '.join('>'.join(p) for p in r.get('family', [])) or r.get('reason', '')
        print(f"{task}|{lang}|{f.name}|{o}|{'' if ok is None else ('ok' if ok else 'WRONG')}|{detail}")
    print('\n=== AP13 v3.1 OUTCOMES (one per file) ===')
    for k in ['ALL', 'pos', 'neg'] + sorted(x for x in st if x.startswith('lang:')):
        s = st[k]
        cov = s['files'] - s['UNKNOWN']
        print(f"{k:16s} files={s['files']:4d} IDENTIFIED={s['IDENTIFIED']:3d}({s['IDENTIFIED_ok']}) "
              f"FAMILY={s['FAMILY']:3d}({s['FAMILY_ok']}) LIBRARY={s['LIBRARY']:3d}({s['LIBRARY_ok']}) "
              f"SHAPE={s['SHAPE']:3d}({s['SHAPE_ok']}) AMBIGUOUS={s['AMBIGUOUS']:3d} CONTAINS={s['CONTAINS']:3d} NO_BODY={s['NO_ALGORITHM_BODY']:3d} UNKNOWN={s['UNKNOWN']:3d} "
              f"coverage={cov / max(s['files'], 1):.1%}")
    a, p = st['ALL'], st['pos']
    print(f"\nCOVERAGE (explained outcome / files) = {a['files'] - a['UNKNOWN']}/{a['files']}"
          f" = {(a['files'] - a['UNKNOWN']) / max(a['files'], 1):.1%}")
    print(f"PRECISION (correct / algorithm answers) = {a['correct']}/{a['answered']}"
          f" = {a['correct'] / max(a['answered'], 1):.1%}")
    print(f"RECALL (correct / positive files) = {p['correct']}/{p['files']} = {p['correct'] / max(p['files'], 1):.1%}")
    print(f"WRONG ON NEGATIVES = {st['neg']['answered'] - st['neg']['correct']} of {st['neg']['files']} files")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', nargs='?', type=Path)
    ap.add_argument('--store', type=Path)
    ap.add_argument('--rosetta', type=Path)
    ap.add_argument('--split', choices=('all', 'dev', 'test'), default='all')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    if a.rosetta:
        evaluate(a.rosetta, a.store, a.split, a.workers)
    else:
        meta = store_mod.metadata(a.store) if a.store else {}
        print(json.dumps(classify(a.source, a.store, meta), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
