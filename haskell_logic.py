"""v0.2 Haskell front end (doc 04 section 16): AP13's Haskell lowerer (polyglot_logic/tools/lower_equations.py,
unchanged) subclassed for the constructs it drops, so that the same program component gives the same facts as
in the other languages. Only additions; what AP13 lowers stays as it is.

  definitions inside a parse ERROR (tree-sitter keeps the valid subtree): lowered
  an indented module: dedented before parsing (else the equations fold into the type signature)
  f = memoize g where g ...: the where functions are lowered, f an alias of g (a call of f in g is a self-call)
  q `f` qs = ...: an infix definition, name f, parameters q and qs
  (name, w, v) in a head or a where bind: each variable is its element of the tuple
  [v | i <- is, j <- js]: nested maps; (a, b) <- xs `zip` ys: the elements of xs and ys in lockstep
  x ! (i, k): elem(elem(x, i), k);  f a $ b: f a b;  if c then a else b: two results under c / not c
  let binds in e: the binds as a where, then e;  (x ==): x = _ (an operator section);  \a b -> e: e
  (-) as a value: fn(sub);  a top-level f = e (point-free): a function of no parameters returning e
  a recursion ends at its base cases: their guards give the loop condition, as AP13 derives in the other languages
  (a, b): tuple([a, b]), as AP13's Python lowerer writes a tuple;  fromIntegral x: x (a numeric conversion)
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import compare_learners

compare_learners._ap13()
import lower_equations as ap13  # AP13 tools on the path
from fact_io import SELF, FactSet, call, elem, has_call, num, op, other, var
from lower_equations import kids, line, text
from parse_source import parser_for

# library wrappers whose value is the function they wrap (Data.MemoCombinators, Data.Function.Memoize)
MEMO_WRAPPERS = {'memoize', 'memo', 'memo2', 'memo3', 'memoFix', 'memoise', 'memoize2'}
# numeric conversions: the value is kept (as a C cast is)
CONVERSIONS = {'fromIntegral', 'toInteger', 'fromInteger', 'realToFrac'}


def definition_name(d):
    """The name of a function definition: its name field, or the operator of an infix definition (q `f` qs)."""
    name = d.child_by_field_name('name')
    if name is not None:
        return text(name)
    inf = next((c for c in kids(d) if c.type == 'infix'), None)
    if inf is not None:
        o = inf.child_by_field_name('operator')
        return text(kids(o)[0]) if o is not None and o.type == 'infix_id' and kids(o) else text(o)
    return ''


def infix_params(d):
    """The two operand variables of an infix definition, or None."""
    inf = next((c for c in kids(d) if c.type == 'infix'), None)
    if d.child_by_field_name('name') is not None or inf is None:
        return None
    sides = [inf.child_by_field_name('left_operand'), inf.child_by_field_name('right_operand')]
    return [text(s) if s is not None and s.type == 'variable' else f'$arg{k}' for k, s in enumerate(sides)]


def tuple_items(p):
    """The items of a tuple pattern (through parentheses), or None."""
    while p is not None and p.type == 'parens':
        p = p.child_by_field_name('pattern') or (kids(p)[0] if kids(p) else None)
    if p is not None and p.type == 'tuple':
        return kids(p)
    return None


class HaskellLowerer(ap13.Lowerer):
    def __init__(self, facts: FactSet):
        super().__init__(facts)
        self.aliases = {}

    # ----- declarations: also inside parse errors; binds with where functions -----------------------
    def declarations(self, node):
        found, stack = [], [node]
        while stack:
            n = stack.pop()
            for c in kids(n):
                if c.type in ('declarations', 'ERROR'):
                    stack.append(c)
                elif n.type in ('declarations', 'ERROR') and c.type in ('function', 'bind'):
                    found.append(c)
        return sorted(found, key=lambda d: d.start_byte)

    def scope(self, decls, captured=()):
        for d in decls:                           # f = memoize g where g ...: f stands for g
            if d.type == 'bind' and d.child_by_field_name('name') is not None:
                wrapped = self.wrapped_function(d)
                if wrapped:
                    self.aliases[text(d.child_by_field_name('name'))] = wrapped
        groups = {}
        for d in decls:
            if d.type == 'function':
                groups.setdefault(definition_name(d), []).append(d)
        for name, equations in groups.items():
            self.function(name, equations, captured)
        for d in decls:                           # the functions of a bind's where block
            local = d.child_by_field_name('binds') if d.type == 'bind' else None
            if local is not None:
                self.scope([c for c in kids(local) if c.type in ('function', 'bind')], captured)
        if not captured:                          # a top-level f = e (point-free): a function of no parameters
            for d in decls:
                if d.type == 'bind' and d.child_by_field_name('name') is not None and \
                        d.child_by_field_name('binds') is None and not self.wrapped_function(d):
                    self.point_free(d)

    def point_free(self, d):
        m = d.child_by_field_name('match')
        e = m.child_by_field_name('expression') if m is not None else None
        if e is None:
            return
        f = self.facts.new_func(text(d.child_by_field_name('name')), line(d))
        self.name, self.params, self.loop_id = text(d.child_by_field_name('name')), [], None
        s = self.facts.new_stmt(ap13.Ctx(f), 'ret', line(d))
        value = self.expr(e, {})
        self.facts.add('ret', s, value)
        self.calls(value, s)

    def wrapped_function(self, d):
        """g when the bind is f = g or f = memoize g (a memo wrapper is the function it wraps)."""
        m = d.child_by_field_name('match')
        e = m.child_by_field_name('expression') if m is not None else None
        if e is None:
            return None
        if e.type == 'variable':
            return text(e)
        if e.type == 'apply' and text(e.child_by_field_name('function')) in MEMO_WRAPPERS:
            arg = e.child_by_field_name('argument')
            return text(arg) if arg is not None and arg.type == 'variable' else None
        return None

    # ----- one function: AP13's, with infix definitions, tuple patterns and conditional results --------
    def function(self, name, equations, captured=()):
        infix = infix_params(equations[0])
        if infix is None:
            return super().function(name, equations, captured)
        f = self.facts.new_func(name, line(equations[0]))
        for k, p in enumerate(infix):
            self.facts.add('param', f, k, p)
        for k, p in enumerate(c for c in captured if c not in infix):
            self.facts.add('param', f, len(infix) + k, p)
        self.name, self.params, self.loop_id = name, infix, None
        ctx = ap13.Ctx(f)
        env = {p: var(p) for p in infix}
        for e in equations:
            local = e.child_by_field_name('binds')
            if local is not None:
                self.where(local, ctx, env)
            for m in e.children_by_field_name('match'):
                self.result(m.child_by_field_name('expression'), ctx, env, None, m)
        return None

    def calls_self(self, node, name):
        if super().calls_self(node, name):
            return True
        return any(g == name and super(HaskellLowerer, self).calls_self(node, a) for a, g in self.aliases.items())

    def patterns(self, equation, params):
        env, guards, uses_cursor, list_param = super().patterns(equation, params)
        pats = equation.child_by_field_name('patterns')
        for k, p in enumerate(kids(pats) if pats is not None else []):
            pname = params[k]
            items = tuple_items(p)
            if items is not None:                 # (name, w, v): the tuple's elements
                self.bind_tuple(items, var(pname), env)
                continue
            while p.type == 'parens':
                p = p.child_by_field_name('pattern') or kids(p)[0]
            if p.type == 'infix':                 # (name, w, v) : rest: the head's elements
                parts = [t for t in ap13.flatten(p) if not isinstance(t, tuple)]
                for i, item in enumerate(parts[:-1]):
                    sub = tuple_items(item)
                    if sub is not None:
                        self.bind_tuple(sub, elem(var(pname), ap13.at(i)), env)
        return env, guards, uses_cursor, list_param

    def bind_tuple(self, items, whole, env):
        for j, item in enumerate(items):
            sub = tuple_items(item)
            if sub is not None:
                self.bind_tuple(sub, elem(whole, num(j)), env)
            elif item.type == 'variable':
                env[text(item)] = elem(whole, num(j))

    def where(self, local, ctx, env):
        super().where(local, ctx, env)
        for d in kids(local):                     # ((x0, x1), (y0, y1)) = e: each variable its element of e
            if d.type == 'bind' and d.child_by_field_name('name') is None:
                items = tuple_items(kids(d)[0]) if kids(d) else None
                m = d.child_by_field_name('match')
                if items is None or m is None:
                    continue
                value = self.expr(m.child_by_field_name('expression'), env)
                named = {}
                self.bind_tuple(items, value, named)
                for v, t in named.items():
                    s = self.facts.new_stmt(ctx, 'assign', line(d))
                    self.facts.add('assign', s, var(v), t)
                    self.calls(t, s)

    def result(self, body, ctx, env, list_param, node, base_guard=None):
        if body is not None and body.type == 'let_in':        # let binds in e: the binds as a where, then e
            binds = body.child_by_field_name('binds')
            if binds is not None:
                self.where(binds, ctx, env)
            return self.result(body.child_by_field_name('expression'), ctx, env, list_param, node, base_guard)
        if body is not None and body.type == 'conditional':   # if c then a else b
            c, a, b = (kids(body) + [None, None, None])[:3]
            g = self.expr(c, env)
            self.result(a, ctx.guard(g, 'true'), env, list_param, node)
            self.result(b, ctx.guard(g, 'false'), env, list_param, node)
            return None
        return super().result(body, ctx, env, list_param, node, base_guard)

    # ----- expressions ---------------------------------------------------------------------------------
    def expr(self, node, env):
        if node is not None and node.type == 'lambda':           # \a b -> e: e, with a and b as themselves
            pats = node.child_by_field_name('patterns')
            names = [text(q) for q in kids(pats)] if pats is not None else []
            return self.expr(node.child_by_field_name('expression'), dict(env, **{n: var(n) for n in names}))
        if node is not None and node.type == 'tuple':            # (a, b): tuple([a, b]), as AP13's Python lowerer
            return ('tuple', [self.expr(c, env) for c in kids(node)])
        if node is not None and node.type == 'prefix_id':        # (-) as a value: the function object
            o = text(node).strip('()` ')
            return ('fn', ap13.LANG_OPERATORS['haskell'].get(o) or ap13.OPERATORS.get(o, o))
        if node is not None and node.type in ('left_section', 'right_section'):   # (x ==), (== x)
            parts = kids(node)
            o = text(parts[-1] if node.type == 'left_section' else parts[0])
            name = ap13.LANG_OPERATORS['haskell'].get(o) or ap13.OPERATORS.get(o, o)
            side = self.expr(parts[0] if node.type == 'left_section' else parts[-1], env)
            hole = var('$hole')
            return op(name, side, hole) if node.type == 'left_section' else op(name, hole, side)
        t = super().expr(node, env)
        if isinstance(t, tuple) and t[:1] == ('call',) and t[1] in CONVERSIONS and len(t[2]) == 1:
            return t[2][0]                            # fromIntegral x: x (a numeric conversion keeps the value)
        if isinstance(t, tuple) and t[:1] == ('call',) and t[1] in self.aliases:
            return call(self.aliases[t[1]], t[2])  # a call of the memo wrapper is a call of the function
        return t

    def binary(self, tree, env):
        if isinstance(tree, tuple) and tree[0] == 'bin':
            _, o, left, right = tree
            if o == '$':                          # f a $ b == f a b
                f, b = self.binary(left, env), self.binary(right, env)
                if f[0] == 'call':
                    return call(f[1], f[2] + [b])
                if f[0] == 'var':
                    return call(self.aliases.get(f[1], f[1]), [b])
                return op('$', f, b)
            if o in ap13.HASKELL_INDEX and not isinstance(right, tuple):
                items = tuple_items(right) if right.type != 'tuple' else kids(right)
                if items:                         # x ! (i, k): row i, column k
                    t = self.binary(left, env)
                    for item in items:
                        t = elem(t, self.expr(item, env))
                    return t
        return super().binary(tree, env)

    def comprehension(self, node, env):
        """Several generators: nested maps, the first the outer loop. A generator (a, b) <- xs `zip` ys binds
        the elements of xs and ys in lockstep; otherwise AP13's single generator."""
        quals = node.child_by_field_name('qualifiers')
        gens = [q for q in kids(quals) if q.type == 'generator'] if quals else []
        simple = len(gens) == 1 and gens[0].child_by_field_name('pattern').type == 'variable'
        if simple or not gens:
            return super().comprehension(node, env)
        conds = [q for q in kids(quals) if q.type == 'boolean']
        inner, seqs = dict(env), []
        for k, g in enumerate(gens):
            loop_el = var('$e' if k == 0 else f'$e{k}')
            pat, src = g.child_by_field_name('pattern'), g.child_by_field_name('expression')
            items = tuple_items(pat)
            zipped = self.zip_sources(src, inner) if items is not None else None
            if items is not None and zipped is not None and len(zipped) == len(items):
                seq = zipped[0]
                for item, s in zip(items, zipped):
                    if item.type == 'variable':
                        inner[text(item)] = ('elem', s, loop_el)
            else:
                seq = self.expr(src, inner)
                if pat.type == 'variable':
                    inner[text(pat)] = ('elem', seq, loop_el)
                elif items is not None:
                    self.bind_tuple(items, ('elem', seq, loop_el), inner)
                else:
                    return other('nested_comprehension')
            seqs.append(seq)
        cond = self.expr(kids(conds[0])[0], inner) if conds else ('bool', 'true')
        value = self.expr(node.child_by_field_name('expression'), inner)
        term = ('map', seqs[-1], value, cond)
        for seq in reversed(seqs[:-1]):
            term = ('map', seq, term, ('bool', 'true'))
        return term

    def zip_sources(self, src, env):
        """[xs, ys] of xs `zip` ys or zip xs ys, else None."""
        if src.type == 'infix':
            o = src.child_by_field_name('operator')
            name = text(kids(o)[0]) if o is not None and o.type == 'infix_id' and kids(o) else text(o)
            if name == 'zip':
                return [self.expr(src.child_by_field_name('left_operand'), env),
                        self.expr(src.child_by_field_name('right_operand'), env)]
        if src.type == 'apply':
            args, head = [], src
            while head.type == 'apply':
                args.insert(0, head.child_by_field_name('argument'))
                head = head.child_by_field_name('function')
            if text(head) == 'zip' and len(args) == 2:
                return [self.expr(a, env) for a in args]
        return None


def lower(path: Path) -> str:
    """The base facts of a Haskell file (the source dedented, parsed by tree-sitter, lowered)."""
    source = textwrap.dedent(path.read_text(encoding='utf-8', errors='replace')).encode('utf-8')
    tree = parser_for('haskell').parse(source)    # the tree stays referenced while its nodes are read
    facts = HaskellLowerer(FactSet('haskell')).run(tree.root_node)
    del tree
    base_case_conditions(facts)
    return facts.text()


def base_case_conditions(facts):
    """The recursion ends at its base cases, as AP13's shared post-pass derives for the other languages
    (fact_io.FactSet.finish): the guard of a return without a self-call gives the loop condition not(guard). AP13's
    equational lowerer derives it only from a | guard of variables, so go acc 0 = acc (the guard n == 0 of a pattern)
    gave a recursion with no condition; here every base case of a recursion loop gives it, as in Python."""
    loops = {a[1]: a[0] for a in facts.facts['loop'] if a[2] == 'recursion'}
    stmt_func = {a[0]: a[1] for a in facts.facts['stmt']}
    have = {(a[0], repr(a[1])) for a in facts.facts['loop_cond']}
    # the statements making a self-call: a guard they carry too is the context (an enclosing equation's pattern,
    # inherited by a where function), not what ends the recursion
    steps = {a[0] for a in facts.facts['call_at'] if a[1] == SELF}
    step_guards = {(stmt_func.get(g_s), repr(cond), pol) for g_s, cond, pol in facts.facts['guard'] if g_s in steps}
    for s, value in list(facts.facts['ret']):
        loop = loops.get(stmt_func.get(s))
        if loop is None or has_call(value, SELF):
            continue
        for g_s, cond, pol in list(facts.facts['guard']):
            c = op('not', cond)
            if g_s == s and pol == 'true' and cond[0] == 'op' and (loop, repr(c)) not in have                     and (stmt_func.get(s), repr(cond), pol) not in step_guards:
                facts.facts['loop_cond'].append((loop, c))
                have.add((loop, repr(c)))
