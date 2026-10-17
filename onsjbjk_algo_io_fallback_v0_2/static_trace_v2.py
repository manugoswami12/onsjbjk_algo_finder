"""v0.2 evidence extraction: the v0.1 analysis (static_trace.py, unchanged) plus more
conservative witnesses. Source only: stdlib `ast`; no candidate source is executed.

Each witness is a local, syntactic dependency pattern tied to the function's inputs,
named after an established notion (docs/01_V02_REQUIREMENTS_DESIGN.md, section 8):
  roles of variables (Sajaniemi): gatherer, most-wanted holder, stepper, one-way flag
  loop idioms / recurrences (LLVM LoopIdiomRecognize, ScalarEvolution chains of recurrences)
  reductions (Ginsbach & O'Boyle), data dependence on inputs (Weiser slicing, PDG)
"""
from __future__ import annotations

import ast
import re

from static_trace import (Analysis, analyse, coherent_interval_search, same, statements,
                          subscript_on, used_names)


# ---------- small shared helpers (base for every witness: critical, see doc table 6) ----------

def tainted_names(result: Analysis, inputs: set[str]) -> set[str]:
    """Names that may depend on an input (from the v0.1 may-depend-on fixpoint)."""
    return {n for n, origins in result.dependencies.items() if set(origins) & inputs} | inputs


def returned_names(rows) -> set[str]:
    out = set()
    for stmt, _, _ in rows:
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            out |= used_names(stmt.value)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Yield, ast.YieldFrom)) and stmt.value.value:
            out |= used_names(stmt.value.value)      # a generator's output
    return out


def is_name(expr, name=None):
    return isinstance(expr, ast.Name) and (name is None or expr.id == name)


def is_const(expr, value):
    return isinstance(expr, ast.Constant) and type(expr.value) is type(value) and expr.value == value


def binop(expr, op):
    return isinstance(expr, ast.BinOp) and isinstance(expr.op, op)


def loop_driven_by(loop, tainted):
    """Stepper role: the loop's iteration space depends on an input."""
    head = loop.iter if isinstance(loop, ast.For) else loop.test
    return bool(used_names(head) & tainted)


def element_of_input(expr, loops, inputs):
    """An input element: A[...] with A an input, the target of `for x in A`,
    or x of `for i, x in enumerate(A)`."""
    if subscript_on(expr, inputs):
        return True
    return is_name(expr) and any((isinstance(l, ast.For) and is_name(l.target, expr.id)
                                  and is_name(l.iter) and l.iter.id in inputs)
                                 or enumerate_pair(l, inputs)[2:] == (expr.id,) for l in loops)


def enumerate_pair(loop, inputs):
    """`for i, x in enumerate(A)` with A an input -> (A, i, x), else ()."""
    if (isinstance(loop, ast.For) and isinstance(loop.target, ast.Tuple) and len(loop.target.elts) == 2
            and all(is_name(t) for t in loop.target.elts) and isinstance(loop.iter, ast.Call)
            and is_name(loop.iter.func, 'enumerate') and len(loop.iter.args) == 1
            and is_name(loop.iter.args[0]) and loop.iter.args[0].id in inputs):
        return (loop.iter.args[0].id,) + tuple(t.id for t in loop.target.elts)
    return ()


def range_loop_var(expr, loops, tainted):
    """The target of an enclosing `for i in range(..input..)`."""
    return is_name(expr) and any(isinstance(l, ast.For) and is_name(l.target, expr.id)
                                 and isinstance(l.iter, ast.Call) and is_name(l.iter.func, 'range')
                                 and loop_driven_by(l, tainted) for l in loops)


def accumulation(stmt):
    """Gatherer update: acc += v | acc *= v | acc = acc + v | acc = acc * v -> (acc, op, v)."""
    if isinstance(stmt, ast.AugAssign) and is_name(stmt.target) and isinstance(stmt.op, (ast.Add, ast.Mult)):
        return stmt.target.id, type(stmt.op), stmt.value
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and is_name(stmt.targets[0])
            and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, (ast.Add, ast.Mult))
            and is_name(stmt.value.left, stmt.targets[0].id)):
        return stmt.targets[0].id, type(stmt.value.op), stmt.value.right
    return None


def assigns(stmt, name):
    """Value assigned to `name` by `name = v`, `name //= k` style statements (normalised)."""
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and is_name(stmt.targets[0], name):
        return stmt.value
    if isinstance(stmt, ast.AugAssign) and is_name(stmt.target, name):
        return ast.BinOp(left=ast.Name(id=name, ctx=ast.Load()), op=stmt.op, right=stmt.value)
    return None


def self_calls(node, fname):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call) and is_name(n.func, fname)]


def minus(expr, name, k):  # name - k
    return binop(expr, ast.Sub) and is_name(expr.left, name) and is_const(expr.right, k)


def true_compares(guards):
    for if_stmt, polarity in guards:
        if polarity and isinstance(if_stmt.test, ast.Compare) and len(if_stmt.test.ops) == 1:
            yield if_stmt


# ---------- witnesses, one function per witness ----------

def w_sorting(result, rows, inputs):
    """Insertion: shifting write A[x+1] = A[x] in a while loop (comparison in the loop test).
    Selection: guarded min-index update m = j from A[j] vs A[m], then exchange with A[m]."""
    min_index = {}
    for stmt, guards, loops in rows:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Subscript) and isinstance(stmt.value, ast.Subscript)
                and loops and isinstance(loops[-1], ast.While)):
            name = subscript_on(stmt.targets[0], inputs)
            if name and subscript_on(stmt.value, {name}) == name:
                dst, src = stmt.targets[0].slice, stmt.value.slice
                if ((binop(dst, ast.Add) and is_const(dst.right, 1) and same(dst.left, src)) or
                        (binop(src, ast.Sub) and is_const(src.right, 1) and same(src.left, dst))):
                    result.add('input_sequence_mutated', stmt.lineno)
                    result.add('adjacent_shift_write', stmt.lineno)
                    loop = loops[-1]
                    if any(isinstance(c, ast.Compare) and any(subscript_on(x, {name}) == name
                                                             for x in [c.left] + c.comparators)
                           for c in ast.walk(loop.test)):
                        result.add('comparison_controls_shift', loop.lineno)
                        result.add('comparison_controls_shift', stmt.lineno)
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and is_name(stmt.targets[0])
                and is_name(stmt.value)):
            m, j = stmt.targets[0].id, stmt.value.id
            for if_stmt in true_compares(guards):
                c = if_stmt.test
                if not isinstance(c.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                    continue
                l, r = c.left, c.comparators[0]
                name = subscript_on(l, inputs)
                if name and subscript_on(r, {name}) and {ast.unparse(l.slice), ast.unparse(r.slice)} == {m, j}:
                    min_index[(name, m)] = (if_stmt.lineno, stmt.lineno)
    for stmt, _, _ in rows:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Tuple)
                and isinstance(stmt.value, ast.Tuple) and 'element_exchange' in result.evidence
                and stmt.lineno in result.evidence['element_exchange']):
            lhs = stmt.targets[0].elts
            name = subscript_on(lhs[0], inputs)
            for (arr, m), lines in min_index.items():
                if arr == name and any(is_name(x.slice, m) for x in lhs):
                    for line in lines + (stmt.lineno,):
                        result.add('min_index_then_exchange', line)


def w_aggregate(result, rows, inputs, tainted, returned):
    """Gatherer over input elements; most-wanted holder (best-so-far); range sum/product."""
    for stmt, guards, loops in rows:
        acc = accumulation(stmt)
        if acc and loops and acc[0] in returned:
            name, op, value = acc
            if element_of_input(value, loops, inputs):
                result.add('input_element_accumulated', stmt.lineno)
            elif range_loop_var(value, loops, tainted):
                result.add('range_product' if op is ast.Mult else 'range_sum', stmt.lineno)
        if (loops and isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and is_name(stmt.targets[0]) and stmt.targets[0].id in returned):
            best, value = stmt.targets[0].id, stmt.value
            for if_stmt in true_compares(guards):
                c = if_stmt.test
                if not isinstance(c.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                    continue
                sides = (c.left, c.comparators[0])
                value_vs_best = any(same(a, value) and element_of_input(a, loops, inputs) and is_name(b, best)
                                    for a, b in (sides, sides[::-1]))
                index_vs_index = (is_name(value) and subscript_on(sides[0], inputs) and
                                  subscript_on(sides[1], inputs) and
                                  {ast.unparse(sides[0].slice), ast.unparse(sides[1].slice)} == {best, value.id})
                if value_vs_best or index_vs_index:
                    result.add('best_so_far_update', if_stmt.lineno)
                    result.add('best_so_far_update', stmt.lineno)
            # best = min(best, x) / max(x, best): the builtin is the guarded update
            if (isinstance(value, ast.Call) and is_name(value.func) and value.func.id in ('min', 'max')
                    and len(value.args) == 2 and not value.keywords
                    and any(is_name(a, best) and element_of_input(b, loops, inputs)
                            for a, b in (value.args, value.args[::-1]))):
                result.add('best_so_far_update', stmt.lineno)


def w_lookup(result, rows, inputs, returned):
    """Indexed lookup when the logic is wired through locals (Sajaniemi follower / stored result):
    x = A[i]; if x == t: ... ; and `return i` or `r = i` with r returned.
    Emits the v0.1 facts, so the v0.1 lookup rules route it unchanged."""
    followers = {}                                # x -> (A, i) from x = A[i] inside a loop
    for stmt, _, loops in rows:
        if (loops and isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and is_name(stmt.targets[0])
                and subscript_on(stmt.value, inputs) and is_name(stmt.value.slice)):
            followers[stmt.targets[0].id] = (stmt.value.value.id, stmt.value.slice.id)
        pair = enumerate_pair(stmt, inputs)
        if pair:
            followers[pair[2]] = (pair[0], pair[1])
    witnesses = []
    for stmt, guards, loops in rows:
        if not loops:
            continue
        if isinstance(stmt, ast.Return) and is_name(stmt.value):
            idx = stmt.value.id
        elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and is_name(stmt.targets[0])
              and stmt.targets[0].id in returned and is_name(stmt.value)):
            idx = stmt.value.id
        else:
            continue
        for if_stmt in true_compares(guards):
            c = if_stmt.test
            if not isinstance(c.ops[0], ast.Eq):
                continue
            for elem, target in ((c.left, c.comparators[0]), (c.comparators[0], c.left)):
                if not (is_name(target) and target.id in inputs):
                    continue
                if is_name(elem) and elem.id in followers:
                    arr, i = followers[elem.id]
                elif subscript_on(elem, inputs) and is_name(elem.slice):
                    arr, i = elem.value.id, elem.slice.id
                else:
                    continue
                if i == idx and arr != target.id:
                    result.add('indexed_equality_controls_index_return', if_stmt.lineno)
                    result.add('indexed_equality_controls_index_return', stmt.lineno)
                    witnesses += [(arr, i, if_stmt.lineno, loop) for loop in loops]
    if 'coherent_midpoint_interval_update' not in result.evidence:
        for witness in witnesses:
            found = coherent_interval_search(rows, witness)
            if found:
                for line in found:
                    result.add('coherent_midpoint_interval_update', line)
                break


def w_slice_halving(result, fn, rows, inputs):
    """mid = len(A) // 2 and self-calls on A[:mid] and A[mid + 1:] (recursive halving search)."""
    mids = {s.targets[0].id for s, _, _ in rows if isinstance(s, ast.Assign) and len(s.targets) == 1
            and is_name(s.targets[0]) and binop(s.value, ast.FloorDiv) and is_const(s.value.right, 2)
            and isinstance(s.value.left, ast.Call) and is_name(s.value.left.func, 'len')
            and len(s.value.left.args) == 1 and is_name(s.value.left.args[0])
            and s.value.left.args[0].id in inputs}
    halves = set()
    for stmt, guards, _ in rows:
        if not (isinstance(stmt, ast.Return) and guards):
            continue
        for c in self_calls(stmt, fn.name):
            for a in c.args:
                if (isinstance(a, ast.Subscript) and is_name(a.value) and a.value.id in inputs
                        and isinstance(a.slice, ast.Slice) and a.slice.step is None):
                    lo, hi = a.slice.lower, a.slice.upper
                    if lo is None and is_name(hi) and hi.id in mids:
                        halves.add(('low', stmt.lineno))
                    if (hi is None and binop(lo, ast.Add) and is_name(lo.left) and lo.left.id in mids
                            and is_const(lo.right, 1)):
                        halves.add(('high', stmt.lineno))
    if {h for h, _ in halves} == {'low', 'high'}:
        for _, line in halves:
            result.add('slice_halving_self_call', line)


def w_membership(result, rows, inputs):
    """`for x in A: if x == t: return True` with A and t inputs."""
    for stmt, guards, loops in rows:
        if not (isinstance(stmt, ast.Return) and is_const(stmt.value, True)):
            continue
        for if_stmt in true_compares(guards):
            c = if_stmt.test
            if not isinstance(c.ops[0], ast.Eq):
                continue
            for a, b in ((c.left, c.comparators[0]), (c.comparators[0], c.left)):
                if (element_of_input(a, loops, inputs) and is_name(b) and b.id in inputs
                        and not (is_name(a) and a.id == b.id)):
                    result.add('element_equality_controls_true_return', if_stmt.lineno)
                    result.add('element_equality_controls_true_return', stmt.lineno)


def w_recurrence(result, fn, rows, inputs, tainted, returned):
    """Chains of recurrences: (a, b) <- (b, a + b); Euclid (a, b) <- (b, a % b), loop or
    self-call; n * f(n - 1); two self-calls f(n - 1) + f(n - 2)."""
    for stmt, _, loops in rows:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Tuple)
                and isinstance(stmt.value, ast.Tuple) and len(stmt.targets[0].elts) == 2
                and len(stmt.value.elts) == 2 and all(is_name(t) for t in stmt.targets[0].elts)):
            x, y = (t.id for t in stmt.targets[0].elts)
            v1, v2 = stmt.value.elts
            if not (is_name(v1, y) and loops and loop_driven_by(loops[-1], tainted) and {x, y} & returned):
                continue
            if binop(v2, ast.Add) and {ast.unparse(v2.left), ast.unparse(v2.right)} == {x, y}:
                result.add('pair_recurrence', stmt.lineno)
            if (binop(v2, ast.Mod) and is_name(v2.left, x) and is_name(v2.right, y)
                    and isinstance(loops[-1], ast.While) and y in used_names(loops[-1].test)):
                result.add('modulo_recurrence', stmt.lineno)
    for stmt, _, loops in rows:                 # list recurrence L.append(L[-1] + L[-2]) / L[i] = L[i-1] + L[i-2]
        if not (loops and loop_driven_by(loops[-1], tainted)):
            continue
        if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == 'append'
                and is_name(stmt.value.func.value) and len(stmt.value.args) == 1):
            arr, v, dst = stmt.value.func.value.id, stmt.value.args[0], None
            terms = {'-1', '-2'}
        elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Subscript)
              and is_name(stmt.targets[0].value) and is_name(stmt.targets[0].slice)):
            arr, v, dst = stmt.targets[0].value.id, stmt.value, stmt.targets[0].slice.id
            terms = {f'{dst} - 1', f'{dst} - 2'}
        else:
            continue
        if (arr in returned and binop(v, ast.Add) and all(isinstance(x, ast.Subscript) and is_name(x.value, arr)
                                                          for x in (v.left, v.right))
                and {ast.unparse(v.left.slice), ast.unparse(v.right.slice)} == terms):
            result.add('list_recurrence_two_terms', stmt.lineno)
    for stmt, _, _ in rows:                     # three-statement Euclid: t = a % b; a = b; b = t
        if isinstance(stmt, ast.While) and len(stmt.body) >= 3:
            for s1, s2, s3 in zip(stmt.body, stmt.body[1:], stmt.body[2:]):
                if (isinstance(s1, ast.Assign) and is_name(s1.targets[0]) and binop(s1.value, ast.Mod)
                        and is_name(s1.value.left) and is_name(s1.value.right)):
                    t, a, b = s1.targets[0].id, s1.value.left.id, s1.value.right.id
                    if (is_name(assigns(s2, a), b) and is_name(assigns(s3, b), t)
                            and b in used_names(stmt.test) and a in returned and a in tainted):
                        result.add('modulo_recurrence', s1.lineno)
    params = [a.arg for a in fn.args.args]

    def parts(stmt):
        """Value expressions of a statement; `return b if c else e` contributes both arms."""
        v = stmt.value
        if isinstance(stmt, ast.Return) and isinstance(v, ast.IfExp):
            return [v.body, v.orelse]
        return [v]

    # Base case: a guarded return without a self-call, or an inline `x if c else ...` arm without one.
    has_base_case = any(isinstance(s, ast.Return) and s.value is not None and (
        (g and not self_calls(s, fn.name)) or
        (isinstance(s.value, ast.IfExp) and any(not self_calls(e, fn.name) for e in parts(s))))
        for s, g, _ in rows)
    for stmt, _, _ in rows:
        if not isinstance(stmt, (ast.Return, ast.Assign, ast.AugAssign)) or stmt.value is None:
            continue
        for value in parts(stmt):
            calls = self_calls(value, fn.name)
            if (isinstance(stmt, ast.Return) and len(calls) == 1 and len(params) == 2
                    and len(calls[0].args) == 2 and is_name(calls[0].args[0], params[1])
                    and binop(calls[0].args[1], ast.Mod) and is_name(calls[0].args[1].left, params[0])
                    and is_name(calls[0].args[1].right, params[1]) and value is calls[0]):
                result.add('modulo_recurrence', stmt.lineno)
            if not has_base_case or len(params) != 1:
                continue
            p = params[0]
            if (isinstance(stmt, ast.Return) and binop(value, ast.Mult) and len(calls) == 1
                    and len(calls[0].args) == 1 and minus(calls[0].args[0], p, 1)
                    and any(is_name(x, p) for x in (value.left, value.right))):
                result.add('linear_self_product', stmt.lineno)
            if len(calls) >= 2:
                result.add('double_self_call', stmt.lineno)
                args = [c.args[0] for c in calls if len(c.args) == 1]
                if (len(calls) == 2 and len(args) == 2 and binop(value, ast.Add)
                        and sorted(ast.unparse(a) for a in args) == [f'{p} - 1', f'{p} - 2']):
                    result.add('self_calls_minus_one_minus_two', stmt.lineno)


def w_number(result, rows, tainted):
    """Digit decomposition (n % 10, n //= 10); divisor test n % d == 0 with stepper d;
    Collatz step: parity test with n // 2 and 3 * n + 1 in one input-driven while loop."""
    for stmt, _, loops in rows:
        if isinstance(stmt, ast.While):
            loop_rows = [(s, g, l) for s, g, l in rows if stmt in l]
            heads = used_names(stmt.test)
            if is_const(stmt.test, True):            # while True: ... if <test on n>: break
                heads = set().union(*(used_names(s.test) for s, _, _ in loop_rows if isinstance(s, ast.If)
                                      and any(isinstance(b, ast.Break) for b in s.body)))
            for n in heads & tainted:
                values = [(s.lineno, assigns(s, n)) for s, _, _ in loop_rows]
                values = [(line, v) for line, v in values if v is not None]
                halves = [line for line, v in values
                          if (binop(v, ast.FloorDiv) and is_name(v.left, n) and is_const(v.right, 2))
                          or (binop(v, ast.RShift) and is_name(v.left, n) and is_const(v.right, 1))]
                tens = [line for line, v in values if binop(v, ast.FloorDiv) and is_name(v.left, n)
                        and is_const(v.right, 10)]
                triples = [line for line, v in values if binop(v, ast.Add) and is_const(v.right, 1)
                           and binop(v.left, ast.Mult)
                           and {ast.unparse(v.left.left), ast.unparse(v.left.right)} == {n, '3'}]
                mods = [x for s, _, _ in loop_rows for x in ast.walk(s) if binop(x, ast.Mod)
                        and is_name(x.left, n)]
                counts = [s for s, _, _ in loop_rows if isinstance(s, ast.AugAssign) and isinstance(s.op, ast.Add)
                          and is_name(s.target) and is_const(s.value, 1)]
                if tens and (any(is_const(x.right, 10) for x in mods) or counts):
                    for line in [stmt.lineno] + tens:
                        result.add('digit_decomposition', line)
                parity = [s.lineno for s, _, _ in loop_rows if isinstance(s, ast.If) and any(
                    (binop(x, ast.Mod) and is_name(x.left, n) and is_const(x.right, 2)) or
                    (binop(x, ast.BitAnd) and is_name(x.left, n) and is_const(x.right, 1))
                    for x in ast.walk(s.test))]
                if parity and halves and triples:
                    for line in [stmt.lineno] + parity + halves + triples:
                        result.add('parity_halving_or_triple', line)
        if isinstance(stmt, ast.If) and loops:
            for c in ast.walk(stmt.test):
                if not (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], ast.Eq)
                        and is_const(c.comparators[0], 0) and binop(c.left, ast.Mod)
                        and is_name(c.left.left) and c.left.left.id in tainted and is_name(c.left.right)):
                    continue
                d = c.left.right.id
                if any((isinstance(l, ast.For) and is_name(l.target, d)) or
                       (isinstance(l, ast.While) and d in used_names(l.test)) for l in loops):
                    result.add('divisor_test_in_loop', stmt.lineno)


def stepped(loop, name):
    """Stepper role in a while loop: `name += 1` in its body (top level)."""
    return any(isinstance(s, ast.AugAssign) and is_name(s.target, name) and isinstance(s.op, ast.Add)
               and is_const(s.value, 1) for s in loop.body)


def w_marking(result, rows, tainted):
    """Strided marking: for j in range(s, n, p): M[j] = const, inside `for p in ...`;
    one-way flag M[p] guarding the strided loop (sieve)."""
    for stmt, guards, loops in rows:
        if not (isinstance(stmt, ast.For) and is_name(stmt.target) and isinstance(stmt.iter, ast.Call)
                and is_name(stmt.iter.func, 'range') and len(stmt.iter.args) == 3
                and is_name(stmt.iter.args[2]) and used_names(stmt.iter.args[1]) & tainted):
            continue
        j, p = stmt.target.id, stmt.iter.args[2].id
        if not any((isinstance(l, ast.For) and is_name(l.target, p)) or
                   (isinstance(l, ast.While) and p in used_names(l.test) and stepped(l, p)) for l in loops):
            continue
        marks = [s for s in ast.walk(stmt) if isinstance(s, ast.Assign) and len(s.targets) == 1
                 and isinstance(s.targets[0], ast.Subscript) and is_name(s.targets[0].value)
                 and is_name(s.targets[0].slice, j) and isinstance(s.value, ast.Constant)]
        for s in marks:
            arr = s.targets[0].value.id
            result.add('stride_marking', stmt.lineno)
            result.add('stride_marking', s.lineno)
            for if_stmt, _ in guards:
                if any(isinstance(x, ast.Subscript) and is_name(x.value, arr) and is_name(x.slice, p)
                       for x in ast.walk(if_stmt.test)):
                    result.add('flag_guards_stride', if_stmt.lineno)


MIRROR = (r'^-{i} - 1$', r'^-1 - {i}$', r'^~{i}$', r'^.+ - 1 - {i}$', r'^.+ - {i} - 1$')


def mirror_pair(c, inputs, two_pointer):
    """A[i] vs A[mirror(i)], A[i] vs A[j] with i up / j down, or A == A[::-1]."""
    if not (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], (ast.Eq, ast.NotEq))):
        return False
    l, r = c.left, c.comparators[0]
    for a, b in ((l, r), (r, l)):
        if (is_name(a) and a.id in inputs and isinstance(b, ast.Subscript) and is_name(b.value, a.id)
                and isinstance(b.slice, ast.Slice) and b.slice.lower is None and b.slice.upper is None
                and b.slice.step is not None and ast.unparse(b.slice.step) == '-1'):
            return True
        name = subscript_on(a, inputs)
        if name and subscript_on(b, {name}) and is_name(a.slice):
            i = re.escape(a.slice.id)
            if any(re.match(p.format(i=i), ast.unparse(b.slice)) for p in MIRROR):
                return True
            if is_name(b.slice) and (a.slice.id, b.slice.id) in two_pointer:
                return True
    return False


def w_mirror(result, rows, inputs):
    ups = {s.target.id for s, _, l in rows if l and isinstance(s, ast.AugAssign) and is_name(s.target)
           and isinstance(s.op, ast.Add) and is_const(s.value, 1)}
    downs = {s.target.id for s, _, l in rows if l and isinstance(s, ast.AugAssign) and is_name(s.target)
             and isinstance(s.op, ast.Sub) and is_const(s.value, 1)}
    two_pointer = {(i, j) for i in ups for j in downs}
    for stmt, guards, _ in rows:
        if isinstance(stmt, ast.If) and any(mirror_pair(c, inputs, two_pointer) for c in ast.walk(stmt.test)):
            result.add('mirror_compare', stmt.lineno)
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            if any(mirror_pair(c, inputs, two_pointer) for c in ast.walk(stmt.value)):
                result.add('mirror_compare', stmt.lineno)
                result.add('mirror_compare_decides_result', stmt.lineno)
            elif isinstance(stmt.value, ast.Constant) and type(stmt.value.value) is bool:
                for if_stmt, _ in guards:
                    if any(mirror_pair(c, inputs, two_pointer) for c in ast.walk(if_stmt.test)):
                        result.add('mirror_compare_decides_result', if_stmt.lineno)
                        result.add('mirror_compare_decides_result', stmt.lineno)


def analyse_v2(fn) -> Analysis:
    result = analyse(fn)                       # v0.1 facts, unchanged
    inputs = set(result.inputs)
    rows = list(statements(fn.body))
    tainted = tainted_names(result, inputs)
    returned = returned_names(rows)
    w_sorting(result, rows, inputs)
    w_aggregate(result, rows, inputs, tainted, returned)
    w_lookup(result, rows, inputs, returned)
    w_membership(result, rows, inputs)
    w_slice_halving(result, fn, rows, inputs)
    w_recurrence(result, fn, rows, inputs, tainted, returned)
    w_number(result, rows, tainted)
    w_marking(result, rows, tainted)
    w_mirror(result, rows, inputs)
    return result


def analyze_source(source: str) -> list[Analysis]:
    tree = ast.parse(source)
    return [analyse_v2(f) for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
