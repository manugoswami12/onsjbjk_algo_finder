"""v0.3 fixes of the behaviour lowering (doc 04 section 18.7), kept separate from the pipeline: polyglot_logic's
lisp_to_prolog.py and to_prolog.py are not edited; install() changes two of their methods in this process only (the
way crosslang_frontends plugs its front ends into io_trace).

  Lisp `finally`   AP13's LispPNF.f_loop puts the `finally` form in `post`, which is also where `for x = e then e2`
                   keeps its per-iteration update, and `post` is the end of the loop BODY. So (loop for i from 2 upto
                   n do (setf leo ...) finally (return (first leo))) returned after the first iteration:
                   fibonacci-sequence-9.lisp gave fib(n) = 1 for every n >= 2, the behaviour of signum. Here the
                   `finally` form runs once, after the loop, as the Common Lisp standard says.
  C/Java  x op= y  PNFLowerer.assign_term applies the operator only to the aug_assign kind (Python, Rust); C and Java
                   write `result *= i` as an assignment_expression with an operator field, so it became result = i:
                   factorial-2.c computed n, the behaviour of MaxFenwickTree.get_next. The structure lowering
                   (lower_imperative.py) already reads the operator; here the behaviour lowering does too.
"""
from __future__ import annotations

_installed = False


def install():
    global _installed
    if _installed:
        return
    import compare_learners
    compare_learners._ap13()
    import lisp_to_prolog
    import to_prolog
    from lang_tables import AUGMENTED
    loop = lisp_to_prolog.LispPNF.f_loop

    def f_loop(self, a):
        rest, finals, i = [], [], 0
        while i < len(a):
            if a[i] == 'finally' and i + 1 < len(a):
                finals.append(a[i + 1])
                i += 2
                continue
            rest.append(a[i])
            i += 1
        stmts, value = loop(self, rest)
        for form in finals:
            s, _ = self.compile(form)
            stmts = stmts + s
        return stmts, value

    assign = to_prolog.PNFLowerer.assign_term

    def assign_term(self, node, kind, roles):
        if kind == 'assign':
            opnode = self.role(node, roles, 'op')
            if opnode is not None and to_prolog.text(opnode) in AUGMENTED:
                kind = 'aug_assign'
        return assign(self, node, kind, roles)

    lisp_to_prolog.LispPNF.f_loop = f_loop
    to_prolog.PNFLowerer.assign_term = assign_term
    _installed = True
