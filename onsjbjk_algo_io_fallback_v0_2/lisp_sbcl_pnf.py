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

import subprocess
import tempfile
from pathlib import Path

import compare_learners

KEEP = '''defun let let* setf setq incf decf rotatef push if when unless cond and or not progn quote
function lambda dotimes dolist do loop return return-from block the declare locally labels flet
multiple-value-bind psetq psetf'''.split()

SBCL_SCRIPT = r'''
(defpackage :v02x (:use :cl))
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


def sbcl_expand(path: Path, timeout=60) -> str:
    script = SBCL_SCRIPT.replace('%KEEP%', ' '.join(f'"{k}"' for k in KEEP))
    with tempfile.TemporaryDirectory(prefix='v02_sbcl_') as td:
        sf = Path(td) / 'expand.lisp'
        sf.write_text(script, encoding='utf-8')
        proc = subprocess.run(['sbcl', '--script', str(sf), str(path)], capture_output=True, text=True,
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

        def f_values(self, a):
            return self.compile(a[0]) if a else ([], ('none',))

        def f_char_code(self, a):
            return self.compile(a[0])
        f_code_char = f_char_code

        def f_map(self, a):
            # (map 'list fn seq): like mapcar
            return self.f_mapcar(a[1:3])

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
    return _CLS().run(expanded) if expanded.strip() else []
