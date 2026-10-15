"""AP13 transform: imperative syntax (Python, Rust, Java, C, R) -> base facts.

One table-driven walker (lang_tables.SPEC); no per-language algorithm rules.
"""
from __future__ import annotations

from fact_io import Ctx, FactSet, call, elem, num, op, other, var
from lang_tables import (AUGMENTED, IMPLICIT_RETURN, INT_SLASH, LENGTH_CALLS, OPERATORS,
                         R_ASSIGN, R_ASSIGN_RIGHT, SPEC, WRAPPERS)

FALSE = ('bool', 'false')


def named(node):
    return [c for c in node.named_children if c.type not in ('comment', 'line_comment', 'block_comment')]


def text(node):
    return node.text.decode('utf-8', 'replace') if node is not None else ''


def line(node):
    return node.start_point[0] + 1


class Lowerer:
    def __init__(self, lang, facts: FactSet):
        self.lang, self.facts, self.spec = lang, facts, SPEC[lang]

    # ----- table access -------------------------------------------------
    def kind(self, node):
        if node is None:
            return None, {}
        if self.lang == 'r' and node.type == 'binary_operator':
            o = text(node.child_by_field_name('operator'))
            if o in R_ASSIGN or o in R_ASSIGN_RIGHT:
                return 'r_assign', {}
        return self.spec.get(node.type, (None, {}))

    def role(self, node, roles, name, many=False):
        key = roles.get(name)
        if key is None:
            return [] if many else None
        if key.startswith('#'):
            kids = named(node)
            i = int(key[1:])
            return kids[i] if i < len(kids) else None
        if many:
            return node.children_by_field_name(key)
        return node.child_by_field_name(key)

    # ----- functions ------------------------------------------------------
    def run(self, root):
        self.scan(root, prefix='')
        return self.facts

    def scan(self, node, prefix):
        kind, roles = self.kind(node)
        if kind == 'function':
            self.function(node, roles, prefix)
            return
        if kind == 'class':
            name = text(self.role(node, roles, 'name'))
            prefix = f'{prefix}{name}.'
        if kind == 'r_assign' and node.child_by_field_name('rhs') is not None \
                and node.child_by_field_name('rhs').type == 'function_definition':
            fn = node.child_by_field_name('rhs')
            self.function(fn, self.spec['function_definition'][1], prefix,
                          name=text(node.child_by_field_name('lhs')))
            return
        for child in named(node):
            self.scan(child, prefix)

    def function_name(self, node, roles):
        n = self.role(node, roles, 'name')
        if self.lang == 'c':  # declarator: function_declarator(declarator: identifier)
            while n is not None and n.type != 'identifier':
                n = n.child_by_field_name('declarator')
        return text(n)

    def params(self, node, roles):
        p = self.role(node, roles, 'params')
        if self.lang == 'c':
            while p is not None and p.type != 'function_declarator':
                p = p.child_by_field_name('declarator')
            p = p.child_by_field_name('parameters') if p is not None else None
        names = []
        for child in named(p) if p is not None else []:
            ident = child if child.type == 'identifier' else self.first_identifier(child)
            if ident is not None:
                names.append(text(ident))
        return names

    def first_identifier(self, node):
        for key in ('name', 'pattern', 'declarator'):
            sub = node.child_by_field_name(key)
            if sub is not None:
                return sub if sub.type == 'identifier' else self.first_identifier(sub)
        for child in named(node):
            if child.type == 'identifier':
                return child
        return None

    def function(self, node, roles, prefix, name=None):
        name = prefix + (name or self.function_name(node, roles))
        f = self.facts.new_func(name, line(node))
        for k, pname in enumerate(self.params(node, roles)):
            self.facts.add('param', f, k, pname)
        body = self.role(node, roles, 'body')
        self.block(body, Ctx(f), last_returns=self.lang in IMPLICIT_RETURN)

    # ----- statements ------------------------------------------------------
    def block(self, node, ctx, last_returns=False):
        kind, _ = self.kind(node)
        kids = named(node) if kind == 'block' else ([node] if node is not None else [])
        prev = None
        for i, child in enumerate(kids):
            implicit = last_returns and i == len(kids) - 1
            s = self.stmt(child, ctx, implicit)
            if prev and s:
                self.facts.add('next_stmt', prev, s)
            prev = s
            exit_cond = self.early_exit(child)
            if exit_cond is not None:  # control dependence: later code runs only if cond is false
                ctx = ctx.guard(exit_cond, 'false')

    def early_exit(self, node):
        """`if c: return ...` without alternatives -> c, else None (PDG control dependence)."""
        kind, roles = self.kind(node)
        if kind == 'expr_stmt':
            return self.early_exit(self.role(node, roles, 'inner'))
        if kind != 'if' or self.role(node, roles, 'alt', many=True):
            return None
        then = self.role(node, roles, 'then')
        tkind, _ = self.kind(then)
        body = named(then) if tkind == 'block' else [then]
        while body:
            last = body[-1]
            lkind, lroles = self.kind(last)
            if lkind == 'expr_stmt':
                body = [self.role(last, lroles, 'inner')]
                continue
            if lkind == 'return' or (lkind == 'call' and self.lang == 'r'
                                     and text(self.role(last, lroles, 'fn')) == 'return'):
                return self.expr(self.role(node, roles, 'cond'))
            return None
        return None

    def stmt(self, node, ctx, implicit=False):
        kind, roles = self.kind(node)
        if kind == 'expr_stmt':
            inner = self.role(node, roles, 'inner')
            return self.stmt(inner, ctx) if inner is not None else None
        if kind == 'block':
            self.block(node, ctx)
            return None
        if kind in ('function', 'class'):
            return None  # nested definitions are separate functions (scanned elsewhere)
        if kind == 'for_range':
            loop_id = self.facts.new_loop(ctx, 'count', line(node))
            v = self.role(node, roles, 'var')
            if v is not None:
                self.facts.add('loop_var', loop_id, text(v))
            self.calls(self.role(node, roles, 'iter'), loop_id)
            self.block(self.role(node, roles, 'body'), ctx.loop(loop_id))
            return loop_id
        if kind == 'c_for':
            init = self.role(node, roles, 'init')
            if init is not None:
                self.stmt(init, ctx)
            loop_id = self.facts.new_loop(ctx, 'count', line(node))
            upd = self.role(node, roles, 'update')
            name = self.updated_name(upd)
            if name:
                self.facts.add('loop_var', loop_id, name)
            cond = self.role(node, roles, 'cond')
            if cond is not None:
                self.facts.add('loop_cond', loop_id, self.expr(cond))
            self.block(self.role(node, roles, 'body'), ctx.loop(loop_id))
            return loop_id
        if kind in ('while', 'do_while'):
            loop_id = self.facts.new_loop(ctx, 'cond', line(node))
            cond = self.role(node, roles, 'cond')
            if cond is not None:  # do-while and R repeat test at the end / via break
                self.facts.add('loop_cond', loop_id, self.expr(cond))
            self.block(self.role(node, roles, 'body'), ctx.loop(loop_id))
            return loop_id
        if kind == 'if':
            return self.if_chain(node, roles, ctx)
        if kind == 'decl':
            last = None
            for d in self.role(node, roles, 'declarator', many=True):
                last = self.stmt(d, ctx) or last
            return last
        if kind in ('assign', 'aug_assign', 'r_assign', 'update'):
            return self.assignment(node, kind, roles, ctx)
        if kind == 'return':
            return self.ret(self.role(node, roles, 'value'), ctx, node)
        if kind == 'call' and self.lang == 'r' and text(self.role(node, roles, 'fn')) == 'return':
            args = self.args(self.role(node, roles, 'args'))
            return self.ret_term(args[0] if args else num(0), ctx, node)
        if implicit and kind in ('ident', 'int', 'binary', 'unary', 'call', 'index', 'paren', 'method', 'field'):
            return self.ret(node, ctx, node)
        if kind is None and node is not None and node.type in ('pass_statement', 'empty_statement', ';'):
            return None
        s = self.facts.new_stmt(ctx, 'call' if kind in ('call', 'method') else 'other', line(node))
        if kind is None:
            self.facts.add('unsupported', ctx.func, node.type, line(node))
        self.calls(node, s)
        return s

    def if_chain(self, node, roles, ctx):
        cond = self.expr(self.role(node, roles, 'cond'))
        then = self.role(node, roles, 'then')
        if cond != FALSE:  # P17: statically dead branch is not live code
            self.block(then, ctx.guard(cond, 'true'))
        if cond == ('bool', 'true'):
            return None
        rest = ctx.guard(cond, 'false')
        for alt in self.role(node, roles, 'alt', many=True):
            akind, aroles = self.kind(alt)
            if akind == 'if':
                rest_cond = self.expr(self.role(alt, aroles, 'cond'))
                if self.lang == 'python' and alt.type == 'elif_clause':
                    if rest_cond != FALSE:
                        self.block(self.role(alt, aroles, 'then'), rest.guard(rest_cond, 'true'))
                    rest = rest.guard(rest_cond, 'false')
                else:
                    self.if_chain(alt, aroles, rest)
            elif akind == 'else':
                body = self.role(alt, aroles, 'body')
                bkind, broles = self.kind(body)
                if bkind == 'if':
                    self.if_chain(body, broles, rest)
                else:
                    self.block(body, rest)
            else:
                self.block(alt, rest)
        return None

    def updated_name(self, upd):
        if upd is None:
            return None
        kind, roles = self.kind(upd)
        target = self.role(upd, roles, 'arg') if kind == 'update' else self.role(upd, roles, 'left')
        return text(target) if target is not None and target.type == 'identifier' else None

    def assignment(self, node, kind, roles, ctx):
        if kind == 'update':  # i++ / i--
            target = self.role(node, roles, 'arg')
            delta = 'sub' if '--' in text(node) else 'add'
            s = self.facts.new_stmt(ctx, 'assign', line(node))
            t = self.expr(target)
            self.facts.add('assign', s, t, op(delta, t, num(1)))
            return s
        if kind == 'r_assign':
            o = text(node.child_by_field_name('operator'))
            lhs, rhs = node.child_by_field_name('lhs'), node.child_by_field_name('rhs')
            if o in R_ASSIGN_RIGHT:
                lhs, rhs = rhs, lhs
            if rhs is not None and rhs.type == 'function_definition':
                return None
        else:
            lhs, rhs = self.role(node, roles, 'left'), self.role(node, roles, 'right')
        if rhs is None:
            return None  # declaration without value
        s = self.facts.new_stmt(ctx, 'assign', line(node))
        opnode = self.role(node, roles, 'op') if kind != 'r_assign' else None
        aug = AUGMENTED.get(text(opnode)) if opnode is not None else None
        if kind == 'aug_assign' and aug is None:
            aug = AUGMENTED.get(text(opnode), 'unknown')
        lkind, _ = self.kind(lhs)
        rkind, _ = self.kind(rhs)
        if lkind == 'tuple' and rkind == 'tuple':
            self.facts.add('par_assign', s, [self.expr(x) for x in named(lhs)],
                           [self.expr(x) for x in named(rhs)])
        else:
            t = self.expr(lhs)
            v = self.expr(rhs)
            self.facts.add('assign', s, t, op(aug, t, v) if aug else v)
        self.calls(rhs, s)
        return s

    def ret(self, value, ctx, node):
        return self.ret_term(self.expr(value) if value is not None else other('none'), ctx, node)

    def ret_term(self, value, ctx, node):
        s = self.facts.new_stmt(ctx, 'ret', line(node))
        self.facts.add('ret', s, value)
        self.calls(node, s)
        return s

    def calls(self, node, s):
        """call_at for every call inside node (for interprocedural nesting)."""
        if node is None:
            return
        stack = [node]
        while stack:
            n = stack.pop()
            kind, _ = self.kind(n)
            if kind in ('function', 'class'):
                continue
            if kind in ('call', 'method'):
                t = self.expr(n)
                if t[0] == 'call':
                    self.facts.add('call_at', s, t[1], t[2])
            stack.extend(named(n))

    # ----- expressions -----------------------------------------------------
    def args(self, node):
        if node is None:
            return []
        out = []
        for a in named(node):
            if a.type == 'argument':  # R
                a = a.child_by_field_name('value') or (named(a)[0] if named(a) else a)
            if a.type in ('keyword_argument',):
                continue
            out.append(self.expr(a))
        return out

    def expr(self, node):
        if node is None:
            return other('none')
        kind, roles = self.kind(node)
        if kind == 'ident':
            return var(text(node))
        if kind == 'int':
            raw = text(node).rstrip('LlUu').replace('_', '')
            try:
                value = float(raw) if self.lang == 'r' else int(raw, 0)
            except ValueError:
                return other('literal')
            return num(value) if value == int(value) else other('float')
        if kind == 'bool':
            return ('bool', text(node).lower())
        if kind == 'paren':
            return self.expr(self.role(node, roles, 'inner'))
        if kind == 'index':
            idx = self.role(node, roles, 'idx')
            if self.lang == 'r':
                inner = self.args(idx)
                return elem(self.expr(self.role(node, roles, 'seq')), inner[0] if inner else other('none'))
            return elem(self.expr(self.role(node, roles, 'seq')), self.expr(idx))
        if kind in ('binary', 'compare'):
            spelled = text(self.role(node, roles, 'op'))
            name = OPERATORS.get(spelled, spelled)
            if name == 'fdiv' and self.lang in INT_SLASH:
                name = 'div'
            return normalise(op(name, self.expr(self.role(node, roles, 'left')),
                                self.expr(self.role(node, roles, 'right'))))
        if kind == 'not':
            return op('not', self.expr(self.role(node, roles, 'arg')))
        if kind == 'unary':
            arg = self.role(node, roles, 'arg')
            spelled = text(self.role(node, roles, 'op')) if roles.get('op') else text(node)[:1]
            inner = self.expr(arg)
            if spelled.startswith('-'):
                return num(-inner[1]) if inner[0] == 'int' else op('neg', inner)
            if spelled.startswith('!') or spelled == 'not':
                return op('not', inner)
            return inner
        if kind == 'call':
            fn = self.role(node, roles, 'fn')
            args = self.args(self.role(node, roles, 'args'))
            fkind, froles = self.kind(fn)
            if fkind == 'field':  # receiver.method(args)
                name = text(self.role(fn, froles, 'field'))
                return self.call_term(name, [self.expr(self.role(fn, froles, 'obj'))] + args)
            return self.call_term(text(fn), args)
        if kind == 'method':
            obj = self.role(node, roles, 'obj')
            args = self.args(self.role(node, roles, 'args'))
            name = text(self.role(node, roles, 'name'))
            if obj is not None and text(obj) not in ('Collections', 'Arrays', 'this'):
                args = [self.expr(obj)] + args
            return self.call_term(name, args)
        if kind == 'field':
            name = text(self.role(node, roles, 'field'))
            if name in LENGTH_CALLS:
                return call('len', [self.expr(self.role(node, roles, 'obj'))])
            return other('field')
        if kind == 'tuple':
            return ('tuple', [self.expr(x) for x in named(node)])
        return other(node.type)

    def call_term(self, name, args):
        short = name.split('::')[-1].split('.')[-1]
        if short in LENGTH_CALLS:
            return call('len', args[:1])
        if short in WRAPPERS and len(args) == 1:
            return args[0]
        return call(short, args)


def normalise(t):
    """Tiny Metzger-Wen style tidy-up: constants to the right, +0 removed."""
    if t[0] == 'op' and t[1] == 'add' and len(t[2]) == 2:
        a, b = t[2]
        if a[0] == 'int' and b[0] != 'int':
            a, b = b, a
        if b == ('int', 0):
            return a
        return op('add', a, b)
    return t


def lower(lang, root) -> FactSet:
    return Lowerer(lang, FactSet(lang)).run(root)
