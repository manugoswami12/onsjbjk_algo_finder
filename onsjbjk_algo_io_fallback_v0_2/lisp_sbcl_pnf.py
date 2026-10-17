"""Common Lisp -> Prolog normal form through SBCL's own macro expander.

SBCL reads the file (`*read-eval*` off: `#.` is refused) and expands every STANDARD Common Lisp
macro the AP13 Lisp translator does not already understand (shiftf, psetf, case, prog1, ...),
so the program reaches the translator in a small core of forms. User macros are NOT expanded
(that would run code from the file); such forms stay unsupported. Generated symbols are renamed
to unique interned names. The AP13 translator (polyglot_logic/tools/lisp_to_prolog.py, unchanged)
is then extended here by subclassing: lambda folds (reduce), &rest parameters, labels/flet
(lambda-lifted), block / the / declare / locally, psetq, member, multiple-value-bind of floor.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import compare_learners

KEEP = '''defun let let* setf setq incf decf rotatef push if when unless cond and or not progn quote
function lambda dotimes dolist do loop return return-from block the declare locally labels flet
multiple-value-bind psetq psetf'''.split()

SBCL_SCRIPT = r'''
(defpackage :v02x (:use :cl))
;%PKGS%
(in-package :v02x)
(defparameter *keep* '(%KEEP%))
(defparameter *names* (make-hash-table :test 'eq))
(defparameter *n* 0)
(defun keep-p (h) (and (symbolp h) (member (symbol-name h) *keep* :test #'string-equal)))
(defun std-macro-p (h)
  (and (symbolp h) (eq (symbol-package h) (find-package :cl)) (macro-function h)))
(defun walk (f)
  (cond ((atom f) f)
        ((eq (car f) 'quote) f)
        ((keep-p (car f)) (cons (car f) (mapcar #'walk-any (cdr f))))
        ((std-macro-p (car f)) (walk (macroexpand-1 f)))
        (t (cons (car f) (mapcar #'walk-any (cdr f))))))
(defun walk-any (f) (if (consp f) (walk f) f))
(defun rename (f)
  (cond ((and (symbolp f) f (null (symbol-package f)))
         (or (gethash f *names*)
             (setf (gethash f *names*) (intern (format nil "G~D-~A" (incf *n*) (symbol-name f))))))
        ((consp f) (cons (rename (car f)) (rename (cdr f))))
        (t f)))
(let ((*read-eval* nil) (*package* (find-package :v02x)))
  (with-open-file (in (second sb-ext:*posix-argv*))
    (handler-case
        (loop for form = (read in nil :eof) until (eq form :eof)
              when (and (consp form) (member (car form) '(defun) :test #'eq))
                do (let ((*print-case* :downcase) (*print-pretty* nil) (*print-circle* nil))
                     (prin1 (rename (walk form))) (terpri)))
      (error () nil))))
'''


PKG_PREFIX = re.compile(r'(?<![\w:#|])([A-Za-z][\w.+-]*):(?=[^\s:()])')


def readable_source(src: str) -> tuple[str, list[str]]:
    """Symbols of packages that are not loaded (`rtl:with`) would stop the reader: each such
    package is pre-defined and its prefix made internal (`rtl::with`), so every form is read."""
    pkgs = sorted({m.group(1).lower() for m in PKG_PREFIX.finditer(src)} - {'cl', 'common-lisp', 'keyword'})
    return PKG_PREFIX.sub(lambda m: m.group(1) + '::', src), pkgs


def sbcl_expand(path: Path, timeout=60) -> str:
    src, pkgs = readable_source(path.read_text(encoding='utf-8', errors='replace'))
    defs = ''.join(f'(unless (find-package "{p.upper()}") (make-package "{p.upper()}" :use (list "CL")))\n'
                   for p in pkgs)
    script = SBCL_SCRIPT.replace('%KEEP%', ' '.join(f'"{k}"' for k in KEEP)).replace(';%PKGS%', defs)
    with tempfile.TemporaryDirectory(prefix='v02_sbcl_') as td:
        sf, srcf = Path(td) / 'expand.lisp', Path(td) / 'source.lisp'
        sf.write_text(script, encoding='utf-8')
        srcf.write_text(src, encoding='utf-8')
        proc = subprocess.run(['sbcl', '--script', str(sf), str(srcf)], capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    return proc.stdout


def _base():
    compare_learners._ap13()
    import lisp_to_prolog
    return lisp_to_prolog


def _make_class():
    L = _base()
    Sym = L.Sym

    class LispPNF2(L.LispPNF):
        def defun(self, f):
            lam = [p for p in f[2] if p not in ('&rest', '&body')] if isinstance(f[2], list) else f[2]
            self.scope = [str(p) for p in lam if isinstance(p, Sym) and not str(p).startswith('&')]
            return super().defun([f[0], f[1], lam] + f[3:])

        def f_block(self, a):
            return self.compile_body(a[1:])

        def f_the(self, a):
            return self.compile(a[1])

        def f_declare(self, a):
            return [], ('none',)

        def f_locally(self, a):
            return self.compile_body([x for x in a if not (isinstance(x, list) and x and x[0] == 'declare')])

        def f_psetq(self, a):
            ts, vs, stmts = [], [], []
            for p, e in zip(a[0::2], a[1::2]):
                s1, t = self.place(p)
                s2, v = self.compile(e)
                stmts += s1 + s2
                ts.append(t)
                vs.append(v)
            return stmts + [('par_assign', ts, vs)], ('none',)
        f_psetf = f_psetq

        # (return x) leaves the innermost NIL block: inside do/dotimes/dolist that is the loop,
        # not the function (the AP13 base translator returned from the function).
        loop_depth = 0

        def _in_loop(self, method, a):
            self.loop_depth += 1
            try:
                return method(self, a)
            finally:
                self.loop_depth -= 1

        def f_do(self, a):
            return self._in_loop(L.LispPNF.f_do, a)

        def f_dotimes(self, a):
            return self._in_loop(L.LispPNF.f_dotimes, a)

        def f_dolist(self, a):
            return self._in_loop(L.LispPNF.f_dolist, a)

        def f_return(self, a):
            if self.loop_depth > 0:
                s, _ = self.compile(a[0]) if a else ([], ('none',))
                return s + ['break'], ('none',)
            return super().f_return(a)

        def f_minusp(self, a):
            s, (x,) = self.many(a[:1])
            return s, ('op', 'lt', [x, ('int', 0)])

        def f_plusp(self, a):
            s, (x,) = self.many(a[:1])
            return s, ('op', 'gt', [x, ('int', 0)])

        def f_rtl__with(self, a):
            # RUTILS `with` (used by the book): sequential bindings like let*
            return self.f_let(a)

        def f_subseq(self, a):
            s, vs = self.many(a[:3])
            return s, ('slice', vs[0], vs[1], vs[2] if len(vs) > 2 else ('none',), ('none',))

        def f_first(self, a):
            s, (q,) = self.many(a[:1])
            return s, ('elem', q, ('int', 0))

        def f_rest(self, a):
            s, (q,) = self.many(a[:1])
            return s, ('slice', q, ('int', 1), ('none',), ('none',))

        def f_last(self, a):
            s, (q,) = self.many(a[:1])
            return s, ('slice', q, ('int', -1), ('none',), ('none',))   # (last l) is the last CONS

        def f_vector(self, a):
            return self.f_list(a)

        def f_values(self, a):
            return self.compile(a[0]) if a else ([], ('none',))

        def f_char_code(self, a):
            return self.compile(a[0])
        f_code_char = f_char_code

        def f_map(self, a):
            # (map 'list fn seq): like mapcar
            return self.f_mapcar(a[1:3])

        def f_loop(self, a):
            """ANSI LOOP subset with the standard's order: clauses initialise in sequence (each
            numeric/list clause tests for termination right after), the body runs, then the clauses
            step in sequence, each followed by its test."""
            KW = {'for', 'as', 'with', 'repeat', 'while', 'until', 'do', 'doing', 'collect', 'collecting',
                  'append', 'appending', 'sum', 'summing', 'count', 'counting', 'maximize', 'maximizing',
                  'minimize', 'minimizing', 'finally', 'return', 'when', 'if', 'unless', 'always', 'never',
                  'thereis', 'into', 'and', 'initially'}
            toks = list(a)
            if not toks or not isinstance(toks[0], Sym) or str(toks[0]) not in KW:
                return super().f_loop(a)            # simple (loop forms...) = infinite loop with return
            k = lambda t: str(t).lower() if isinstance(t, Sym) else None
            init, step, body, fin = [], [], [], []
            acc, acc_kind, result = None, None, None
            i = 0

            def take():
                nonlocal i
                x = toks[i]
                i += 1
                return x

            def accumulate(kind, e, cond=None):
                nonlocal acc, acc_kind
                s, v = self.compile(e)
                if acc is None:
                    acc = self.fresh()
                    acc_kind = kind
                    start = {'collect': ('list', []), 'append': ('list', []), 'sum': ('int', 0), 'count': ('int', 0),
                             'maximize': ('none',), 'minimize': ('none',)}[kind]
                    init.insert(0, ('assign', ('var', acc), start))
                A = ('var', acc)
                upd = {'collect': ('op', 'add', [A, ('list', [v])]), 'append': ('op', 'add', [A, v]),
                       'sum': ('op', 'add', [A, v]), 'count': ('cond', v, ('op', 'add', [A, ('int', 1)]), A),
                       'maximize': ('cond', ('op', 'or', [('op', 'eq', [A, ('none',)]), ('op', 'gt', [v, A])]), v, A),
                       'minimize': ('cond', ('op', 'or', [('op', 'eq', [A, ('none',)]), ('op', 'lt', [v, A])]), v, A)}[kind]
                st = s + [('assign', A, upd)]
                return [('if', cond, ('seq', st), ('skip',))] if cond is not None else st

            def clause(cond=None):
                """One body clause (after when/if/unless optionally); returns statements."""
                w = k(take())
                if w in ('do', 'doing'):
                    out = []
                    while i < len(toks) and isinstance(toks[i], list):
                        sb, _ = self.compile(take())
                        out += sb
                    return [('if', cond, ('seq', out), ('skip',))] if cond is not None else out
                if w in ('collect', 'collecting', 'append', 'appending', 'sum', 'summing', 'count', 'counting',
                         'maximize', 'maximizing', 'minimize', 'minimizing'):
                    kind = w.replace('ing', '').replace('collect', 'collect')
                    kind = {'collect': 'collect', 'append': 'append', 'sum': 'sum', 'summ': 'sum', 'count': 'count',
                            'maximiz': 'maximize', 'maximize': 'maximize', 'minimiz': 'minimize',
                            'minimize': 'minimize'}[kind]
                    e = take()
                    if i < len(toks) and k(toks[i]) == 'into':
                        raise ValueError('into')
                    return accumulate(kind, e, cond)
                if w == 'return':
                    s2, v = self.compile(take())
                    st = s2 + [('return', v)]
                    return [('if', cond, ('seq', st), ('skip',))] if cond is not None else st
                raise ValueError('clause ' + str(w))
            try:
                while i < len(toks):
                    w = k(toks[i])
                    if w in ('for', 'as'):
                        take()
                        v = str(take())
                        how = k(take())
                        if how == '=':
                            s1, v0 = self.compile(take())
                            init += s1 + [('assign', ('var', v), v0)]
                            if i < len(toks) and k(toks[i]) == 'then':
                                take()
                                s2, v1 = self.compile(take())
                                step += s2 + [('assign', ('var', v), v1)]
                            else:
                                step += s1 + [('assign', ('var', v), v0)]
                        elif how in ('from', 'upfrom', 'downfrom'):
                            s1, lo = self.compile(take())
                            init += s1 + [('assign', ('var', v), lo)]
                            down = how == 'downfrom'
                            limit, inclusive, by = None, True, ('int', 1)
                            while i < len(toks) and k(toks[i]) in ('to', 'upto', 'below', 'downto', 'above', 'by'):
                                kw = k(take())
                                s3, e3 = self.compile(take())
                                init += s3
                                if kw == 'by':
                                    by = e3
                                else:
                                    lim = self.fresh()
                                    init.append(('assign', ('var', lim), e3))
                                    limit, inclusive = ('var', lim), kw in ('to', 'upto', 'downto')
                                    down = down or kw in ('downto', 'above')
                            V = ('var', v)
                            step.append(('assign', V, ('op', 'sub' if down else 'add', [V, by])))
                            if limit is not None:
                                op = ('lt' if inclusive else 'le') if down else ('gt' if inclusive else 'ge')
                                test = ('if', ('op', op, [V, limit]), 'break', ('skip',))
                                init.append(test)
                                step.append(test)
                        elif how in ('in', 'across'):
                            s1, q = self.compile(take())
                            qv, ix = self.fresh(), self.fresh()
                            init += s1 + [('assign', ('var', qv), q), ('assign', ('var', ix), ('int', 0))]
                            if q[0] == 'var':                     # list parameter probe (battery kind)
                                init.insert(0, ('expr', ('call', 'len', [q])))
                            test = ('if', ('op', 'ge', [('var', ix), ('call', 'len', [('var', qv)])]), 'break', ('skip',))
                            get = ('assign', ('var', v), ('elem', ('var', qv), ('var', ix)))
                            init += [test, get]
                            step += [('assign', ('var', ix), ('op', 'add', [('var', ix), ('int', 1)])), test, get]
                        else:
                            raise ValueError('for ' + str(how))
                    elif w == 'with':
                        take()
                        v = str(take())
                        if i < len(toks) and k(toks[i]) == '=':
                            take()
                            s1, v0 = self.compile(take())
                        else:
                            s1, v0 = [], ('bool', 'false')
                        init += s1 + [('assign', ('var', v), v0)]
                    elif w == 'repeat':
                        take()
                        s1, n = self.compile(take())
                        c = self.fresh()
                        init += s1 + [('assign', ('var', c), n),
                                      ('if', ('op', 'le', [('var', c), ('int', 0)]), 'break', ('skip',))]
                        step += [('assign', ('var', c), ('op', 'sub', [('var', c), ('int', 1)])),
                                 ('if', ('op', 'le', [('var', c), ('int', 0)]), 'break', ('skip',))]
                    elif w in ('while', 'until'):
                        take()
                        s1, c = self.compile(take())
                        body += s1 + [('if', c if w == 'until' else ('op', 'not', [c]), 'break', ('skip',))]
                    elif w in ('when', 'if', 'unless'):
                        take()
                        s1, c = self.compile(take())
                        body += s1 + clause(('op', 'not', [c]) if w == 'unless' else c)
                    elif w == 'finally':
                        take()
                        while i < len(toks) and isinstance(toks[i], list):
                            f = take()
                            if f and k(f[0]) == 'return':
                                s1, result = self.compile(f[1]) if len(f) > 1 else ([], ('bool', 'false'))
                                fin += s1
                            else:
                                s1, _ = self.compile(f)
                                fin += s1
                    else:
                        body += clause()
            except (ValueError, IndexError):
                return [('unsupported', 'loop_clause')], ('none',)
            first = self.fresh()
            loop = [('assign', ('var', first), ('bool', 'true')),
                    ('while', ('bool', 'true'), ('seq', [
                        ('if', ('var', first), ('seq', init), ('seq', step)),
                        ('assign', ('var', first), ('bool', 'false'))] + body))]
            value = result if result is not None else (('var', acc) if acc else ('bool', 'false'))
            return loop + fin, value

        def f_member(self, a):
            s, vs = self.many(a[:2])
            return s, ('op', 'in', vs)

        def f_multiple_value_bind(self, a):
            names, form, body = a[0], a[1], a[2:]
            if isinstance(form, list) and form and form[0] in ('floor', 'truncate') and len(form) == 3:
                s, (x, y) = self.many(form[1:])
                stmts = s
                for i, n in enumerate(names[:2]):
                    stmts.append(('assign', ('var', str(n)), ('elem', ('call', 'divmod', [x, y]), ('int', i))))
                sb, v = self.compile_body(body)
                return stmts + sb, v
            return [('unsupported', 'multiple_value_bind')], ('none',)

        def lam_parts(self, f):
            if isinstance(f, list) and f and f[0] == 'function':
                f = f[1]
            if isinstance(f, list) and f and f[0] == 'lambda':
                return [str(p) for p in f[1] if not str(p).startswith('&')], f[2:]
            return None

        def f_reduce(self, a):
            fn, seq, kw = a[0], a[1], a[2:]
            lp = self.lam_parts(fn)
            if lp is None or len(lp[0]) != 2:
                return super().f_reduce(a)
            s, q = self.compile(seq)
            opts = dict(zip([str(k) for k in kw[0::2]], kw[1::2]))
            acc, x = self.fresh(), self.fresh()
            if ':initial-value' in opts:
                si, init = self.compile(opts[':initial-value'])
                s, items = s + si, q
            else:
                init, items = ('elem', q, ('int', 0)), ('slice', q, ('int', 1), ('none',), ('none',))
            (p1, p2), body = lp
            sb, vb = self.compile_body(body)
            loop = [('assign', ('var', acc), init),
                    ('for_each', x, items, ('seq', [('assign', ('var', p1), ('var', acc)),
                                                     ('assign', ('var', p2), ('var', x))] + sb +
                                            [('assign', ('var', acc), vb)]))]
            return s + loop, ('var', acc)

        def f_labels(self, a):
            """Local functions are lifted to top level; the enclosing variables they use become
            extra leading parameters, and calls inside pass them along."""
            defs, body = a[0], a[1:]
            outer = list(getattr(self, 'scope', []))
            names = [str(d[0]) for d in defs]
            used = {}
            for d in defs:
                syms = set()
                _symbols(d[2:], syms)
                used[str(d[0])] = [v for v in outer if v in syms and v not in [str(p) for p in d[1]]]
            extra = sorted({v for vs in used.values() for v in vs})
            renamed = {n: f'{n}$l{next(self.tmp)}' for n in names}
            for d in defs:
                lam = [Sym(v) for v in extra] + list(d[1])
                fbody = _rename_calls(d[2:], renamed, extra)
                saved = getattr(self, 'scope', [])
                L.LispPNF.defun(self, [Sym('defun'), Sym(renamed[str(d[0])]), lam] + fbody)
                self.scope = saved
            return self.compile_body(_rename_calls(body, renamed, extra))
        f_flet = f_labels

        def f_let(self, a):
            for b in a[0]:
                name = b[0] if isinstance(b, list) else b
                if hasattr(self, 'scope'):
                    self.scope.append(str(name))
            return super().f_let(a)
        f_let_ = f_let

    return LispPNF2


def _symbols(t, out):
    if isinstance(t, list):
        for x in t:
            _symbols(x, out)
    elif isinstance(t, str) and not isinstance(t, tuple):
        out.add(str(t))


def _rename_calls(t, renamed, extra):
    L = _base()
    if isinstance(t, list):
        if t and isinstance(t[0], str) and str(t[0]) in renamed:
            return [L.Sym(renamed[str(t[0])])] + [L.Sym(v) for v in extra] + [_rename_calls(x, renamed, extra) for x in t[1:]]
        if t and t[0] == 'function' and len(t) == 2 and isinstance(t[1], str) and str(t[1]) in renamed:
            return [L.Sym('function'), L.Sym(renamed[str(t[1])])]
        return [_rename_calls(x, renamed, extra) for x in t]
    return t


_CLS = None


def lisp_normal_form_sbcl(path: Path):
    global _CLS
    if _CLS is None:
        _CLS = _make_class()
    expanded = sbcl_expand(path)
    return list_probes(_CLS().run(expanded)) if expanded.strip() else []


SEQ_CALLS = {'len', 'reverse', 'sorted', 'sum', 'product', 'max', 'min', 'list', 'index', 'all', 'any'}


def list_probes(funs):
    """A parameter used as a sequence (element access, slicing, iteration, sequence builtins,
    string/list equality with a reversed copy) gets a len() probe, so the battery feeds it lists."""
    out = []
    for name, params, body in funs:
        seq = set()

        def walk(t, seq):
            if isinstance(t, tuple) and t:
                if t[0] in ('elem', 'slice') and t[1][:1] == ('var',):
                    seq.add(t[1][1])
                if t[0] == 'call' and t[1] in SEQ_CALLS:
                    seq.update(a[1] for a in t[2] if a[:1] == ('var',))
                if t[0] == 'comp' and t[2][:1] == ('var',):
                    seq.add(t[2][1])
                if t[0] == 'for_each' and t[2][:1] == ('var',):
                    seq.add(t[2][1])
                for x in t[1:]:
                    walk(x, seq)
            elif isinstance(t, list):
                for x in t:
                    walk(x, seq)
        walk(body, seq)
        probes = [('expr', ('call', 'len', [('var', p)])) for p in params if p in seq]
        out.append((name, params, ('seq', probes + list(body[1])) if probes and body[0] == 'seq' else body))
    return out
