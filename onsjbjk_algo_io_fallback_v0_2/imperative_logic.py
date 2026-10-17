"""v0.2 imperative front end (doc 04 section 16): AP13's table-driven lowerer (polyglot_logic/tools/
lower_imperative.py, unchanged) subclassed for components it leaves opaque, so that the same component gives the
same facts in every language. Only additions; everything AP13 lowers stays as it is.

  an assignment used as a value (a = b = e in Python, (y = f(x)) < x in C): the value e
  a slice s[i:j] (Python): call(slice, [s, i, j]) (AP13's s[k:] with a constant k stays tail(s, k))
  a field p->f, s.f, o.f: field(p, f) (AP13: other(field); a length field stays len(o))
"""
from __future__ import annotations

from pathlib import Path

import compare_learners

compare_learners._ap13()
import lower_imperative as ap13  # AP13 tools on the path
from fact_io import FactSet, call, other
from lang_tables import LENGTH_CALLS
from lower_imperative import text
from parse_source import parse

ASSIGNMENT_VALUES = {'assignment', 'assignment_expression'}


class ImperativeLowerer(ap13.Lowerer):
    def expr(self, node):
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
        """[start, stop] of a slice (none where absent): a[k:] is [k, none], a[:k] is [none, k]."""
        bounds, current = [], None
        for c in idx.children:
            if c.type == ':':
                bounds.append(current)
                current = None
            elif c.is_named:
                current = c
        bounds.append(current)
        return [self.expr(b) if b is not None else other('none') for b in bounds[:2]]


def lower(path: Path) -> str:
    """The base facts of a Python, C, ... file, lowered by the subclass."""
    lang, _, root = parse(path)
    return ImperativeLowerer(lang, FactSet(lang)).run(root).text()

