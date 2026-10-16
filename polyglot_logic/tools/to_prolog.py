"""AP13 v4 (doc 10): every function of a source file -> an EXECUTABLE Prolog program (PNF).

Subclass of the working lower_imperative.Lowerer: its tables and its kind/role/expr/params/
ternary methods are reused unchanged; only statement lowering is overridden, to build a
structured program instead of flat dependence facts.

  pnf_fun(Name, [Param...], Body).
  Body: seq([...]) | assign(T, E) | par_assign([T], [E]) | if(C, A, B) | while(C, B)
        | c_for(Init, Cond, Update, Body) | for_range(V, From, To, Step, B) | for_each(V, E, B)
        | return(E) | break | continue | expr(E) | skip | unsupported(NodeType)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fact_io import FactSet, term  # noqa: E402
from lang_tables import IGNORED_STATEMENTS, IMPLICIT_RETURN  # noqa: E402
from lower_imperative import Lowerer, line, named, text  # noqa: E402
from parse_source import parse  # noqa: E402

COUNTING = {'range', 'xrange'}
CONSTANTS = {'math.pi': 3.141592653589793, 'math.e': 2.718281828459045}


def string_value(raw):
    import ast
    try:
        v = ast.literal_eval(raw)
        return v if isinstance(v, str) else str(v)
    except (ValueError, SyntaxError):
        return raw.strip('\'"')


class PNFLowerer(Lowerer):
    """Lowerer -> Prolog normal form. Nothing of the parent's fact output is used."""

    def __init__(self, lang):
        super().__init__(lang, FactSet(lang))
        self.funs = []                       # (name, params, body)

    # ----- functions -------------------------------------------------------------
    def run(self, root):
        self.scan(root, prefix='')
        if self.lang in ('python', 'r'):
            top = [c for c in named(root) if self.top_level_statement(c)]
            if top:
                self.funs.append(('<toplevel>', [], ('seq', [self.st(c) for c in top])))
        return self.funs

    def function(self, node, roles, prefix, name=None):        # overrides the parent
        name = prefix + (name or self.function_name(node, roles))
        body = self.role(node, roles, 'body')
        implicit = self.lang in IMPLICIT_RETURN
        self.funs.append((name, self.params(node, roles), self.blk(body, implicit)))
        return name

    def expr(self, node):                                   # value forms the fact view did not need
        if node is None:
            return ('none',)
        t = node.type
        if t == 'mut_pattern' and named(node):
            return self.expr(named(node)[-1])
        if t in ('none', 'null', 'null_literal', 'nil'):
            return ('none',)
        if t in ('float', 'float_literal', 'floating_point_literal', 'decimal_floating_point_literal'):
            try:
                return ('num', float(text(node).rstrip('fFdD').replace('_', '')))
            except ValueError:
                return ('other', 'float')
        if t in ('string', 'string_literal', 'interpreted_string_literal', 'raw_string_literal',
                 'char_literal', 'character_literal'):
            return ('str', string_value(text(node)))
        if t in ('list_comprehension', 'generator_expression', 'set_comprehension'):
            return self.comp(node)
        if t == 'attribute' and text(node) in CONSTANTS:
            return ('num', CONSTANTS[text(node)])
        if t == 'subscript' and node.child_by_field_name('subscript') is not None \
                and node.child_by_field_name('subscript').type == 'slice':
            sl = node.child_by_field_name('subscript')
            parts, cur = [None, None, None], 0
            for c in sl.children:
                if c.type == ':':
                    cur += 1
                elif c.is_named:
                    parts[cur] = self.expr(c)
            return ('slice', self.expr(node.child_by_field_name('value')),
                    *[x if x is not None else ('none',) for x in parts])
        return super().expr(node)

    def comp(self, node):
        """[v for x in s if c] -> comp(x, s, c, v): a plain loop, not the fact view's elem form."""
        kids = named(node)
        value, clauses = kids[0], kids[1:]
        fors = [c for c in clauses if c.type == 'for_in_clause']
        if len(fors) != 1:
            return ('other', 'nested_comprehension')
        left = fors[0].child_by_field_name('left')
        x = ('tuple', [self.expr(c) for c in named(left)]) if self.kind(left)[0] == 'tuple' else text(left)
        seq = self.expr(fors[0].child_by_field_name('right'))
        ifs = [c for c in clauses if c.type == 'if_clause']
        cond = self.expr(named(ifs[0])[0]) if ifs else ('bool', 'true')
        return ('comp', x, seq, cond, self.expr(value))

    # ----- statements ------------------------------------------------------------
    def blk(self, node, implicit=False):
        kind, _ = self.kind(node)
        kids = named(node) if kind == 'block' else ([node] if node is not None else [])
        out = []
        for i, c in enumerate(kids):
            s = self.st(c, implicit and i == len(kids) - 1)
            if s != ('skip',):
                out.append(s)
        return ('seq', out)

    def st(self, node, implicit=False):
        if node is None or node.type in IGNORED_STATEMENTS:
            return ('skip',)
        if node.type in ('break_statement', 'break_expression', 'break'):
            return ('break',)
        if node.type in ('continue_statement', 'continue_expression', 'next'):
            return ('continue',)
        if node.type in ('raise_statement', 'throw_statement'):
            return ('raise',)
        kind, roles = self.kind(node)
        if kind == 'expr_stmt':
            return self.st(self.role(node, roles, 'inner'), implicit)
        if kind in ('wrap',):
            return self.blk(self.role(node, roles, 'body'))
        if kind in ('assert', 'function', 'class') or node.type == 'pass_statement':
            return ('skip',)
        if kind == 'block':
            return self.blk(node, implicit)
        if kind == 'for_range':
            v = self.role(node, roles, 'var')
            it = self.role(node, roles, 'iter')
            body = self.blk(self.role(node, roles, 'body'))
            name = text(v) if v is not None else '_'
            if v is not None and self.kind(v)[0] == 'tuple':        # for i, x in enumerate(s)
                name = ('tuple', [self.expr(x) for x in named(v)])
            e = self.expr(it) if it is not None else ('other', 'none')
            if it is not None and it.type == 'range_expression':        # Rust a..b
                parts = named(it)
                lo = self.expr(parts[0]) if parts else ('int', 0)
                hi = self.expr(parts[1]) if len(parts) > 1 else ('other', 'none')
                return ('for_range', name, lo, hi, ('int', 1), body)
            if e[0] == 'call' and e[1] in COUNTING:
                a = e[2]
                lo, hi, step = (('int', 0), a[0], ('int', 1)) if len(a) == 1 else \
                    (a[0], a[1], a[2] if len(a) > 2 else ('int', 1))
                return ('for_range', name, lo, hi, step, body)
            return ('for_each', name, e, body)
        if kind == 'c_for':
            init = self.role(node, roles, 'init')
            cond = self.role(node, roles, 'cond')
            upd = self.role(node, roles, 'update')
            return ('c_for', self.st(init) if init is not None else ('skip',),
                    self.expr(cond) if cond is not None else ('bool', 'true'),
                    self.st(upd) if upd is not None else ('skip',),
                    self.blk(self.role(node, roles, 'body')))
        if kind in ('while', 'do_while'):
            cond = self.role(node, roles, 'cond')
            c = self.expr(cond) if cond is not None else ('bool', 'true')
            body = self.blk(self.role(node, roles, 'body'))
            if kind == 'do_while':
                return ('seq', [body, ('while', c, body)])
            return ('while', c, body)
        if kind == 'if':
            return self.if_term(node, roles, implicit)
        if kind == 'decl':
            return ('seq', [self.st(d) for d in self.role(node, roles, 'declarator', many=True)])
        if kind in ('assign', 'aug_assign', 'r_assign', 'update'):
            return self.assign_term(node, kind, roles)
        if kind == 'return':
            v = self.role(node, roles, 'value')
            return ('return', self.expr(v) if v is not None else ('other', 'none'))
        if kind == 'call' and self.lang == 'r' and text(self.role(node, roles, 'fn')) == 'return':
            args = self.args(self.role(node, roles, 'args'))
            return ('return', args[0] if args else ('int', 0))
        if implicit and kind in ('ident', 'int', 'binary', 'unary', 'call', 'index', 'paren', 'method',
                                 'field', 'tuple', 'bool'):
            return ('return', self.expr(node))
        if kind in ('call', 'method', 'binary', 'unary', 'index', 'ident'):
            return ('expr', self.expr(node))
        if kind is None and node.type in ('empty_statement', ';'):
            return ('skip',)
        return ('unsupported', node.type)

    def if_term(self, node, roles, implicit):
        c = self.expr(self.role(node, roles, 'cond'))
        then = self.blk(self.role(node, roles, 'then'), implicit)
        alts = self.role(node, roles, 'alt', many=True)
        return ('if', c, then, self.alt_chain(alts, implicit))

    def alt_chain(self, alts, implicit):
        if not alts:
            return ('skip',)
        alt, rest = alts[0], alts[1:]
        akind, aroles = self.kind(alt)
        if akind == 'if':
            c = self.expr(self.role(alt, aroles, 'cond'))
            then = self.blk(self.role(alt, aroles, 'then'), implicit)
            inner = self.role(alt, aroles, 'alt', many=True)
            return ('if', c, then, self.alt_chain(inner + rest, implicit))
        if akind == 'else':
            body = self.role(alt, aroles, 'body')
            bkind, broles = self.kind(body)
            if bkind == 'if':
                return self.if_term(body, broles, implicit)
            return self.blk(body, implicit)
        return self.blk(alt, implicit)

    def assign_term(self, node, kind, roles):
        if kind == 'update':                                   # i++ / i--
            t = self.expr(self.role(node, roles, 'arg'))
            return ('assign', t, ('op', 'sub' if '--' in text(node) else 'add', [t, ('int', 1)]))
        if kind == 'r_assign':
            from lang_tables import R_ASSIGN_RIGHT
            o = text(node.child_by_field_name('operator'))
            lhs, rhs = node.child_by_field_name('lhs'), node.child_by_field_name('rhs')
            if o in R_ASSIGN_RIGHT:
                lhs, rhs = rhs, lhs
            opnode = None
        else:
            lhs, rhs = self.role(node, roles, 'left'), self.role(node, roles, 'right')
            opnode = self.role(node, roles, 'op')
        if rhs is None:
            return ('skip',)
        from lang_tables import AUGMENTED
        aug = AUGMENTED.get(text(opnode), 'op' + text(opnode)) if kind == 'aug_assign' else None
        lk, _ = self.kind(lhs)
        rk, _ = self.kind(rhs)
        if lk == 'tuple' and rk == 'tuple':
            return ('par_assign', [self.expr(x) for x in named(lhs)], [self.expr(x) for x in named(rhs)])
        t = self.expr(lhs)
        tern = self.ternary(rhs)
        v = ('cond', self.expr(tern[0]), self.expr(tern[1]), self.expr(tern[2])) if tern else self.expr(rhs)
        return ('assign', t, ('op', aug, [t, v]) if aug else v)


def normal_form(path: Path) -> tuple[str, list]:
    lang, data, root = parse(path)
    if lang == 'commonlisp':
        from lisp_to_prolog import lisp_normal_form
        return lang, lisp_normal_form(data.decode('utf-8', 'replace'))
    if root is None:
        return lang, []                       # Prolog source: run natively (run_main.pl)
    return lang, PNFLowerer(lang).run(root)


def pnf_text(path: Path) -> tuple[str, str]:
    lang, funs = normal_form(path)
    lines = [f"pnf_lang({term(lang)})."]
    for name, params, body in funs:
        lines.append(f"pnf_fun({term(name)},{term(list(params))},{render(body)}).")
    return lang, '\n'.join(lines) + '\n'


def term_var(p):
    return p


def render(t):
    """term() with zero-argument statements as atoms (skip, break, continue); floats as numbers."""
    if isinstance(t, float):
        return repr(t) if t == t and t not in (float('inf'), float('-inf')) else '0.0'
    if isinstance(t, tuple) and len(t) == 1:
        return term(t[0])
    if isinstance(t, tuple):
        return term(t[0]) + '(' + ','.join(render(a) for a in t[1:]) + ')'
    if isinstance(t, list):
        return '[' + ','.join(render(a) for a in t) + ']'
    return term(t)


if __name__ == '__main__':
    print(pnf_text(Path(sys.argv[1]))[1])
