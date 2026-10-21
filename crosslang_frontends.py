"""Language front ends that reuse each language's own tooling, plugged into the AP13 behaviour
pipeline (polyglot_logic/tools/io_trace.py) at run time; polyglot_logic itself is not edited.

  .hs    GHC Core (haskell_core_pnf.py)
  .lisp  SBCL macro-expansion of standard macros, then the AP13 Lisp translator (lisp_sbcl_pnf.py)
  any    a formatted result string is its value (without_formatting)
  .lisp, .c  lowering_v03.py: the Lisp loop's `finally` runs after the loop; C's x op= y keeps its operator
  .c     the program after its own macros (learn_facts.c_expanded), as the tree reads it (19.14)
  .hs    a root returning a function partly applied, eta-expanded (eta_expanded, 19.14)
"""
from __future__ import annotations

import tempfile
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
            funs = eta_expanded(haskell_normal_form(Path(path)))
            return 'haskell', with_swapped_search(with_comparator_wrappers(funs, '<='))
        if lisp_sbcl and suffix in ('.lisp', '.cl', '.lsp'):
            from lisp_sbcl_pnf import lisp_normal_form_sbcl
            return 'commonlisp', with_swapped_search(with_comparator_wrappers(lisp_normal_form_sbcl(Path(path)), '<'))
        if suffix == '.c':                    # the program as its macros make it, as the tree reads it
            from learn_facts import c_expanded
            text = c_expanded(Path(path))
            if text is not None:
                with tempfile.TemporaryDirectory(prefix='v04_cpp_') as td:
                    f = Path(td) / Path(path).name
                    f.write_text(text, encoding='utf-8')
                    lang, funs = original(f)
                    return lang, without_formatting(funs)
        lang, funs = original(path)
        return lang, without_formatting(funs)
    io_trace.normal_form = normal_form
    import lowering_v03
    lowering_v03.install()
    import returns_function                   # a function returning a function, lowered as a new one (19.8)
    returns_function.install()
    import generators                         # a generator gives the list it yields (19.14)
    generators.install()
    import behaviour_v04                      # nested functions lifted, the v0.4 interpreter (19.8)
    behaviour_v04.install()
    _installed = True


def eta_expanded(funs):
    """A definition that returns a function partly applied (digsum base = f 0) is the function of all the
    arguments: the missing parameters are added to it and to the call (digsum base n = f 0 n), as a Python
    function returning a function is (returns_function, 19.8). Only when every own return is such a call."""
    arity = {n: len(ps) for n, ps, _ in funs}

    def returns(t, out):
        if isinstance(t, tuple) and t:
            if t[0] == 'return':
                out.append(t)
                return out
            for x in t[1:]:
                returns(x, out)
        elif isinstance(t, list):
            for x in t:
                returns(x, out)
        return out

    def missing(body):
        rs = returns(body, [])
        ks = {arity[r[1][1]] - len(r[1][2]) if len(r) == 2 and isinstance(r[1], tuple) and r[1][:1] == ('call',)
              and r[1][1] in arity and len(r[1][2]) < arity[r[1][1]] else 0 for r in rs}
        return ks.pop() if rs and len(ks) == 1 else 0

    def extend(t, extra):
        if isinstance(t, tuple) and t:
            if t[0] == 'return' and len(t) == 2 and t[1][:1] == ('call',):
                return ('return', ('call', t[1][1], list(t[1][2]) + extra))
            return tuple(extend(x, extra) if i else x for i, x in enumerate(t))
        if isinstance(t, list):
            return [extend(x, extra) for x in t]
        return t

    changed = True
    while changed:
        changed, out = False, []
        for n, ps, body in funs:
            k = missing(body)
            if k:
                extra = [f'eta${i}' for i in range(k)]
                body, ps, changed = extend(body, [('var', v) for v in extra]), list(ps) + extra, True
                arity[n] = len(ps)
            out.append((n, ps, body))
        funs = out
    return funs


def without_formatting(funs):
    """The program only has to name its algorithm: presenting a result is not the result. A string
    formatted with a value ('Survivor: %d' % r, Python's printf operator in the normal form) is that
    value, as a print is an effect and not the logic."""
    def strip(t):
        if isinstance(t, tuple) and t:
            if t[0] == 'op' and t[1] == 'mod' and len(t) == 3 and len(t[2]) == 2 and t[2][0][:1] == ('str',):
                return strip(t[2][1])
            return tuple(strip(x) for x in t)
        if isinstance(t, list):
            return [strip(x) for x in t]
        return t
    if isinstance(funs, list):
        return [(name, params, strip(body)) for name, params, body in funs]
    return funs


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
