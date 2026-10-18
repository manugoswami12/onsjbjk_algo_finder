"""Separate test tool (doc 04 section 18.2): is a file a new version of a known class, a new algorithm (or an
implementation we cannot check), or undecided? Decided only on the file's root functions (prolog/call_roots.pl: own
functions no other own function calls, so a helper's class is never the file's), each run on every battery input.
  new_version    every root ran on every input and all satisfy one and the same class relation (Haskell where/let
                 definitions, main and test code are not roots)
  new_algorithm  every root ran on every input, its output varies, and no class relation holds
  undecided      anything else (a root that does not run fully, roots of no or different classes, a timeout)

usage: PYTHONPATH=. python tools_manual/decide_new_or_known.py ROOT FILES.json OUT.json [--v03]
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import compare_learners
import crosslang_frontends
import learn_facts
import ta_classes
from ta_corpus import ROOT

crosslang_frontends.install(lisp_sbcl=False)
compare_learners._ap13()
import io_trace

ROOTS = ROOT / 'prolog' / 'call_roots.pl'
V03 = '--v03' in sys.argv          # run the normal form with the separate v0.3 runner (pnf_v03.py)
if V03:
    import pnf_v03


def roots(p: Path) -> set[str]:
    """The file's root functions. In Haskell a definition on an indented line is local (a where or let binding, by the
    layout rule): a helper of the function it is in, never a root (the lowering loses some of those calls, inside a
    case scrutinee)."""
    kind, text = learn_facts.tree_facts(p)
    if not text.strip():
        return set()
    src = p.read_text(encoding='utf-8', errors='replace').splitlines() if p.suffix == '.hs' else []
    out = set()
    for line in learn_facts.swipl_facts('roots_main', ROOTS, kind, text):
        if line.startswith('ROOT|'):
            _, name, at = line.split('|')
            k = int(at) - 1 if at.isdigit() else -1
            if src and 0 <= k < len(src) and src[k][:1].isspace():
                continue
            out.add(name)
    return out


def base(name: str) -> str:
    return name.split('$')[0]                       # io_trace names a where-function gs$1


def decide(p: Path) -> dict:
    try:
        rts = roots(p)
        info = (pnf_v03.run_functions(p) if V03 else io_trace.run_functions(p))
    except Exception as e:                          # noqa: BLE001  (any failure is undecided)
        return {'decision': 'undecided', 'why': 'no run: ' + type(e).__name__}
    if not rts:
        return {'decision': 'undecided', 'why': 'no root function'}
    full = {n for n, d in info.items() if d.get('runs') and not d.get('unsupported') and all(r[0] for r in d['runs'])}
    if not rts <= full:                             # every root runs on every input (a root left out could be the
        return {'decision': 'undecided', 'why': 'a root does not run on every input', 'roots': sorted(rts),
                'not_full': sorted(rts - full)}     # algorithm itself: simpson_integration beside f(x) = x*x)
    ran = rts
    try:
        rs = ta_classes.runs(p, v03=V03)
        cs = ta_classes.classes(p, rs)
    except Exception as e:                          # noqa: BLE001
        return {'decision': 'undecided', 'why': 'check error ' + type(e).__name__}
    if cs is None:
        return {'decision': 'undecided', 'why': 'check timeout'}
    by_root = {r: set().union(*[v for n, v in cs.items() if base(n) == r]) for r in ran}
    if all(len(v) == 1 for v in by_root.values()) and len(set().union(*by_root.values())) == 1:
        return {'decision': 'new_version', 'class': min(set().union(*by_root.values())), 'roots': sorted(ran),
                'nodes': learn_facts.nodes(p)}          # nodes: the second witness (eval_decision.py)
    if any(by_root.values()):
        return {'decision': 'undecided', 'why': 'roots of no or different classes', 'classes': {r: sorted(v) for r, v in by_root.items()}}
    varied = all(len({o for _, o in rs[n][1]}) > 1 for n in rs if base(n) in rts)
    if varied and all(any(base(n) == r for n in rs) for r in rts):
        return {'decision': 'new_algorithm', 'roots': sorted(rts)}
    return {'decision': 'undecided', 'why': 'output does not depend on the input', 'roots': sorted(rts)}


if __name__ == '__main__':
    root, files = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
    with ThreadPoolExecutor(4) as pool:
        out = dict(zip(files, pool.map(lambda f: decide(root / f), files)))
    Path(sys.argv[3]).write_text(json.dumps(out, indent=1))
