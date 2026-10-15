"""AP13 fact file save/load: language-neutral base facts as grouped Prolog clauses.

Terms are Python tuples ('var', 'x'), ('int', 1), ('op', 'add', [a, b]) ...
Atoms are quoted with the frozen AP2 exporter's atom(), never spliced as code.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from env_run import REPO

sys.path.insert(0, str(REPO / 'semgrep_prolog_poc' / 'tools'))
from export_ast_facts import atom  # noqa: E402  (frozen, reused unchanged)

PREDICATES = ('lang', 'func', 'param', 'stmt', 'loop', 'in_loop', 'loop_var', 'loop_cond',
              'guard', 'assign', 'par_assign', 'call_at', 'ret', 'next_stmt', 'unsupported')


def var(name): return ('var', str(name))
def num(n): return ('int', int(n))
def op(name, *args): return ('op', name, list(args))
def elem(seq, idx): return ('elem', seq, idx)
def call(name, args): return ('call', str(name), list(args))
def other(kind): return ('other', str(kind))


def term(value) -> str:
    """Render a Python term as inert Prolog text."""
    if isinstance(value, list):
        return '[' + ','.join(term(v) for v in value) + ']'
    if isinstance(value, tuple):
        head, *args = value
        return atom(head) + '(' + ','.join(term(a) for a in args) + ')'
    if isinstance(value, bool):
        return atom('true' if value else 'false')
    if isinstance(value, int):
        return str(value)
    return atom(value)


@dataclass
class Ctx:
    """Where a statement sits: its function, enclosing loops and guards."""
    func: str
    loops: tuple = ()
    guards: tuple = ()

    def loop(self, loop_id):
        return Ctx(self.func, self.loops + (loop_id,), self.guards)

    def guard(self, cond, polarity):
        return Ctx(self.func, self.loops, self.guards + ((cond, polarity),))


@dataclass
class FactSet:
    lang: str
    facts: dict = field(default_factory=lambda: {p: [] for p in PREDICATES})
    counter: int = 0

    def add(self, pred, *args):
        self.facts[pred].append(args)

    def new_id(self, prefix):
        self.counter += 1
        return f'{prefix}{self.counter}'

    def new_func(self, name, line):
        f = self.new_id('f')
        self.add('func', f, name, line)
        return f

    def new_stmt(self, ctx: Ctx, kind, line):
        s = self.new_id('s')
        self.add('stmt', s, ctx.func, kind, line)
        for loop_id in ctx.loops:
            self.add('in_loop', s, loop_id)
        for cond, polarity in ctx.guards:
            self.add('guard', s, cond, polarity)
        return s

    def new_loop(self, ctx: Ctx, kind, line):
        loop_id = self.new_stmt(ctx, 'loop', line)
        self.add('loop', loop_id, ctx.func, kind)
        return loop_id

    def functions(self):
        return [(f, name) for f, name, _ in self.facts['func']]

    def text(self) -> str:
        lines = ['% AP13 language-neutral base facts (generated; source never executed).',
                 f'lang({atom(self.lang)}).']
        for pred in PREDICATES[1:]:
            seen = set()
            for args in self.facts[pred]:
                line = f'{pred}(' + ','.join(term(a) for a in args) + ').'
                if line not in seen:
                    seen.add(line)
                    lines.append(line)
        return '\n'.join(lines) + '\n'

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.text(), encoding='utf-8')
        return path
