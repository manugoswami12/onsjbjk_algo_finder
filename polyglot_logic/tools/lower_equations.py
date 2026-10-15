"""AP13 transform: Haskell equations -> base facts (same vocabulary).

Recursion is a loop; guards are guard/3; recursive-call arguments are parameter
updates; list patterns x:y:rest address positions $cursor, $cursor+1 (doc 01 §7).
"""
from __future__ import annotations

from fact_io import Ctx, FactSet, call, elem, num, op, other, var
from lang_tables import FOLDS, HASKELL_FIXITY, HASKELL_INDEX, LENGTH_CALLS, OPERATORS, SYNONYMS, WRAPPERS

CURSOR = var('$cursor')


def text(n):
    return n.text.decode('utf-8', 'replace') if n is not None else ''


def line(n):
    return n.start_point[0] + 1


def kids(n):
    return [c for c in n.named_children if c.type != 'comment']


def at(k):
    return CURSOR if k == 0 else op('add', CURSOR, num(k))


def flatten(node):
    """tree-sitter-haskell leaves infix chains unresolved: collect operands/operators."""
    if node.type == 'infix':
        o = node.child_by_field_name('operator')
        name = text(kids(o)[0]) if o.type == 'infix_id' else text(o)
        return flatten(node.child_by_field_name('left_operand')) + [('OP', name)] + \
            flatten(node.child_by_field_name('right_operand'))
    return [node]


def shunting_yard(tokens):
    """Dijkstra's algorithm with Haskell Report fixities -> nested ('bin', op, l, r)."""
    out, ops = [], []

    def reduce():
        o = ops.pop()
        r, l = out.pop(), out.pop()
        out.append(('bin', o, l, r))

    for tok in tokens:
        if isinstance(tok, tuple) and tok[0] == 'OP':
            assoc, prec = HASKELL_FIXITY.get(tok[1], ('l', 9))
            while ops:
                top_assoc, top_prec = HASKELL_FIXITY.get(ops[-1], ('l', 9))
                if top_prec > prec or (top_prec == prec and assoc == 'l'):
                    reduce()
                else:
                    break
            ops.append(tok[1])
        else:
            out.append(tok)
    while ops:
        reduce()
    return out[0]


class Lowerer:
    def __init__(self, facts: FactSet):
        self.facts = facts

    def run(self, root):
        self.scope(self.declarations(root))
        return self.facts.finish()

    def declarations(self, node):
        found = []
        for c in kids(node):
            if c.type == 'declarations':
                found += kids(c)
        return found

    def scope(self, decls, captured=()):
        groups = {}
        for d in decls:
            if d.type == 'function':
                groups.setdefault(text(d.child_by_field_name('name')), []).append(d)
        for name, equations in groups.items():
            self.function(name, equations, captured)

    # ----- one function = all its equations ----------------------------------
    def function(self, name, equations, captured=()):
        f = self.facts.new_func(name, line(equations[0]))
        arity = max(len(kids(e.child_by_field_name('patterns'))) for e in equations
                    if e.child_by_field_name('patterns') is not None) if any(
            e.child_by_field_name('patterns') is not None for e in equations) else 0
        params = [f'$arg{k}' for k in range(arity)]
        for e in equations:
            pats = e.child_by_field_name('patterns')
            for k, p in enumerate(kids(pats) if pats is not None else []):
                if p.type == 'variable' and params[k].startswith('$'):
                    params[k] = text(p)
        for k, p in enumerate(params):
            self.facts.add('param', f, k, p)
        # A local (where) function sees the enclosing parameters it captures.
        for k, p in enumerate(c for c in captured if c not in params):
            self.facts.add('param', f, len(params) + k, p)
        self.name, self.params = name, params
        recursive = any(self.calls_self(e, name) for e in equations)
        ctx = Ctx(f)
        loop_id = None
        if recursive:
            loop_id = self.facts.new_loop(ctx, 'recursion', line(equations[0]))
            ctx = ctx.loop(loop_id)
        self.loop_id = loop_id
        pending = []  # negated guards of earlier refutable equations
        for e in equations:
            env, pat_guards, uses_cursor, list_param = self.patterns(e, params)
            if uses_cursor and loop_id:
                self.facts.add('loop_var', loop_id, '$cursor')
            ectx = ctx
            for g, pol in pending:
                ectx = ectx.guard(g, pol)
            for g in pat_guards:
                ectx = ectx.guard(g, 'true')
            local = e.child_by_field_name('binds')
            if local is not None:
                self.where(local, ectx, env)
            alt_ctx = ectx
            for m in e.children_by_field_name('match'):
                guards = m.child_by_field_name('guards')
                body = m.child_by_field_name('expression')
                if guards is not None:
                    g = self.expr(kids(kids(guards)[0])[0] if kids(kids(guards)[0]) else kids(guards)[0], env)
                    if g == ('bool', 'true'):
                        self.result(body, alt_ctx, env, list_param, m)
                    else:
                        self.result(body, alt_ctx.guard(g, 'true'), env, list_param, m, base_guard=g)
                        alt_ctx = alt_ctx.guard(g, 'false')
                else:
                    self.result(body, alt_ctx, env, list_param, m)
            for g in pat_guards:  # later equations only run when this pattern failed
                pending.append((g, 'false'))
            if local is not None:
                self.scope([d for d in kids(local) if d.type == 'function'],
                           tuple(captured) + tuple(params))
                self.name, self.params, self.loop_id = name, params, loop_id

    def calls_self(self, node, name):
        stack = [node.child_by_field_name(x) for x in ('match',)] + node.children_by_field_name('match')
        stack = [s for s in stack if s is not None]
        while stack:
            n = stack.pop()
            if n.type == 'apply':
                head = n
                while head.type == 'apply':
                    head = head.child_by_field_name('function')
                if head.type == 'variable' and text(head) == name:
                    return True
            stack.extend(kids(n))
        return False

    def patterns(self, equation, params):
        env, guards, uses_cursor, list_param = {}, [], False, None
        pats = equation.child_by_field_name('patterns')
        for k, p in enumerate(kids(pats) if pats is not None else []):
            while p.type == 'parens':
                p = p.child_by_field_name('pattern') or kids(p)[0]
            pname = params[k]
            if p.type == 'variable':
                env[text(p)] = var(pname)
            elif p.type == 'literal':
                guards.append(op('eq', var(pname), self.expr(p, env)))
            elif p.type == 'infix':  # x:y:rest
                parts = [t for t in flatten(p) if not isinstance(t, tuple)]
                for i, item in enumerate(parts[:-1]):
                    if item.type == 'variable':
                        env[text(item)] = elem(var(pname), at(i))
                tail = parts[-1]
                if tail.type == 'variable':
                    env[text(tail)] = ('tail', pname, len(parts) - 1)
                uses_cursor, list_param = True, pname
            elif p.type == 'list' and not kids(p):
                guards.append(op('eq', call('len', [var(pname)]), num(0)))
        return env, guards, uses_cursor, list_param

    def where(self, local, ctx, env):
        for d in kids(local):
            if d.type == 'bind' and d.child_by_field_name('name') is not None:
                m = d.child_by_field_name('match')
                value = self.expr(m.child_by_field_name('expression'), env)
                s = self.facts.new_stmt(ctx, 'assign', line(d))
                self.facts.add('assign', s, var(text(d.child_by_field_name('name'))), value)
                self.calls(value, s)

    # ----- the right-hand side of one alternative -------------------------------
    def result(self, body, ctx, env, list_param, node, base_guard=None):
        e = self.expr(body, env)
        if e[0] == 'fold':
            e = self.fold(e, ctx, node)
        writes, k = [], 0
        while e[0] == 'cons':  # emitted elements: y : rest
            if list_param:
                writes.append((elem(var(list_param), at(k)), e[1]))
            k += 1
            e = e[2]
        stmts = []
        if e[0] == 'call' and e[1] == self.name:
            # one recursive step = ONE statement: the call, its parameter updates, the result
            s = self.facts.new_stmt(ctx, 'ret', line(node))
            self.facts.add('call_at', s, e[1], [x for x in e[2]])
            for i, a in enumerate(e[2][:len(self.params)]):
                p = self.params[i]
                if a[0] == 'cons' and list_param:  # recursion continues with x : rest
                    j = k  # after k emitted heads the recursive list starts at cursor + k
                    while a[0] == 'cons':
                        writes.append((elem(var(list_param), at(j)), a[1]))
                        j += 1
                        a = a[2]
                elif a != var(p) and not (a[0] == 'tail'):
                    self.facts.add('assign', s, var(p), a)
                    self.calls(a, s)
            if not writes and k == 0:  # a tail self-call IS the result (as `return f(...)`)
                self.facts.add('ret', s, e)
            stmts.append(s)
        else:
            s = self.facts.new_stmt(ctx, 'ret', line(node))
            self.facts.add('ret', s, e if e[0] != 'tail' else var(e[1]))
            self.calls(e, s)
            stmts.append(s)
            if base_guard is not None and self.loop_id and base_guard[0] == 'op' \
                    and all(x[0] == 'var' for x in base_guard[2]):
                self.facts.add('loop_cond', self.loop_id, op('not', base_guard))
        writes = [(t, v) for t, v in writes if t != v]  # identity writes are not effects
        if writes:
            s = self.facts.new_stmt(ctx, 'assign', line(node))
            self.facts.add('par_assign', s, [t for t, _ in writes], [v for _, v in writes])

    def fold(self, f, ctx, node):
        """acc = z; for each element e of xs: acc = f(acc, e); result acc."""
        _, kind, seq, z, fn, env = f
        acc, el = var('$acc'), var('$e')
        s0 = self.facts.new_stmt(ctx, 'assign', line(node))
        self.facts.add('assign', s0, acc, z)
        loop_id = self.facts.new_loop(ctx, 'count', line(node))
        self.facts.add('loop_var', loop_id, '$e')
        self.facts.add('loop_iter', loop_id, seq)
        args = [el, acc] if kind == 'foldr' else [acc, el]
        s1 = self.facts.new_stmt(ctx.loop(loop_id), 'assign', line(node))
        self.facts.add('assign', s1, acc, self.apply_fn(fn, args, env))
        return acc

    def calls(self, t, s):
        stack = [t]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, tuple):
                if x[0] == 'call':
                    self.facts.add('call_at', s, x[1], x[2])
                stack.extend(a for a in x[1:] if isinstance(a, (list, tuple)))

    # ----- expressions -----------------------------------------------------
    def expr(self, node, env):
        if node is None:
            return other('none')
        t = node.type
        if t == 'variable':
            name = text(node)
            if name == 'otherwise':
                return ('bool', 'true')
            return env.get(name, var(name))
        if t == 'literal':
            inner = kids(node)[0] if kids(node) else node
            try:
                return num(int(text(inner)))
            except ValueError:
                return other('literal')
        if t == 'integer':
            return num(int(text(node)))
        if t == 'negation':
            inner = self.expr(node.child_by_field_name('expression') or kids(node)[0], env)
            return num(-inner[1]) if inner[0] == 'int' else op('neg', inner)
        if t == 'parens':
            return self.expr(node.child_by_field_name('expression') or kids(node)[0], env)
        if t == 'list_comprehension':
            return self.comprehension(node, env)
        if t == 'list':
            return ('list', [self.expr(e, env) for e in kids(node)])
        if t == 'apply':
            arg_nodes, head = [], node
            while head.type == 'apply':
                arg_nodes.insert(0, head.child_by_field_name('argument'))
                head = head.child_by_field_name('function')
            name = text(head)
            if name in ('filter', 'map') and len(arg_nodes) == 2:   # filter p xs / map f xs
                seq = self.expr(arg_nodes[1], env)
                body = self.apply_fn(arg_nodes[0], [('elem', seq, var('$e'))], env)
                return ('filter', seq, body) if name == 'filter' else ('map', seq, body, ('bool', 'true'))
            if name in FOLDS and len(arg_nodes) == 3:               # foldl f z xs (G5)
                return ('fold', name, self.expr(arg_nodes[2], env), self.expr(arg_nodes[1], env),
                        arg_nodes[0], env)
            args = [self.expr(a, env) for a in arg_nodes]
            if name in LENGTH_CALLS:
                return call('len', args[:1])
            if name in WRAPPERS and len(args) == 1:
                return args[0]
            return call(SYNONYMS.get(name, name), args)
        if t == 'infix':
            return self.binary(shunting_yard(flatten(node)), env)
        if t == 'constructor' and text(node) in ('True', 'False'):
            return ('bool', text(node).lower())
        return other(t)

    def comprehension(self, node, env):
        """[v | x <- xs, c]  ->  filter(xs, c) or map(xs, v, c), x = elem(xs, $e) (G4)."""
        quals = node.child_by_field_name('qualifiers')
        gens = [q for q in kids(quals) if q.type == 'generator'] if quals else []
        conds = [q for q in kids(quals) if q.type == 'boolean'] if quals else []
        if len(gens) != 1 or gens[0].child_by_field_name('pattern').type != 'variable':
            return other('nested_comprehension')
        x = text(gens[0].child_by_field_name('pattern'))
        seq = self.expr(gens[0].child_by_field_name('expression'), env)
        inner = dict(env, **{x: ('elem', seq, var('$e'))})
        cond = self.expr(kids(conds[0])[0], inner) if conds else ('bool', 'true')
        value = self.expr(node.child_by_field_name('expression'), inner)
        if value == ('elem', seq, var('$e')):
            return ('filter', seq, cond)
        return ('map', seq, value, cond)

    def apply_fn(self, fn, args, env):
        """Apply a lambda, an operator section or a named function to argument terms."""
        while fn.type == 'parens':
            fn = fn.child_by_field_name('expression') or kids(fn)[0]
        if fn.type == 'lambda':
            pats = [text(p) for p in kids(fn.child_by_field_name('patterns'))]
            return self.expr(fn.child_by_field_name('expression'), dict(env, **dict(zip(pats, args))))
        if fn.type in ('right_section', 'left_section'):
            parts = kids(fn)
            o = text(parts[0] if fn.type == 'right_section' else parts[-1])
            other_side = self.expr(parts[-1] if fn.type == 'right_section' else parts[0], env)
            name = OPERATORS.get(o, o)
            if fn.type == 'right_section':        # (>= x) e  ==  e >= x
                return op(name, args[0], other_side)
            return op(name, other_side, args[0])  # (x <) e   ==  x < e
        return call(SYNONYMS.get(text(fn), text(fn)), args)

    def binary(self, tree, env):
        if not (isinstance(tree, tuple) and tree[0] == 'bin'):
            return self.expr(tree, env)
        _, o, l, r = tree
        a, b = self.binary(l, env), self.binary(r, env)
        if o == ':':
            return ('cons', a, b)
        if o == '++':  # list concatenation, flattened
            return ('concat', (a[1] if a[0] == 'concat' else [a]) + (b[1] if b[0] == 'concat' else [b]))
        if o in HASKELL_INDEX:
            return elem(a, b)
        name = OPERATORS.get(o, o)
        if name == 'add' and a[0] == 'int' and b[0] != 'int':
            a, b = b, a
        return op(name, a, b)


def lower(root) -> FactSet:
    return Lowerer(FactSet('haskell')).run(root)
