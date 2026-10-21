"""The behaviour runner of the pipeline (doc 04 section 19.8): AP13's io_trace.run_functions with three additions,
each a rule of the language; the source still never runs, only its Prolog normal form does.
  lift              a nested function is a new function (lambda lifting): a function A.g defined inside A that reads
                    variables of A takes them as trailing parameters; inside A (and A's other nested functions) a
                    call g(a) is A.g(a, free...), and g used as a value is the closure lambda(params, A.g(params,
                    free...)). The short name resolves lexically (A's own g before any other g of the file).
  a sequence        a parameter passed to list(), zip(), enumerate(), sorted(), reversed(), set() or tuple() is a
                    sequence (io_trace's kinds: indexed, measured or iterated only)
  interp_v04.pl     the interpreter (prolog/run_main_v04.pl: interp_v03.pl's closures and library relations, plus
                    zip/min/max of any arity, accumulate, reduce, a boolean operand of + - * as 0 or 1), each clause
                    applying only where AP13's interp.pl would throw
install(): io_trace.run_functions and io_trace._uses replaced (called by crosslang_frontends.install).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners

compare_learners._ap13()
import io_trace
from fact_io import term
from to_prolog import render

RUN_MAIN = Path(__file__).resolve().parent / 'prolog' / 'run_main_v04.pl'
SEQ_CALLS = {'list', 'zip', 'enumerate', 'sorted', 'reversed', 'set', 'tuple'}
_installed = False



def walk(t, fn):
    fn(t)
    if isinstance(t, tuple):
        for x in t[1:]:
            walk(x, fn)
    elif isinstance(t, list):
        for x in t:
            walk(x, fn)


def reads_and_writes(body):
    reads, writes = set(), set()

    def target(t):
        if isinstance(t, tuple) and t[:1] == ('var',):
            writes.add(t[1])
        elif isinstance(t, tuple) and t[:1] == ('tuple',):
            for x in t[1]:
                target(x)

    def visit(t):
        if isinstance(t, tuple) and t[:1] == ('var',) and isinstance(t[1], str):
            reads.add(t[1])
        if isinstance(t, tuple) and t[:1] == ('assign',):
            target(t[1])
        if isinstance(t, tuple) and t[:1] == ('par_assign',):
            for x in t[1]:
                target(x)
        if isinstance(t, tuple) and t[:1] in (('for_each',), ('for_range',)) and len(t) > 1:
            target(t[1])
    walk(body, visit)
    return reads, writes


def lift(funs):
    funs = [list(f) for f in funs]
    names = {f[0] for f in funs}
    scope = {}                                          # function -> its parameters and assigned names
    for name, params, body in funs:
        r, w = reads_and_writes(body)
        scope[name] = (set(params) | w, r)
    free = {}
    for name, params, body in funs:                    # innermost first does not matter: one level of names
        parts = name.split('.')
        enclosing = ['.'.join(parts[:k]) for k in range(len(parts) - 1, 0, -1) if '.'.join(parts[:k]) in names]
        if not enclosing:
            continue
        own, reads = scope[name]
        outer = set().union(*(scope[e][0] for e in enclosing))
        fv = sorted((reads - own) & outer - {n.split('.')[-1] for n in names})
        if fv:
            free[name] = fv
    nested = {}                                         # (enclosing, short name) -> full name
    for n in names:
        if '.' in n:
            nested[(n.rsplit('.', 1)[0], n.rsplit('.', 1)[1])] = n

    def resolve(scope_name, short):
        s = scope_name
        while True:
            if (s, short) in nested:
                return nested[(s, short)]
            if '.' not in s:
                return None
            s = s.rsplit('.', 1)[0]

    def rewrite(t, where, fparams):
        if isinstance(t, tuple) and t[:1] == ('call',) and isinstance(t[1], str):
            full = resolve(where, t[1]) if t[1] not in fparams else None
            args = [rewrite(a, where, fparams) for a in t[2]]
            if full is not None:
                return ('call', full, args + [('var', v) for v in free.get(full, [])])
            return ('call', t[1], args)
        if isinstance(t, tuple) and t[:1] == ('var',) and isinstance(t[1], str) and t[1] not in fparams:
            full = resolve(where, t[1])
            if full is not None:
                ps = next(p for n, p, _ in funs if n == full)
                own = [p for p in ps if p not in free.get(full, [])]
                return ('lambda', own, ('call', full, [('var', p) for p in own] + [('var', v) for v in free.get(full, [])]))
            return t
        if isinstance(t, tuple):
            return (t[0],) + tuple(rewrite(x, where, fparams) for x in t[1:])
        if isinstance(t, list):
            return [rewrite(x, where, fparams) for x in t]
        return t

    out = []
    for name, params, body in funs:
        params = list(params) + free.get(name, [])
        out.append((name, params, rewrite(body, name, set(params))))
    return out


def uses(body, p, _original=None):
    """io_trace._uses, and a parameter passed to a sequence call, sliced or iterated by a comprehension is a sequence."""
    k = _original(body, p)
    if k != 'int':
        return k
    found = []
    walk(body, lambda t: found.append(1) if isinstance(t, tuple) and t[:1] == ('call',) and t[1] in SEQ_CALLS
         and len(t) > 2 and any(a == ('var', p) for a in t[2]) else None)
    walk(body, lambda t: found.append(1) if isinstance(t, tuple) and t[:1] == ('slice',) and len(t) > 1
         and t[1] == ('var', p) else None)                     # a sliced parameter is a sequence (19.17)
    walk(body, lambda t: found.append(1) if isinstance(t, tuple) and t[:1] == ('comp',) and len(t) > 2
         and t[2] == ('var', p) else None)                     # so is one a comprehension iterates over
    return 'list' if found else k


def constants(funs):
    """[(name, value)] of the module-level `name = value` statements (pnf_v03.constants) that no function writes:
    a constant is evaluated where it is read (prolog/interp_v03.pl global_value), so a name a function assigns, stores
    into or appends to (a memo table, a counter) stays unbound rather than losing its writes (doc 04 section 19.17)."""
    out = []
    for name, _, body in funs:
        if name == '<toplevel>' and body and body[0] == 'seq':
            for st in body[1]:
                if isinstance(st, tuple) and len(st) == 3 and st[0] == 'assign' and isinstance(st[1], tuple) \
                        and st[1][0] == 'var':
                    out.append((st[1][1], st[2]))
    written = set()

    def visit(t):
        if isinstance(t, tuple) and t[:1] in (('assign',), ('aug_assign',)) and len(t) > 1:
            x = t[1]
            while isinstance(x, tuple) and x[:1] in (('elem',), ('slice',), ('attr',)):
                x = x[1]
            if isinstance(x, tuple) and x[:1] == ('var',):
                written.add(x[1])
        if isinstance(t, tuple) and t[:1] == ('call',) and len(t) > 2 and t[2] and isinstance(t[2][0], tuple) \
                and t[2][0][:1] == ('var',) and t[1] in ('append', 'extend', 'insert', 'pop', 'remove', 'update',
                                                         'add', 'clear', 'setdefault', 'sort', 'reverse', 'discard'):
            written.add(t[2][0][1])
    for name, _, body in funs:
        if name != '<toplevel>':
            walk(body, visit)
    names = [n for n, _ in out]
    return [(n, v) for n, v in out if n not in written and names.count(n) == 1]


def run_functions(path: Path, functions=None, timeout=120):
    """io_trace.run_functions with the nested functions lifted and the v0.4 interpreter (same result format)."""
    lang, funs = io_trace.normal_form(path)
    if lang == 'prolog':
        return io_trace.run_native_prolog(path, timeout)
    if not funs:
        return {}
    if lang == 'python':
        funs = lift(funs)
    pnf = [f"pnf_lang({term(lang)})."] + [f"pnf_fun({term(n)},{term(list(ps))},{render(b)})." for n, ps, b in funs]
    pnf += [f"pnf_const({term(n)},{render(v)})." for n, v in constants(funs)]
    info, jobs = {}, []
    for name, params, body in funs:
        if functions and name not in functions:
            continue
        ks = io_trace.kinds(params, body)
        sig = io_trace.logical(ks)
        inputs = io_trace.battery(sig)
        info[name] = {'kinds': ks, 'sig': sig, 'inputs': inputs, 'runs': [], 'unsupported': io_trace.has_unsupported(body)}
        for x in inputs:
            jobs.append((len(jobs), name, io_trace.concrete(ks, x)))
    if not jobs:
        return info
    with tempfile.TemporaryDirectory(prefix='v04_pnf_') as td:
        pf, jf = Path(td) / 'pnf.pl', Path(td) / 'jobs.pl'
        pf.write_text('\n'.join(pnf) + '\n', encoding='utf-8')
        jf.write_text(''.join(f"job({i},{term(n)},{io_trace.prolog_value(a)}).\n" for i, n, a in jobs), encoding='utf-8')
        lines = io_trace.swipl('run_main', [RUN_MAIN], [str(pf), str(jf)], timeout=timeout)
    by_id = {}
    for line in lines:
        m = io_trace._RES.match(line)
        if m:
            by_id[int(m.group(1))] = (m.group(2), m.group(3))
    for i, name, _ in jobs:
        status, rest = by_id.get(i, ('err', 'no result'))
        if status == 'ok' and rest.lstrip().startswith(('closure(', 'fun(', 'op_fun(')):
            status, rest = 'err', 'returns a function'
        if status == 'ok':
            result, finals, h, nt, nw = io_trace.split_ok(rest)
            if result == 'false' and int(nw) > 0:
                result = 'none'
            info[name]['runs'].append((True, io_trace.effective(result, finals, info[name]['kinds']),
                                       h if int(nt) > 0 else None))
        else:
            info[name]['runs'].append((False, rest, None))
    return info


def install():
    global _installed
    if _installed:
        return
    _installed = True
    original = io_trace._uses
    io_trace._uses = lambda body, p: uses(body, p, original)
    io_trace.run_functions = run_functions
