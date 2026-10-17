"""Language front ends that reuse each language's own tooling, plugged into the AP13 behaviour
pipeline (polyglot_logic/tools/io_trace.py) at run time; polyglot_logic itself is not edited.

  .hs    GHC Core (haskell_core_pnf.py)
  .lisp  SBCL macro-expansion of standard macros, then the AP13 Lisp translator (lisp_sbcl_pnf.py)
"""
from __future__ import annotations

from pathlib import Path

_installed = False


def install(lisp_sbcl: bool = True):
    """Front ends into io_trace: Haskell via GHC Core; Lisp via SBCL unless lisp_sbcl is False (then
    AP13's own lisp_to_prolog translator stays)."""
    global _installed
    if _installed:
        return
    import compare_learners
    compare_learners._ap13()
    import io_trace
    original = io_trace.normal_form

    def normal_form(path: Path):
        suffix = Path(path).suffix.lower()
        if suffix == '.hs':
            from haskell_core_pnf import haskell_normal_form
            return 'haskell', with_swapped_search(with_comparator_wrappers(haskell_normal_form(Path(path)), '<='))
        if lisp_sbcl and suffix in ('.lisp', '.cl', '.lsp'):
            from lisp_sbcl_pnf import lisp_normal_form_sbcl
            return 'commonlisp', with_swapped_search(with_comparator_wrappers(lisp_normal_form_sbcl(Path(path)), '<'))
        return original(path)
    io_trace.normal_form = normal_form
    _installed = True


def function_params(body, params):
    """Parameters used as the head of a call through a value (funcall comp a b / comp a b)."""
    found = set()

    def walk(t):
        if isinstance(t, tuple) and t:
            if t[0] == 'callv' and t[1][:1] == ('var',) and t[1][1] in params:
                found.add(t[1][1])
            for x in t[1:]:
                walk(x)
        elif isinstance(t, list):
            for x in t:
                walk(x)
    walk(body)
    return found


def with_comparator_wrappers(funs, op):
    """For a function with comparator parameters add `name$asc` with them fixed to the standard
    ascending comparator (partial application / specialisation), so it can be run on the battery."""
    out = list(funs)
    fparams = {name: function_params(body, set(params)) for name, params, body in funs}
    plist = {name: params for name, params, _ in funs}

    def calls(t):
        if isinstance(t, tuple) and t:
            if t[0] == 'call' and len(t) == 3 and t[1] in plist:
                yield t[1], t[2]
            for x in t[1:]:
                yield from calls(x)
        elif isinstance(t, list):
            for x in t:
                yield from calls(x)
    changed = True                      # a parameter passed on into a callee's comparator slot
    while changed:
        changed = False
        for name, params, body in funs:
            for callee, args in calls(body):
                for k, a in enumerate(args):
                    if (a[:1] == ('var',) and a[1] in params and a[1] not in fparams[name]
                            and k < len(plist[callee]) and plist[callee][k] in fparams[callee]):
                        fparams[name].add(a[1])
                        changed = True
    for name, params, body in funs:
        fps = fparams[name]
        if fps and len(fps) < len(params):
            args = [('fn', op) if p in fps else ('var', p) for p in params]
            rest = [p for p in params if p not in fps]
            probes = [st for st in body[1] if st[:1] == ('expr',) and st[1][2][0][1] in rest] \
                if body[0] == 'seq' else []
            out.append((f'{name}$asc', rest, ('seq', probes + [('return', ('call', name, args))])))
    return out


def with_swapped_search(funs):
    """Value-first search signatures `f(x, seq)` get a `f$swap(seq, x)` wrapper, so they meet the
    (sequence, target) inputs that sequence-first references are run on."""
    out = list(funs)
    for name, params, body in funs:
        if len(params) != 2 or body[0] != 'seq':
            continue
        probed = {st[1][2][0][1] for st in body[1] if st[:1] == ('expr',) and st[1][:2] == ('call', 'len')}
        if params[1] in probed and params[0] not in probed:
            x, q = params
            out.append((f'{name}$swap', [q, x], ('seq', [('expr', ('call', 'len', [('var', q)])),
                                                         ('return', ('call', name, [('var', x), ('var', q)]))])))
    return out
