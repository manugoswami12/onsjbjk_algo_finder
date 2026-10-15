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
              'guard', 'assign', 'par_assign', 'call_at', 'ret', 'next_stmt', 'unsupported',
              'loop_iter')
SELF = '$self'


def base_name(name: str) -> str:
    return name.split('.')[-1].split('/')[0]


def rename_calls(t, old, new):
    """Replace call(old, ...) by call(new, ...) anywhere inside a term."""
    if isinstance(t, list):
        return [rename_calls(x, old, new) for x in t]
    if isinstance(t, tuple):
        if t and t[0] == 'call' and t[1] == old:
            return ('call', new, rename_calls(t[2], old, new))
        return tuple(rename_calls(x, old, new) for x in t)
    return t


def has_call(t, name):
    if isinstance(t, list):
        return any(has_call(x, name) for x in t)
    if isinstance(t, tuple):
        if t and t[0] == 'call' and t[1] == name:
            return True
        return any(has_call(x, name) for x in t)
    return False


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

    def expand_folds(self):
        """doc 07: a library fold is the accumulator loop it stands for (as the Haskell
        lowerer does for foldl): r = reduce(mul, xs, 1) / prod(xs) / sum(xs)  ->
        acc = z; for e in xs: acc = acc (op) e; r = acc. Only named operators are
        expanded; any other folding function stays an opaque call."""
        from lang_tables import CALL_FOLDS, OPERATOR_FUNCTIONS
        stmt = {a[0]: a for a in self.facts['stmt']}

        def fold_of(t):
            if not (isinstance(t, tuple) and t and t[0] == 'call' and t[1] in CALL_FOLDS):
                return None
            fixed, args = CALL_FOLDS[t[1]], t[2]
            if fixed:
                return (fixed[0], args[0], num(fixed[1])) if len(args) == 1 else None
            if len(args) in (2, 3) and args[0][0] == 'var' and args[0][1].split('.')[-1] in OPERATOR_FUNCTIONS:
                z = args[2] if len(args) == 3 else None
                return OPERATOR_FUNCTIONS[args[0][1].split('.')[-1]], args[1], z
            return None

        def expand(s, t):
            if isinstance(t, list):
                return [expand(s, x) for x in t]
            if not isinstance(t, tuple):
                return t
            f = fold_of(t)
            if f is None:
                return tuple(expand(s, x) for x in t)
            name, seq, z = f
            _, func, _, ln = stmt[s]
            loops = tuple(l for x, l in self.facts['in_loop'] if x == s)
            ctx = Ctx(func, loops, tuple((c, p) for x, c, p in self.facts['guard'] if x == s))
            acc, el = var(f'$acc{s}'), var(f'$e{s}')
            if z is not None:
                self.add('assign', self.new_stmt(ctx, 'assign', ln), acc, z)
            loop_id = self.new_loop(ctx, 'count', ln)
            self.add('loop_var', loop_id, el[1])
            self.add('loop_iter', loop_id, expand(s, seq))
            self.add('assign', self.new_stmt(ctx.loop(loop_id), 'assign', ln), acc, op(name, acc, el))
            return acc

        for pred in ('ret', 'assign'):
            self.facts[pred] = [(a[0],) + tuple(expand(a[0], x) for x in a[1:]) if a[0] in stmt else a
                                for a in list(self.facts[pred])]

    def finish(self):
        """Shared post-pass (doc 05 G2): a self-calling function is a recursion loop;
        self-calls are named $self; recursive arguments become parameter updates."""
        self.expand_folds()
        stmt_func = {a[0]: a[1] for a in self.facts['stmt']}
        params = {}
        for f, k, name in sorted(self.facts['param'], key=lambda a: (a[0], a[1])):
            params.setdefault(f, []).append(name)
        rec = {a[1] for a in self.facts['loop'] if a[2] == 'recursion'}
        for f, name, line in list(self.facts['func']):
            b = base_name(name)
            own = {s for s, g in stmt_func.items() if g == f}
            selfcalls = [a for a in self.facts['call_at'] if a[0] in own and a[1] == b]
            if not selfcalls:
                continue
            for pred in ('ret', 'assign', 'par_assign', 'guard', 'call_at', 'loop_cond'):
                self.facts[pred] = [
                    (a[0],) + tuple(rename_calls(x, b, SELF) for x in a[1:])
                    if (a[0] in own or pred == 'loop_cond') else a
                    for a in self.facts[pred]]
            self.facts['call_at'] = [(a[0], SELF, a[2]) if a[0] in own and a[1] == b else a
                                     for a in self.facts['call_at']]
            # every self-call updates its parameters (also non-tail calls such as n * f(n - 1),
            # which equational lowerers do not model as one step)
            ps = params.get(f, [])
            updated = {(a[0], term(a[1])) for a in self.facts['assign']}   # terms hold lists
            for s, _, args in [a for a in self.facts['call_at'] if a[0] in own and a[1] == SELF]:
                for k, arg in enumerate(args[:len(ps)]):
                    if arg != var(ps[k]) and (s, term(var(ps[k]))) not in updated:
                        self.facts['assign'].append((s, var(ps[k]), arg))
                        updated.add((s, term(var(ps[k]))))
            if f in rec:
                continue  # equational lowerers already modelled the recursion loop
            loop_id = self.new_id('s')
            self.facts['stmt'].append((loop_id, f, 'loop', line))
            self.facts['loop'].append((loop_id, f, 'recursion'))
            for s in sorted(own):
                self.facts['in_loop'].append((s, loop_id))
            # base cases end the recursion: guards of non-recursive returns give loop_cond
            for s, value in [a for a in self.facts['ret'] if a[0] in own]:
                if has_call(value, SELF):
                    continue
                for g_s, cond, pol in self.facts['guard']:
                    if g_s == s and pol == 'true' and cond[0] == 'op':
                        self.facts['loop_cond'].append((loop_id, op('not', cond)))
        return self

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
