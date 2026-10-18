"""Bounded, source-only evidence extraction. No candidate source is executed.

This deliberately is NOT a complete Python data-flow analyser. Observations are
conservative, local, syntactic dependency witnesses for Prolog branch routing.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class Analysis:
    name: str
    inputs: list[str]
    evidence: dict[str, list[int]] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)

    def add(self, fact: str, line: int) -> None:
        locations = self.evidence.setdefault(fact, [])
        if line not in locations:
            locations.append(line)


def same(a: ast.AST, b: ast.AST) -> bool:
    return ast.unparse(a) == ast.unparse(b)  # ignore Store/Load context for an address


def subscript_on(expr: ast.AST, names: set[str]) -> str | None:
    if isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name):
        if expr.value.id in names:
            return expr.value.id
    return None


def statements(body, guards=(), loops=()):
    """A bounded lexical walk with control ancestry; skip statically dead ifs."""
    for statement in body:
        if isinstance(statement, (ast.Return, ast.Raise)):
            yield statement, guards, loops
            return  # unconditional termination of this lexical block
        yield statement, guards, loops
        if isinstance(statement, ast.If):
            if isinstance(statement.test, ast.Constant) and statement.test.value is False:
                yield from statements(statement.orelse, guards, loops)
            elif isinstance(statement.test, ast.Constant) and statement.test.value is True:
                yield from statements(statement.body, guards, loops)
            else:
                yield from statements(statement.body, guards + ((statement, True),), loops)
                yield from statements(statement.orelse, guards + ((statement, False),), loops)
        elif isinstance(statement, (ast.For, ast.While)):
            yield from statements(statement.body, guards, loops + (statement,))
            yield from statements(statement.orelse, guards, loops)
        # Complicated control constructs are deliberately not traversed.


def pair_exchange(stmt: ast.AST, inputs: set[str]):
    """Recognize an actual simultaneous two-element exchange, not two writes."""
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], (ast.Tuple, ast.List))
            and isinstance(stmt.value, (ast.Tuple, ast.List))):
        return None
    lhs, rhs = stmt.targets[0].elts, stmt.value.elts
    if len(lhs) != 2 or len(rhs) != 2:
        return None
    name = subscript_on(lhs[0], inputs)
    if not name or subscript_on(lhs[1], inputs) != name:
        return None
    if same(lhs[0], lhs[1]):
        return None
    if same(lhs[0], rhs[1]) and same(lhs[1], rhs[0]):
        return name, lhs
    return None


def compare_controls_exchange(guards, name, positions):
    for if_stmt, polarity in guards:
        if not polarity:  # No attempt at inverse-condition reasoning in v0.1
            continue
        cmp = if_stmt.test
        if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                and isinstance(cmp.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE))
                and len(cmp.comparators) == 1):
            continue
        left, right = cmp.left, cmp.comparators[0]
        if (subscript_on(left, {name}) == name and
                subscript_on(right, {name}) == name and
                ((same(left, positions[0]) and same(right, positions[1])) or
                 (same(left, positions[1]) and same(right, positions[0])))):
            return if_stmt.lineno
    return None


def equality_controls_index_return(stmt, guards, loops, inputs):
    if not (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name)
            and loops):
        return None
    for if_stmt, polarity in guards:
        if not polarity:
            continue
        cmp = if_stmt.test
        if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                and isinstance(cmp.ops[0], ast.Eq) and len(cmp.comparators) == 1):
            continue
        l, r = cmp.left, cmp.comparators[0]
        for arr_expr, target in ((l, r), (r, l)):
            name = subscript_on(arr_expr, inputs)
            if (name and isinstance(target, ast.Name) and target.id in inputs
                    and target.id != name and isinstance(arr_expr.slice, ast.Name)
                    and arr_expr.slice.id == stmt.value.id):
                return name, arr_expr.slice.id, if_stmt.lineno
    return None


def midpoint(expr, left, right):
    def nm(expr, value):
        return isinstance(expr, ast.Name) and expr.id == value

    def div2(expr):
        return (isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.FloorDiv)
                and isinstance(expr.right, ast.Constant)
                and type(expr.right.value) is int and expr.right.value == 2)

    if div2(expr) and isinstance(expr.left, ast.BinOp) and isinstance(expr.left.op, ast.Add):
        if nm(expr.left.left, left) and nm(expr.left.right, right):
            return True
        if nm(expr.left.left, right) and nm(expr.left.right, left):
            return True
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add) and nm(expr.left, left):
        d = expr.right
        return (div2(d) and isinstance(d.left, ast.BinOp)
                and isinstance(d.left.op, ast.Sub)
                and nm(d.left.left, right) and nm(d.left.right, left))
    return False


def bound_update(expr, center, plus):
    return (isinstance(expr, ast.BinOp)
            and isinstance(expr.op, ast.Add if plus else ast.Sub)
            and isinstance(expr.left, ast.Name) and expr.left.id == center
            and isinstance(expr.right, ast.Constant)
            and type(expr.right.value) is int and expr.right.value == 1)


def coherent_interval_search(rows, witness):
    name, center, _, loop = witness
    if not (isinstance(loop, ast.While) and isinstance(loop.test, ast.Compare)
            and isinstance(loop.test.left, ast.Name)
            and len(loop.test.ops) == 1 and isinstance(loop.test.ops[0], ast.LtE)
            and len(loop.test.comparators) == 1
            and isinstance(loop.test.comparators[0], ast.Name)):
        return False
    left, right = loop.test.left.id, loop.test.comparators[0].id
    centers, grows, shrinks = [], [], []
    for stmt, guards, loops in rows:
        if loop not in loops or not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        dst = stmt.targets[0]
        if not isinstance(dst, ast.Name):
            continue
        if dst.id == center and midpoint(stmt.value, left, right):
            centers.append(stmt.lineno)
        if guards and dst.id == left and bound_update(stmt.value, center, plus=True):
            grows.append(stmt.lineno)
        if guards and dst.id == right and bound_update(stmt.value, center, plus=False):
            shrinks.append(stmt.lineno)
    return (centers[0], grows[0], shrinks[0]) if centers and grows and shrinks else False


def used_names(expr: ast.AST):
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def analyse(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> Analysis:
    args = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    if fn.args.vararg:
        args.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        args.append(fn.args.kwarg.arg)
    result = Analysis(fn.name, args)
    inputs = set(args)
    rows = list(statements(fn.body))
    if isinstance(fn, ast.AsyncFunctionDef):
        result.unknowns.append('async function not modeled')

    # A tiny, conservative may-depend-on analysis for output reporting.
    # This does not claim reaching-definitions / alias precision.
    deps = {name: {name} for name in inputs}
    for _ in range(min(16, len(rows) + 1)):
        changed = False
        for stmt, _, _ in rows:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                rhs = getattr(stmt, 'value', None)
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                rhs, targets = stmt.iter, [stmt.target]
            else:
                continue
            if rhs is None:
                continue
            origins = set().union(*(deps.get(n, set()) for n in used_names(rhs)))
            for target in targets:
                for node in ast.walk(target):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        existing = deps.setdefault(node.id, set())
                        new = origins - existing
                        if new:
                            existing.update(new)
                            changed = True
        if not changed:
            break
    result.dependencies = {k: sorted(v) for k, v in sorted(deps.items()) if v}

    search_witnesses = []
    for stmt, guards, loops in rows:
        if isinstance(stmt, (ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.Match,
                             ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.unknowns.append('unsupported nested/control construct at line ' + str(stmt.lineno))
        if isinstance(stmt, ast.Return):
            if isinstance(stmt.value, ast.Name):
                result.outputs.append('return ' + stmt.value.id + ' (may depend on: ' +
                                      ', '.join(sorted(deps.get(stmt.value.id, set()))) + ')')
                if stmt.value.id in inputs:
                    result.add('returned_input', stmt.lineno)
            elif stmt.value is not None:
                result.outputs.append('return expression (may depend on: ' +
                                      ', '.join(sorted(set().union(*(deps.get(n, set())
                                                for n in used_names(stmt.value))))) + ')')
            else:
                result.outputs.append('return None')
            hit = equality_controls_index_return(stmt, guards, loops, inputs)
            if hit:
                name, center, cond_line = hit
                result.add('indexed_equality_controls_index_return', cond_line)
                result.add('indexed_equality_controls_index_return', stmt.lineno)
                for loop in loops:
                    search_witnesses.append((name, center, cond_line, loop))
        swap = pair_exchange(stmt, inputs)
        if swap:
            name, positions = swap
            result.add('input_sequence_mutated', stmt.lineno)
            result.add('element_exchange', stmt.lineno)
            line = compare_controls_exchange(guards, name, positions)
            if line is not None:
                result.add('comparison_controls_exchange', line)
                result.add('comparison_controls_exchange', stmt.lineno)
        # Unknown helper calls are not interpreted as known transformations.
        if isinstance(stmt, (ast.Assign, ast.Expr, ast.Return)):
            for node in ast.walk(stmt):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec'):
                        result.unknowns.append('dynamic execution call at line ' + str(node.lineno))
    for witness in search_witnesses:
        found = coherent_interval_search(rows, witness)
        if found:
            for line in found:
                result.add('coherent_midpoint_interval_update', line)
            break
    result.unknowns = list(dict.fromkeys(result.unknowns))
    return result


def analyze_source(source: str) -> list[Analysis]:
    tree = ast.parse(source)
    return [analyse(f) for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
