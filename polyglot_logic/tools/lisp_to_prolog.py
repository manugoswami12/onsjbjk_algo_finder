"""AP13 v4 (doc 10): Common Lisp -> Prolog normal form (the same PNF as to_prolog.py).

Expression language -> statements by A-normal form: compile(form) returns (statements,
value-expression); `if`/`cond`/`let` used as values get temporaries.
"""
from __future__ import annotations

import itertools
import re

ARITH = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'fdiv', 'mod': 'mod', 'rem': 'mod', 'expt': 'pow',
         'logxor': 'xor', 'ash': 'shl'}
CMP = {'<': 'lt', '>': 'gt', '<=': 'le', '>=': 'ge', '=': 'eq', '/=': 'ne', 'eql': 'eq', 'equal': 'eq',
       'eq': 'eq', 'string=': 'eq', 'char=': 'eq'}


class Sym(str):
    pass


def read_all(src: str):
    """A small, total s-expression reader (comments, strings, quote, #', characters)."""
    toks = re.findall(r'''#\\.|"(?:\\.|[^"\\])*"|;[^\n]*|#\|[\s\S]*?\|#|[()']|#'|[^\s()';"]+''', src)
    toks = [t for t in toks if not t.startswith(';') and not t.startswith('#|')]
    pos = 0

    def form():
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == '(':
            out = []
            while pos < len(toks) and toks[pos] != ')':
                out.append(form())
            pos += 1
            return out
        if t in ("'", "#'"):
            return [Sym('quote' if t == "'" else 'function'), form()]
        if t.startswith('"'):
            return ('str', t[1:-1])
        if t.startswith('#\\'):
            return ('chr', t[2:])
        if re.fullmatch(r'[-+]?\d+', t):
            return int(t)
        if re.fullmatch(r'[-+]?\d*\.\d+(e[-+]?\d+)?', t, re.I):
            return float(t)
        return Sym(t.lower())
    forms = []
    while pos < len(toks):
        if toks[pos] == ')':
            pos += 1
            continue
        forms.append(form())
    return forms


class LispPNF:
    def __init__(self):
        self.funs, self.tmp = [], itertools.count()

    def fresh(self):
        return f'$t{next(self.tmp)}'

    def run(self, src):
        for f in read_all(src):
            if isinstance(f, list) and f and f[0] in ('defun',) and len(f) >= 3 and isinstance(f[2], list):
                self.defun(f)
        return self.funs

    def defun(self, f):
        name, lam, body = str(f[1]), f[2], f[3:]
        if body and isinstance(body[0], tuple) and body[0][0] == 'str':       # docstring
            body = body[1:]
        params, pre, mode = [], [], 'req'
        for p in lam:
            if p in ('&optional', '&key', '&aux'):
                mode = str(p)[1:]
                continue
            if p in ('&rest', '&body'):
                mode = 'rest'
                continue
            if mode == 'req':
                params.append(str(p))
            elif mode in ('optional', 'key') and isinstance(p, list) and len(p) > 1:
                s, v = self.compile(p[1])                   # default value: used (battery passes required only)
                pre += s + [('assign', ('var', str(p[0])), v)]
            elif mode == 'aux':
                if isinstance(p, list):
                    s, v = self.compile(p[1])
                    pre += s + [('assign', ('var', str(p[0])), v)]
        stmts, val = self.compile_body(body)
        self.funs.append((name, params, ('seq', pre + stmts + [('return', val)])))

    # ----- forms -> (statements, value) ------------------------------------------------
    def compile_body(self, forms):
        stmts, val = [], ('none',)
        for f in forms:
            s, val = self.compile(f)
            stmts += s
        return stmts, val

    def compile(self, f):
        if isinstance(f, bool):
            return [], ('bool', 'true' if f else 'false')
        if isinstance(f, int):
            return [], ('int', f)
        if isinstance(f, float):
            return [], ('num', f)
        if isinstance(f, tuple):
            if f[0] == 'str':
                return [], ('str', f[1])
            return [], ('int', ord(f[1][0]) if f[1] else 0)
        if isinstance(f, Sym):
            if f in ('nil',):
                return [], ('bool', 'false')
            if f == 't':
                return [], ('bool', 'true')
            return [], ('var', str(f))
        if not f:
            return [], ('bool', 'false')
        head, args = f[0], f[1:]
        if not isinstance(head, Sym):
            return [('unsupported', 'computed_head')], ('none',)
        h = str(head)
        m = getattr(self, 'f_' + re.sub(r'\W', '_', h), None)
        if m is not None:
            return m(args)
        if h in ARITH:
            return self.fold(ARITH[h], args)
        if h in CMP:
            return self.chain(CMP[h], args)
        if h in ('1+', '1-'):
            s, v = self.compile(args[0])
            return s, ('op', 'add' if h == '1+' else 'sub', [v, ('int', 1)])
        s, vs = self.many(args)
        return s, ('call', BUILTIN.get(h, h), vs)

    def many(self, args):
        stmts, vals = [], []
        for a in args:
            s, v = self.compile(a)
            stmts += s
            vals.append(v)
        return stmts, vals

    def fold(self, o, args):
        s, vs = self.many(args)
        if o == 'sub' and len(vs) == 1:
            return s, ('op', 'neg', [vs[0]])
        v = vs[0] if vs else ('int', 0 if o == 'add' else 1)
        for x in vs[1:]:
            v = ('op', o, [v, x])
        return s, v

    def chain(self, o, args):
        s, vs = self.many(args)
        parts = [('op', o, [a, b]) for a, b in zip(vs, vs[1:])]
        v = parts[0] if parts else ('bool', 'true')
        for p in parts[1:]:
            v = ('op', 'and', [v, p])
        return s, v

    def place(self, p):
        """setf targets: variables and element accessors."""
        if isinstance(p, Sym):
            return [], ('var', str(p))
        if isinstance(p, list) and p and p[0] in ('aref', 'elt', 'svref', 'char'):
            s1, q = self.compile(p[1])
            s2, i = self.compile(p[2])
            return s1 + s2, ('elem', q, i)
        if isinstance(p, list) and p and p[0] == 'nth':
            s1, i = self.compile(p[1])
            s2, q = self.compile(p[2])
            return s1 + s2, ('elem', q, i)
        return [('unsupported', 'setf_place')], ('var', '$bad')

    # ----- special forms ------------------------------------------------------------------
    def f_quote(self, a):
        x = a[0]
        if isinstance(x, list):
            return self.f_list(x)
        return self.compile(x)

    def f_function(self, a):
        return [], ('fn', str(a[0]))

    def f_progn(self, a):
        return self.compile_body(a)

    def f_let(self, a):
        stmts = []
        for b in a[0]:
            if isinstance(b, list):
                s, v = self.compile(b[1] if len(b) > 1 else Sym('nil'))
                stmts += s + [('assign', ('var', str(b[0])), v)]
            else:
                stmts.append(('assign', ('var', str(b)), ('bool', 'false')))
        s, v = self.compile_body(a[1:])
        return stmts + s, v
    f_let_ = f_let

    def f_setf(self, a):
        stmts, val = [], ('none',)
        for p, e in zip(a[0::2], a[1::2]):
            s1, t = self.place(p)
            s2, v = self.compile(e)
            stmts += s1 + s2 + [('assign', t, v)]
            val = t
        return stmts, val
    f_setq = f_setf

    def f_incf(self, a, o='add'):
        s1, t = self.place(a[0])
        s2, d = self.compile(a[1]) if len(a) > 1 else ([], ('int', 1))
        return s1 + s2 + [('assign', t, ('op', o, [t, d]))], t

    def f_decf(self, a):
        return self.f_incf(a, 'sub')

    def f_rotatef(self, a):
        s1, t1 = self.place(a[0])
        s2, t2 = self.place(a[1])
        return s1 + s2 + [('par_assign', [t1, t2], [t2, t1])], ('none',)

    def f_push(self, a):
        s1, x = self.compile(a[0])
        s2, t = self.place(a[1])
        return s1 + s2 + [('assign', t, ('concat', [('list', [x]), t]))], t

    def f_if(self, a):
        sc, c = self.compile(a[0])
        st, vt = self.compile(a[1]) if len(a) > 1 else ([], ('bool', 'false'))
        se, ve = self.compile(a[2]) if len(a) > 2 else ([], ('bool', 'false'))
        if not st and not se:
            return sc, ('cond', c, vt, ve)
        t = self.fresh()
        return sc + [('if', c, ('seq', st + [('assign', ('var', t), vt)]),
                      ('seq', se + [('assign', ('var', t), ve)]))], ('var', t)

    def f_when(self, a, neg=False):
        sc, c = self.compile(a[0])
        if neg:
            c = ('op', 'not', [c])
        sb, vb = self.compile_body(a[1:])
        t = self.fresh()
        return sc + [('assign', ('var', t), ('bool', 'false')),
                     ('if', c, ('seq', sb + [('assign', ('var', t), vb)]), ('skip',))], ('var', t)

    def f_unless(self, a):
        return self.f_when(a, neg=True)

    def f_cond(self, a):
        t = self.fresh()
        tree = ('skip',)
        for clause in reversed(a):
            sc, c = self.compile(clause[0])
            sb, vb = self.compile_body(clause[1:]) if len(clause) > 1 else ([], c)
            tree = ('seq', sc + [('if', c, ('seq', sb + [('assign', ('var', t), vb)]), tree)])
        return [('assign', ('var', t), ('bool', 'false')), tree], ('var', t)

    def f_and(self, a):
        return self.chain_logic('and', a)

    def f_or(self, a):
        return self.chain_logic('or', a)

    def chain_logic(self, o, a):
        s, vs = self.many(a)
        if not vs:
            return s, ('bool', 'true' if o == 'and' else 'false')
        v = vs[0]
        for x in vs[1:]:
            v = ('op', o, [v, x])
        return s, v

    def f_not(self, a):
        s, v = self.compile(a[0])
        return s, ('op', 'not', [v])
    f_null = f_not
    f_endp = f_not

    def f_zerop(self, a):
        s, v = self.compile(a[0])
        return s, ('op', 'eq', [v, ('int', 0)])

    def f_evenp(self, a, r=0):
        s, v = self.compile(a[0])
        return s, ('op', 'eq', [('op', 'mod', [v, ('int', 2)]), ('int', r)])

    def f_oddp(self, a):
        return self.f_evenp(a, 1)

    def f_floor(self, a):
        s, vs = self.many(a)
        return s, (('op', 'div', vs) if len(vs) == 2 else ('call', 'floor', vs))
    f_truncate = f_floor

    def f_return_from(self, a):
        s, v = self.compile(a[1]) if len(a) > 1 else ([], ('none',))
        return s + [('return', v)], ('none',)

    def f_return(self, a):
        s, v = self.compile(a[0]) if a else ([], ('none',))
        return s + [('return', v)], ('none',)

    def f_list(self, a):
        s, vs = self.many(a)
        return s, ('list', vs)

    def f_vector(self, a):
        return self.f_list(a)

    def f_cons(self, a):
        s, vs = self.many(a)
        return s, ('concat', [('list', [vs[0]]), vs[1]])

    def f_append(self, a):
        s, vs = self.many(a)
        return s, ('concat', vs)

    def f_aref(self, a):
        s, vs = self.many(a[:2])
        return s, ('elem', vs[0], vs[1])
    f_elt = f_aref
    f_svref = f_aref
    f_char = f_aref

    def f_nth(self, a):
        s, vs = self.many(a[:2])
        return s, ('elem', vs[1], vs[0])

    def f_car(self, a):
        s, v = self.compile(a[0])
        return s, ('elem', v, ('int', 0))
    f_first = f_car

    def f_second(self, a):
        s, v = self.compile(a[0])
        return s, ('elem', v, ('int', 1))

    def f_cdr(self, a):
        s, v = self.compile(a[0])
        return s, ('slice', v, ('int', 1), ('none',), ('none',))
    f_rest = f_cdr

    def f_length(self, a):
        s, v = self.compile(a[0])
        return s, ('call', 'len', [v])

    def f_make_array(self, a):
        s, n = self.compile(a[0])
        init = ('int', 0)
        for k, v in zip(a[1::2], a[2::2]):
            if k == ':initial-element':
                s2, init = self.compile(v)
                s += s2
        return s, ('op', 'mul', [('list', [init]), n])

    def f_copy_seq(self, a):
        s, v = self.compile(a[0])
        return s, ('call', 'list', [v])
    f_copy_list = f_copy_seq

    def f_funcall(self, a):
        s, vs = self.many(a)
        if vs and vs[0][0] == 'fn':
            return s, self.apply_named(vs[0][1], vs[1:])
        return s, ('callv', vs[0], vs[1:])                 # a function held in a variable

    def apply_named(self, n, vs):
        if n in CMP:
            return ('op', CMP[n], vs[:2])
        if n in ARITH:
            return ('op', ARITH[n], vs[:2])
        return ('call', BUILTIN.get(n, n), vs)

    def lam_or_fn(self, f):
        """#'name or (lambda (x) body) -> (param names, body statements, value) or a function name."""
        if isinstance(f, list) and f and f[0] == 'function':
            f = f[1]
        if isinstance(f, Sym):
            return str(f)
        if isinstance(f, list) and f and f[0] == 'lambda':
            ps = [str(p) for p in f[1]]
            s, v = self.compile_body(f[2:])
            return (ps, s, v)
        return None

    def apply1(self, fn, x):
        if isinstance(fn, str):
            if fn in ARITH or fn in CMP:
                return [], None
            return [], ('call', BUILTIN.get(fn, fn), [x])
        ps, s, v = fn
        if s:
            return None, None
        return [], subst(v, ps[0], x)

    def f_mapcar(self, a):
        fn = self.lam_or_fn(a[0])
        s, q = self.compile(a[1])
        x = self.fresh()
        _, body = self.apply1(fn, ('var', x)) if fn else (None, None)
        if body is None:
            return s + [('unsupported', 'mapcar_function')], ('none',)
        return s, ('comp', x, q, ('bool', 'true'), body)

    def f_remove_if_not(self, a, keep=True):
        fn = self.lam_or_fn(a[0])
        s, q = self.compile(a[1])
        x = self.fresh()
        _, c = self.apply1(fn, ('var', x)) if fn else (None, None)
        if c is None:
            return s + [('unsupported', 'filter_function')], ('none',)
        return s, ('comp', x, q, c if keep else ('op', 'not', [c]), ('var', x))

    def f_remove_if(self, a):
        return self.f_remove_if_not(a, keep=False)

    def f_reduce(self, a):
        fn = self.lam_or_fn(a[0])
        s, q = self.compile(a[1])
        if fn in ('+', '*', 'max', 'min'):
            name = {'+': 'sum', '*': 'product', 'max': 'max', 'min': 'min'}[fn]
            return s, ('call', name, [q])
        return s + [('unsupported', 'reduce_function')], ('none',)

    def f_sort(self, a):
        s, q = self.compile(a[0])
        fn = self.lam_or_fn(a[1]) if len(a) > 1 else '<'
        if fn in ('<', '<='):
            return s, ('call', 'sorted', [q])
        if fn in ('>', '>='):
            return s, ('call', 'reverse', [('call', 'sorted', [q])])
        return s + [('unsupported', 'sort_predicate')], ('none',)
    f_stable_sort = f_sort

    def f_dotimes(self, a):
        v, n = str(a[0][0]), a[0][1]
        s, nv = self.compile(n)
        sb, _ = self.compile_body(a[1:])
        return s + [('for_range', v, ('int', 0), nv, ('int', 1), ('seq', sb))], ('bool', 'false')

    def f_dolist(self, a):
        v, q = str(a[0][0]), a[0][1]
        s, qv = self.compile(q)
        sb, _ = self.compile_body(a[1:])
        return s + [('for_each', v, qv, ('seq', sb))], ('bool', 'false')

    def f_do(self, a):
        specs, end, body = a[0], a[1], a[2:]
        init, step = [], []
        for sp in specs:
            sp = sp if isinstance(sp, list) else [sp]
            s, v = self.compile(sp[1]) if len(sp) > 1 else ([], ('bool', 'false'))
            init += s + [('assign', ('var', str(sp[0])), v)]
            if len(sp) > 2:
                s2, v2 = self.compile(sp[2])
                step.append((s2, ('var', str(sp[0])), v2))
        sc, c = self.compile(end[0])
        sr, r = self.compile_body(end[1:])
        sb, _ = self.compile_body(body)
        upd = [x for s2, _, _ in step for x in s2] + \
            ([('par_assign', [t for _, t, _ in step], [v for _, _, v in step])] if step else [])
        if sc:
            return init + [('unsupported', 'do_end_test_with_statements')], ('none',)
        return init + [('while', ('op', 'not', [c]), ('seq', sb + upd))] + sr, r

    def f_loop(self, a):
        """The common clauses of the loop macro."""
        # keywords compare equal as Sym (a str subclass); values stay Sym for compile()
        i, pre, loops, body, post, acc = 0, [], [], [], [], None
        while i < len(a):
            k = a[i]
            if k in ('for', 'as'):
                v = a[i + 1]
                kw = a[i + 2]
                if kw == 'in':
                    s, q = self.compile(a[i + 3])
                    pre += s
                    loops.append(('each', v, q))
                    i += 4
                    continue
                if kw in ('from', 'upfrom', 'below', 'to', 'upto'):
                    if kw in ('from', 'upfrom'):
                        s, lo = self.compile(a[i + 3])
                        pre += s
                        i += 4
                    else:                                  # for x below n: from 0
                        lo = ('int', 0)
                        i += 2
                    hi, incl, step = ('none',), False, ('int', 1)
                    while i < len(a) and a[i] in ('to', 'below', 'upto', 'by'):
                        s2, x = self.compile(a[i + 1])
                        pre += s2
                        if a[i] == 'by':
                            step = x
                        else:
                            hi, incl = x, a[i] in ('to', 'upto')
                        i += 2
                    if incl:
                        hi = ('op', 'add', [hi, ('int', 1)])
                    loops.append(('range', v, lo, hi, step))
                    continue
                if kw == '=':
                    s, e = self.compile(a[i + 3])
                    pre += s + [('assign', ('var', str(v)), e)]
                    i += 4
                    if i < len(a) and a[i] == 'then':
                        s2, e2 = self.compile(a[i + 1])
                        post += s2 + [('assign', ('var', str(v)), e2)]
                        i += 2
                    continue
                return [('unsupported', 'loop_for_' + str(kw))], ('none',)
            if k == 'with':                               # with v = e
                v = a[i + 1]
                if i + 2 < len(a) and a[i + 2] == '=':
                    s, e = self.compile(a[i + 3])
                    pre += s + [('assign', ('var', str(v)), e)]
                    i += 4
                else:
                    pre.append(('assign', ('var', str(v)), ('bool', 'false')))
                    i += 2
                continue
            if k == 'repeat':
                s, n = self.compile(a[i + 1])
                pre += s
                loops.append(('range', '$r', ('int', 0), n, ('int', 1)))
                i += 2
                continue
            if k in ('while', 'until'):
                s, c = self.compile(a[i + 1])
                if k == 'until':
                    c = ('op', 'not', [c])
                body += s + [('if', c, ('skip',), ('break',))]
                i += 2
                continue
            if k == 'do':
                i += 1
                while i < len(a) and isinstance(a[i], list):
                    s, _ = self.compile(a[i])
                    body += s
                    i += 1
                continue
            if k in ('collect', 'collecting', 'sum', 'summing', 'count', 'counting', 'maximize', 'minimize'):
                s, v = self.compile(a[i + 1])
                acc = acc or self.fresh()
                kind = k.rstrip('ing') if k.endswith('ing') else k
                init = {'collect': ('list', []), 'sum': ('int', 0), 'count': ('int', 0),
                        'maximize': ('none',), 'minimize': ('none',)}.get(kind, ('int', 0))
                if not any(p == ('assign', ('var', acc), init) for p in pre):
                    pre.append(('assign', ('var', acc), init))
                upd = {'collect': ('concat', [('var', acc), ('list', [v])]),
                       'sum': ('op', 'add', [('var', acc), v]),
                       'count': ('cond', v, ('op', 'add', [('var', acc), ('int', 1)]), ('var', acc)),
                       'maximize': ('cond', ('op', 'eq', [('var', acc), ('none',)]), v,
                                    ('call', 'max', [('var', acc), v])),
                       'minimize': ('cond', ('op', 'eq', [('var', acc), ('none',)]), v,
                                    ('call', 'min', [('var', acc), v]))}.get(kind)
                body += s + [('assign', ('var', acc), upd)]
                i += 2
                continue
            if k == 'return':
                s, v = self.compile(a[i + 1])
                body += s + [('return', v)]
                i += 2
                continue
            if k in ('finally',):
                s, _ = self.compile(a[i + 1])
                post += s
                i += 2
                continue
            if isinstance(k, list):                       # simple loop: (loop form...)
                s, _ = self.compile(k)
                body += s
                i += 1
                continue
            return [('unsupported', 'loop_' + str(k))], ('none',)
        inner = ('seq', body + post)
        for lp in reversed(loops):
            if lp[0] == 'each':
                inner = ('for_each', str(lp[1]), lp[2], inner)
            else:
                _, v, lo, hi, st = lp
                if hi == ('none',):
                    inner = ('seq', [('assign', ('var', str(v)), lo),
                                     ('while', ('bool', 'true'), ('seq', [inner, ('assign', ('var', str(v)),
                                                                                  ('op', 'add', [('var', str(v)), st]))]))])
                else:
                    inner = ('for_range', str(v), lo, hi, st, inner)
        if not loops:
            inner = ('while', ('bool', 'true'), inner)
        return pre + [inner], (('var', acc) if acc else ('bool', 'false'))


BUILTIN = {'abs': 'abs', 'max': 'max', 'min': 'min', 'sqrt': 'sqrt', 'isqrt': 'isqrt', 'gcd': 'gcd',
           'reverse': 'reverse', 'print': 'print', 'format': 'print', 'princ': 'print', 'write': 'print',
           'terpri': 'print', 'length': 'len', 'evenp': 'evenp', 'oddp': 'oddp'}


def subst(t, name, x):
    if t == ('var', name):
        return x
    if isinstance(t, tuple):
        return tuple(subst(a, name, x) if isinstance(a, (tuple, list)) else a for a in t)
    if isinstance(t, list):
        return [subst(a, name, x) for a in t]
    return t


def lisp_normal_form(src: str):
    return LispPNF().run(src)
