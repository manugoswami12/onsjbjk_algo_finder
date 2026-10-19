"""v0.3 fix of the Lisp loop macro's `finally` clause (doc 04 section 18.7), kept separate from the pipeline:
polyglot_logic/tools/lisp_to_prolog.py is not edited; install() changes its LispPNF.f_loop in this process only
(the way crosslang_frontends plugs its front ends into io_trace).

AP13's f_loop puts the `finally` form in `post`, which is also where `for x = e then e2` keeps its per-iteration
update, and `post` is the end of the loop BODY. So (loop for i from 2 upto n do (setf leo ...) finally (return
(first leo))) returned after the first iteration: fibonacci-sequence-9.lisp gave fib(n) = 1 for every n >= 2, the
behaviour of signum. Here the `finally` form runs once, after the loop, as the Common Lisp standard says.
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
    original = lisp_to_prolog.LispPNF.f_loop

    def f_loop(self, a):
        rest, finals, i = [], [], 0
        while i < len(a):
            if a[i] == 'finally' and i + 1 < len(a):
                finals.append(a[i + 1])
                i += 2
                continue
            rest.append(a[i])
            i += 1
        stmts, value = original(self, rest)
        for form in finals:
            s, _ = self.compile(form)
            stmts = stmts + s
        return stmts, value

    lisp_to_prolog.LispPNF.f_loop = f_loop
    _installed = True
