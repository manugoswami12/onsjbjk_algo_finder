"""AP13 transform: Common Lisp s-expressions -> base facts (same vocabulary)."""
from __future__ import annotations

from fact_io import Ctx, FactSet, call, elem, num, op, other, var
from lang_tables import INT_SLASH, LENGTH_CALLS, LISP_ARITH, LISP_COMPARE, OPERATORS

STATEMENTS = {'let', 'let*', 'dotimes', 'loop', 'when', 'unless', 'if', 'cond', 'setf',
              'setq', 'incf', 'decf', 'rotatef', 'return-from', 'return', 'progn'}


class Sym(str):
    """A Lisp symbol (distinct from strings)."""


def to_lists(node, line_of):
    t = node.type
    if t == 'sym_lit':
        s = Sym(node.text.decode().lower())
        line_of[id(s)] = node.start_point[0] + 1
        return s
    if t == 'num_lit':
        try:
            return int(node.text.decode())
        except ValueError:
            return ('other', 'number')
    if t == 'list_lit':
        kids = [c for c in node.named_children if c.type not in ('comment',)]
        if len(kids) == 1 and kids[0].type in ('defun', 'loop_macro'):
            return to_lists(kids[0], line_of)
        out = [to_lists(c, line_of) for c in kids]
        line_of[id(out)] = node.start_point[0] + 1
        return out
    if t == 'defun':
        header = next(c for c in node.named_children if c.type == 'defun_header')
        name = header.child_by_field_name('function_name')
        lam = header.child_by_field_name('lambda_list')
        params = [c.text.decode().lower() for c in lam.named_children] if lam else []
        body = [to_lists(c, line_of) for c in node.children_by_field_name('value')]
        out = [Sym('defun'), name.text.decode().lower(), params, *body]
        line_of[id(out)] = node.start_point[0] + 1
        return out
    if t == 'loop_macro':
        out = [Sym('loop')]
        for clause in node.named_children:
            for c in clause.named_children:
                forms = [to_lists(x, line_of) for x in c.named_children]
                if c.type == 'while_clause':
                    out.append([Sym(':while'), *forms])
                elif c.type == 'do_clause':
                    out.append([Sym(':do'), *forms])
                else:
                    out.append([Sym(':other'), c.type])
        line_of[id(out)] = node.start_point[0] + 1
        return out
    return ('other', t)


class Lowerer:
    def __init__(self, facts: FactSet):
        self.facts, self.lines = facts, {}

    def line(self, form):
        return self.lines.get(id(form), 0)

    def run(self, root):
        for node in root.named_children:
            form = to_lists(node, self.lines)
            if isinstance(form, list) and form and form[0] == 'defun':
                self.defun(form)
        return self.facts

    def defun(self, form):
        f = self.facts.new_func(form[1], self.line(form))
        for k, p in enumerate(form[2]):
            self.facts.add('param', f, k, p)
        self.body(form[3:], Ctx(f), implicit=True)

    def body(self, forms, ctx, implicit=False):
        prev = None
        for i, form in enumerate(forms):
            s = self.stmt(form, ctx, implicit and i == len(forms) - 1)
            if prev and s:
                self.facts.add('next_stmt', prev, s)
            prev = s

    def stmt(self, form, ctx, implicit=False):
        head = form[0] if isinstance(form, list) and form and isinstance(form[0], str) else None
        line = self.line(form)
        if head in ('let', 'let*'):
            prev = None
            for binding in form[1]:
                if isinstance(binding, list) and len(binding) == 2:
                    s = self.facts.new_stmt(ctx, 'assign', line)
                    self.facts.add('assign', s, var(binding[0]), self.expr(binding[1]))
                    self.calls(binding[1], s)
                    if prev:
                        self.facts.add('next_stmt', prev, s)
                    prev = s
            self.body(form[2:], ctx, implicit)
            return prev
        if head == 'progn':
            self.body(form[1:], ctx, implicit)
            return None
        if head == 'dotimes' and isinstance(form[1], list) and form[1]:
            loop_id = self.facts.new_loop(ctx, 'count', line)
            self.facts.add('loop_var', loop_id, str(form[1][0]))
            self.calls(form[1][1], loop_id)
            self.body(form[2:], ctx.loop(loop_id))
            return loop_id
        if head == 'loop':
            loop_id = self.facts.new_loop(ctx, 'cond', line)
            inner = ctx.loop(loop_id)
            for clause in form[1:]:
                if clause[0] == ':while':
                    self.facts.add('loop_cond', loop_id, self.expr(clause[1]))
                elif clause[0] == ':do':
                    self.body(clause[1:], inner)
                else:
                    self.facts.add('unsupported', ctx.func, 'loop ' + str(clause[1]), line)
            return loop_id
        if head in ('when', 'unless'):
            cond = self.expr(form[1])
            self.body(form[2:], ctx.guard(cond, 'true' if head == 'when' else 'false'))
            return None
        if head == 'if':
            cond = self.expr(form[1])
            self.stmt(form[2], ctx.guard(cond, 'true'), implicit)
            if len(form) > 3:
                self.stmt(form[3], ctx.guard(cond, 'false'), implicit)
            return None
        if head == 'cond':
            rest = ctx
            for clause in form[1:]:
                if clause[0] == 't':
                    self.body(clause[1:], rest, implicit)
                    break
                cond = self.expr(clause[0])
                self.body(clause[1:], rest.guard(cond, 'true'), implicit)
                rest = rest.guard(cond, 'false')
            return None
        if head in ('setf', 'setq'):
            last = None
            for place, value in zip(form[1::2], form[2::2]):
                last = self.facts.new_stmt(ctx, 'assign', line)
                self.facts.add('assign', last, self.expr(place), self.expr(value))
                self.calls(value, last)
            return last
        if head in ('incf', 'decf'):
            s = self.facts.new_stmt(ctx, 'assign', line)
            place = self.expr(form[1])
            by = self.expr(form[2]) if len(form) > 2 else num(1)
            self.facts.add('assign', s, place, op('add' if head == 'incf' else 'sub', place, by))
            return s
        if head == 'rotatef' and len(form) == 3:
            s = self.facts.new_stmt(ctx, 'assign', line)
            a, b = self.expr(form[1]), self.expr(form[2])
            self.facts.add('par_assign', s, [a, b], [b, a])
            return s
        if head in ('return-from', 'return'):
            value = form[2] if head == 'return-from' else (form[1] if len(form) > 1 else None)
            s = self.facts.new_stmt(ctx, 'ret', line)
            self.facts.add('ret', s, self.expr(value) if value is not None else other('nil'))
            return s
        if implicit:
            s = self.facts.new_stmt(ctx, 'ret', line)
            self.facts.add('ret', s, self.expr(form))
            self.calls(form, s)
            return s
        s = self.facts.new_stmt(ctx, 'call' if head else 'other', line)
        self.calls(form, s)
        return s

    def calls(self, form, s):
        if not isinstance(form, list) or not form:
            return
        t = self.expr(form)
        if t[0] == 'call':
            self.facts.add('call_at', s, t[1], t[2])
        for x in form[1:]:
            self.calls(x, s)

    def expr(self, form):
        if isinstance(form, Sym):
            return ('bool', 'true') if form == 't' else var(form)
        if isinstance(form, int):
            return num(form)
        if not isinstance(form, list) or not form:
            return other('form')
        head, args = form[0], [self.expr(a) for a in form[1:]]
        if not isinstance(head, str):  # ((lambda ...) ...) and other computed heads
            return other('computed_call')
        if head == 'aref' and len(args) == 2:
            return elem(args[0], args[1])
        if head in ('1+', '1-') and len(args) == 1:
            return op('add' if head == '1+' else 'sub', args[0], num(1))
        if head == 'floor' and len(args) == 2:
            return op('div', args[0], args[1])
        if head == 'not' and len(args) == 1:
            return op('not', args[0])
        if head in LISP_COMPARE | LISP_ARITH and len(args) >= 2:
            name = OPERATORS.get(head, head)
            if name == 'fdiv' and 'commonlisp' in INT_SLASH:
                name = 'div'
            result = args[0]
            for a in args[1:]:  # left fold: (- n i 1) = (n - i) - 1
                result = op(name, result, a)
            return result
        if head == '-' and len(args) == 1:
            return num(-args[0][1]) if args[0][0] == 'int' else op('neg', args[0])
        if head in LENGTH_CALLS:
            return call('len', args[:1])
        return call(str(head), args)


def lower(root) -> FactSet:
    return Lowerer(FactSet('commonlisp')).run(root)
