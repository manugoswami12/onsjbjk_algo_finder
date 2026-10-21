"""v0.2 imperative front end (doc 04 section 16): AP13's table-driven lowerer (polyglot_logic/tools/
lower_imperative.py, unchanged) subclassed for components it leaves opaque, so that the same component gives the
same facts in every language. Only additions; everything AP13 lowers stays as it is.

  an assignment used as a value (a = b = e in Python, (y = f(x)) < x in C): the value e; the inner b = e of a
  chained assignment (Python, C) is a statement too (AP13 lowers a = e only)
  a slice s[i:j] (Python): call(slice, [s, i, j]), s[i:j:k]: call(slice, [s, i, j, k]) (AP13's s[k:] with a constant k
  stays tail(s, k))
  a field p->f, s.f, o.f: field(p, f) (AP13: other(field); a length field stays len(o))
  a generator argument f(x for x in s if c): one argument, the comprehension map/filter (AP13: its parts)
  a dict literal {k: v}: dict([pair(k, v)]) (AP13: other(dictionary))
  an f-string f"..{e}..": fstring([e, ...]) (AP13: other(string))
  a tuple loop target for i, x in ...: loop_var(L, i), loop_var(L, x) (AP13: one variable named 'i, x')
  a counted loop's step: loop_step(L, K) for a constant K, loop_step(L, var(P)) for a variable stride, from Python
  range(a, b, K) and C for (...; i += K) / i = i + K / i++ / i-- (AP13 keeps neither; doc 04 section 17)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import compare_learners

compare_learners._ap13()
import lower_imperative as ap13  # AP13 tools on the path
from fact_io import FactSet, call, other, term
from lang_tables import LENGTH_CALLS
from lower_imperative import text
from parse_source import parse

ASSIGNMENT_VALUES = {'assignment', 'assignment_expression'}


@dataclass
class StepFacts(FactSet):
    """AP13's fact set with loop_step/2 facts after AP13's own."""
    steps: list = field(default_factory=list)

    def text(self) -> str:
        return super().text() + ''.join(f"loop_step('{lp}',{k if isinstance(k, int) else term(k)}).\n"
                                        for lp, k in self.steps)


class ImperativeLowerer(ap13.Lowerer):
    def stmt(self, node, ctx, implicit=False):
        if node is not None and node.type in ASSIGNMENT_VALUES:    # a = b = e: b = e is a statement too
            right = node.child_by_field_name('right')
            if right is not None and right.type in ASSIGNMENT_VALUES:
                self.stmt(right, ctx, implicit)
        loop_id = super().stmt(node, ctx, implicit)
        if loop_id is not None and node is not None and isinstance(self.facts, StepFacts):
            kind, roles = self.kind(node)
            if kind == 'for_range':
                self.split_targets(loop_id, self.role(node, roles, 'var'))
            k = (self.range_step(self.role(node, roles, 'iter')) if kind == 'for_range'
                 else self.update_step(self.role(node, roles, 'update')) if kind == 'c_for' else None)
            if k is not None:
                self.facts.steps.append((loop_id, k))
        return loop_id

    def split_targets(self, loop_id, v):
        """for i, x in ...: loop_var(L, i) and loop_var(L, x), not one variable named 'i, x' (AP13)."""
        if v is None or v.type not in ('pattern_list', 'tuple_pattern', 'tuple'):
            return
        names = [text(c) for c in v.named_children if c.type == 'identifier']
        if not names:
            return
        joined = text(v)
        self.facts.facts['loop_var'] = [a for a in self.facts.facts['loop_var'] if a != (loop_id, joined)]
        self.facts.facts['loop_var'] += [(loop_id, n) for n in names]

    def range_step(self, it):
        """K of range(a, b, K): a constant, or a variable stride var(p)."""
        t = self.expr(it) if it is not None else None
        if t and t[0] == 'call' and t[1] == 'range' and len(t[2]) == 3:
            k = constant(t[2][2])
            return t[2][2] if k is None and t[2][2][0] == 'var' else k
        return None

    def update_step(self, upd):
        """K of i += K, i -= K, i = i + K, i = i - K, i++, i-- (C for update)."""
        if upd is None:
            return None
        name = self.updated_name(upd)
        kind, roles = self.kind(upd)
        if kind == 'update':
            return -1 if '--' in text(upd) else 1
        if name is None or kind not in ('assign', 'aug_assign'):
            return None
        v = self.expr(self.role(upd, roles, 'right'))
        if '+=' in text(upd) or '-=' in text(upd):
            k = constant(v)
            if k is None:                         # i += p: a variable stride (only upwards: i -= p is not named)
                return v if '+=' in text(upd) and v and v[0] == 'var' else None
            return -k if '-=' in text(upd) else k
        if v and v[0] == 'op' and v[1] in ('add', 'sub') and v[2][0] == ('var', name):
            k = constant(v[2][1])
            if k is None:
                return v[2][1] if v[1] == 'add' and v[2][1][0] == 'var' else None
            return k if v[1] == 'add' else -k
        return None

    def args(self, node):
        """f(x for x in s): the one argument is the comprehension (AP13 lowers the generator's parts as arguments)."""
        if node is not None and node.type == 'generator_expression':
            return [self.comprehension(node)]
        return super().args(node)

    def expr(self, node):
        if node is not None and node.type == 'string' and any(c.type == 'interpolation' for c in node.children):
            parts = [c.named_children[0] for c in node.children if c.type == 'interpolation' and c.named_children]
            return ('fstring', [self.expr(x) for x in parts])           # f"..{e}..": fstring([e, ...])
        if node is not None and node.type == 'dictionary':               # {k: v, ...}: dict([pair(k, v), ...])
            pairs = [c for c in node.named_children if c.type == 'pair']
            return ('dict', [('pair', self.expr(c.child_by_field_name('key')), self.expr(c.child_by_field_name('value')))
                             for c in pairs])
        if node is not None and node.type in ASSIGNMENT_VALUES:          # a = b = e: the value e
            right = node.child_by_field_name('right')
            if right is not None:
                return self.expr(right)
        if node is not None:
            kind, roles = self.kind(node)
            if kind == 'index':
                idx = self.role(node, roles, 'idx')
                if idx is not None and idx.type == 'slice':
                    t = super().expr(node)
                    if t[0] == 'tail':
                        return t
                    return call('slice', [self.expr(self.role(node, roles, 'seq'))] + self.slice_bounds(idx))
            if kind == 'field':
                name = text(self.role(node, roles, 'field'))
                if name not in LENGTH_CALLS:
                    return ('field', self.expr(self.role(node, roles, 'obj')), name)
        return super().expr(node)

    def slice_bounds(self, idx):
        """[start, stop] of a slice (none where absent): a[k:] is [k, none], a[:k] is [none, k]; with a step,
        [start, stop, step]: a[::-1] is [none, none, -1]."""
        bounds, current = [], None
        for c in idx.children:
            if c.type == ':':
                bounds.append(current)
                current = None
            elif c.is_named:
                current = c
        bounds.append(current)
        if len(bounds) < 3 or bounds[2] is None:
            bounds = bounds[:2]
        return [self.expr(b) if b is not None else other('none') for b in bounds]


def constant(t):
    """The integer of int(K) or -K, else None."""
    if t and t[0] == 'int':
        return t[1]
    if t and t[0] == 'op' and t[1] == 'neg' and t[2][0][0] == 'int':
        return -t[2][0][1]
    return None


def lower(path: Path) -> str:
    """The base facts of a Python, C, ... file, lowered by the subclass."""
    lang, _, root = parse(path)
    return ImperativeLowerer(lang, StepFacts(lang)).run(root).text()

