"""Haskell -> Prolog normal form (PNF) through GHC's own desugarer (GHC Core).

GHC compiles the module only as far as Core (`-ddump-ds`, nothing is linked or run); Core is a
tiny functional language (lambda, application, let/letrec, join, case) in which `where`, guards,
pattern matching and list comprehensions are already desugared. This module parses that Core
and lowers it to the same PNF the AP13 interpreter (polyglot_logic/prolog/interp.pl) runs, so the
behaviour catalog learned from Python applies unchanged:
  type-class dictionaries ($d.., @a) dropped; local functions lambda-lifted; case -> if-chains on
  Bool / list ([] and :) / boxed literals; overloaded literals and fromInteger are numbers;
  known Prelude functions -> PNF ops/builtins; anything else -> ('unsupported', ...) (not run).
"""
from __future__ import annotations

import itertools
import re
import subprocess
import tempfile
from pathlib import Path

GHC_FLAGS = ['-fforce-recomp', '-O0', '-c', '-ddump-ds', '-dsuppress-all', '-dno-typeable-binds',
             '-dsuppress-module-prefixes', '-dppr-cols=200', '-w',
             '-fdefer-type-errors', '-fdefer-out-of-scope-variables']
CLASH = {'gcd', 'lcm', 'product', 'sum', 'length', 'reverse', 'elem', 'maximum', 'minimum', 'lookup', 'filter',
         'map', 'foldl', 'foldr', 'take', 'drop', 'zip', 'head', 'tail', 'last', 'init', 'null', 'and', 'or',
         'any', 'all', 'concat', 'replicate', 'iterate', 'even', 'odd', 'abs', 'signum', 'div', 'mod', 'quot',
         'rem', 'max', 'min', 'sqrt', 'exp', 'log', 'pi', 'words', 'lines', 'splitAt', 'span', 'until',
         'subtract', 'succ', 'pred', 'fst', 'snd', 'id', 'const', 'flip', 'sequence', 'mapM', 'print'}


# ----------------------------------------------------------------------------------------- GHC
def core_text(path: Path, timeout=90) -> str:
    src = path.read_text(encoding='utf-8', errors='replace')
    src = re.sub(r'^(?:Prelude|\*?Main|ghci|λ)?>.*$', '', src, flags=re.M)          # GHCi transcript lines
    pragmas = re.findall(r'^\{-#.*?#-\}', src, re.M | re.S)
    src = re.sub(r'^\{-#.*?#-\}', '', src, flags=re.M | re.S)
    if not re.search(r'^module\s', src, re.M):
        has_main = re.search(r'^main\s*(::|=)', src, re.M)
        head = 'module Main where\n' if has_main else 'module M where\n'
        defined = set(re.findall(r'^([a-z_][\w\']*)\s*(?:::|[^\n=]*=)', src, re.M))
        hide = sorted(defined & CLASH)
        if hide and not re.search(r'^import\s+Prelude', src, re.M):
            head += f'import Prelude hiding ({", ".join(hide)})\n'
        # imports must come right after the header: move them up
        imports = re.findall(r'^import .*$', src, re.M)
        body = re.sub(r'^import .*$', '', src, flags=re.M)
        src = head + '\n'.join(imports) + '\n' + body
    src = '\n'.join(pragmas) + '\n' + src
    with tempfile.TemporaryDirectory(prefix='v02_ghc_') as td:
        f = Path(td) / 'Main.hs'
        f.write_text(src, encoding='utf-8')
        proc = subprocess.run(['ghc', *GHC_FLAGS, str(f), '-o', str(Path(td) / 'o'), '-ohi', str(Path(td) / 'hi'),
                               '-outputdir', td], capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, cwd=td)
    out = proc.stdout
    if '==================== Desugar' not in out:
        raise ValueError('ghc: ' + (proc.stderr.strip().splitlines() or ['no Core'])[0][:200])
    return out.split('==================== Desugar', 1)[1].split('\n', 1)[1]


# --------------------------------------------------------------------------------- Core parse
TOKEN = re.compile(r'''
  (?P<ws>\s+|--(?![!#$%&*+./<=>?^|~:])[^\n]*) | (?P<cast>\|>\s*<Co:\d+>|`cast`\s*<Co:\d+>\s*::\s*\.\.\.) | (?P<co><Co:\d+>)
| (?P<str>"(?:\\.|[^"\\])*"\#*) | (?P<chr>'(?:\\.|[^'\\])'\#*)
| (?P<num>-?\d+\.\d+(?:e-?\d+)?\#*|-?\d+\#*)
| (?P<punct>\\|->|[(){};,]|\[\]|=(?![=>])|@)
| (?P<name>\$[A-Za-z0-9]*[!#%&*+./<=>?^|~:\-]+|\$?[A-Za-z_][\w$'#]*(?:\[\]|\(,+\))?|\(,+\)|\$[\w$']+)
| (?P<op>[!#$%&*+./<=>?^|~:\-]+)
''', re.X)


class Tok:
    __slots__ = ('kind', 'text', 'col')

    def __init__(self, kind, text, col):
        self.kind, self.text, self.col = kind, text, col

    def __repr__(self):
        return self.text


def tokenize(text):
    """Whole-text scan (string literals of deferred errors may span lines); col = column."""
    lines = [l for l in text.splitlines() if not (l.startswith('Result size') or l.strip().startswith('= {terms'))]
    text = '\n'.join(lines)
    toks, pos = [], 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError('core token: ' + text[pos:pos + 30])
        kind = m.lastgroup
        if kind not in ('ws', 'cast', 'co'):
            toks.append(Tok(kind, m.group(), m.start() - (text.rfind('\n', 0, m.start()) + 1)))
        pos = m.end()
    return toks


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        return self.t[self.i + k].text if self.i + k < len(self.t) else None

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok.text

    def expect(self, s):
        if self.peek() != s:
            raise ValueError(f'core parse: expected {s} got {self.peek()}')
        self.i += 1

    def skip_type(self):
        """After '@': a type atom (name or balanced parentheses)."""
        if self.peek() == '(':
            depth = 0
            while True:
                x = self.next()
                depth += x == '('
                depth -= x == ')'
                if depth == 0:
                    return
        self.next()

    def program(self):
        binds = []
        while self.i < len(self.t):
            if self.peek() in ('Rec', 'end'):
                self.next()
                if self.peek() == 'Rec':
                    self.next()
                if self.peek() in ('{', '}'):
                    self.next()
                continue
            name = self.next()
            self.expect('=')
            start = self.i
            # the body ends at the next column-0 token
            j = self.i
            while j < len(self.t) and not (self.t[j].col == 0 and j > start):
                j += 1
            sub = Parser(self.t[self.i:j])
            binds.append((name, sub.expr()))
            self.i = j
        return binds

    def expr(self):
        p = self.peek()
        if p == '\\':
            self.next()
            params = []
            while self.peek() != '->':
                if self.peek() == '@':
                    self.next()
                    self.skip_type()
                    continue
                params.append(self.next())
            self.expect('->')
            return ('lam', params, self.expr())
        if p in ('let', 'letrec', 'join', 'joinrec'):
            self.next()
            self.expect('{')
            binds = []
            while self.peek() != '}':
                name = self.next()
                params = []
                while self.peek() != '=':
                    x = self.next()
                    if x != '!':
                        params.append(x)
                self.expect('=')
                body = self.expr()
                binds.append((name, ('lam', params, body) if params else body))
                if self.peek() == ';':
                    self.next()
            self.expect('}')
            self.expect('in')
            return ('let', p.startswith('join'), binds, self.expr())
        if p == 'case':
            self.next()
            scrut = self.expr()
            self.expect('of')
            if self.peek() != '{':
                self.next()                      # case binder
            self.expect('{')
            alts = []
            while self.peek() != '}':
                pat = []
                while self.peek() != '->':
                    pat.append(self.next())
                self.expect('->')
                alts.append((pat, self.expr()))
                if self.peek() == ';':
                    self.next()
            self.expect('}')
            return ('case', scrut, alts)
        if p == 'jump':
            self.next()
        return self.app()

    def app(self):
        parts = []
        while self.i < len(self.t) and self.peek() not in (')', '}', ';', ',', 'of', 'in', '->', None):
            if self.peek() == '@':
                self.next()
                self.skip_type()
                continue
            if self.peek() in ('\\', 'let', 'letrec', 'case', 'join', 'joinrec', 'jump'):
                parts.append(self.expr())
                break
            parts.append(self.atom())
        if not parts:
            raise ValueError('core parse: empty application at ' + str(self.peek()))
        return parts[0] if len(parts) == 1 else ('app', parts[0], parts[1:])

    def atom(self):
        tok = self.t[self.i]
        self.i += 1
        if tok.text == '(':
            items = [self.expr()]
            while self.peek() == ',':
                self.next()
                items.append(self.expr())
            self.expect(')')
            return items[0] if len(items) == 1 else ('tuple', items)
        if tok.text == '[]':
            return ('nil',)
        if tok.kind == 'num':
            v = tok.text.rstrip('#')
            return ('lit', float(v) if '.' in v else int(v))
        if tok.kind == 'str':
            return ('slit', bytes(tok.text.rstrip('#')[1:-1], 'utf-8').decode('unicode_escape'))
        if tok.kind == 'chr':
            c = tok.text.rstrip('#')[1:-1]
            return ('lit', ord(bytes(c, 'utf-8').decode('unicode_escape')))
        return ('v', tok.text)


# ------------------------------------------------------------------------------- Core -> PNF
def dictish(e):
    head = e[1] if e[0] == 'app' else e
    return head[0] == 'v' and (re.match(r'\$[A-Za-z]', head[1]) is not None or head[1] in ('void#', 'realWorld#'))


def strip_lams(e):
    """Leading \\ @a $dX -> and `let { $dX = .. } in` layers; returns (value params, body)."""
    params = []
    while True:
        if e[0] == 'lam':
            params += [p for p in e[1] if not p.startswith('$') and p != '_']
            e = e[2]
        elif e[0] == 'let' and all(n.startswith('$') for n, _ in e[2]):
            e = e[3]
        else:
            return params, e


BIN = {'+': 'add', '-': 'sub', '*': 'mul', 'div': 'div', 'quot': 'div', 'mod': 'mod', 'rem': 'mod', '^': 'pow',
       '**': 'pow', '/': 'fdiv', '==': 'eq', '/=': 'ne', '<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge',
       '&&': 'and', '||': 'or', 'shiftR': 'shr', 'shiftL': 'shl', 'xor': 'xor', '++': 'add'}
IDENT = {'fromInteger', 'fromIntegral', 'toInteger', 'realToFrac', 'fromEnum', 'toEnum', 'id', 'I#', 'IS', 'W#',
         'D#', 'C#', 'F#', 'integerToInt', 'integerFromInt', 'unsafeCoerce', 'lazy', 'inline', 'fromRational'}
CALL1 = {'abs': 'abs', 'sqrt': 'sqrt', 'floor': 'floor', 'ceiling': 'ceil', 'truncate': 'int', 'round': 'round',
         'sum': 'sum', 'product': 'product', 'maximum': 'max', 'minimum': 'min', 'reverse': 'reverse',
         'length': 'len', 'genericLength': 'len', 'sort': 'sorted', 'isqrt': 'isqrt'}
CALL2 = {'gcd': 'gcd', 'max': 'max', 'min': 'min'}
RAISE = {'error', 'errorWithoutStackTrace', 'undefined', 'patError'}


def base(name):
    return re.sub(r'_[a-zA-Z0-9]{3,5}$', '', name) if re.search(r'_[a-zA-Z0-9]{3,5}$', name) else name


class Lower:
    def __init__(self, binds):
        self.binds = binds
        self.globals = {n for n, _ in binds}
        self.funs, self.tmp, self.local = [], itertools.count(), {}
        self.listy = set()
        self.alias = {}            # let-bound partial applications, inlined (per function scope)
        self.locfun_arity = {}     # local (lifted) function -> value-parameter count
        self.params_fn = set()

    def fresh(self):
        return f'h${next(self.tmp)}'

    def run(self):
        for name, e in self.binds:
            if name.startswith('$') or name == 'main':
                continue
            params, body = strip_lams(e)
            if params:
                self.function(name, params, body)
            else:
                self.eta(name, body)
        return self.finish()

    def eta(self, name, body):
        """Point-free definitions (`f = product . enumFromTo 1`): eta-expand by 1 or 2 parameters."""
        # `f = letrec { f_x = \ a b -> .. } in f_x` (GHC's wrapper for recursive overloaded
        # functions): the arity is that local function's
        inner = body
        while inner[0] == 'let' and inner[3][0] == 'let':
            inner = inner[3]
        known = None
        if inner[0] == 'let' and inner[3][0] == 'v':
            for n, b in inner[2]:
                if n == inner[3][1] and b[0] == 'lam':
                    known = len(strip_lams(b)[0])
        for k in ([known] if known else (1, 2)):
            xs = [f'eta{i}_x{name[:3]}' for i in range(k)]
            probe = Lower.__new__(Lower)
            probe.__dict__.update(self.__dict__, funs=[], local=dict(self.local), listy=set())
            try:
                probe.compile(('app', body, [('v', x) for x in xs]))
            except _Unsupported:
                continue
            self.function(name, xs, ('app', body, [('v', x) for x in xs]))
            return

    def finish(self):
        """A parameter passed on to a callee's list parameter is a list too (fixpoint), then
        each list parameter gets a harmless len() probe so the battery feeds it lists."""
        listy = {n: set(l) for n, _, _, l in self.funs}
        params = {n: ps for n, ps, _, _ in self.funs}

        def calls(t):
            if isinstance(t, tuple):
                if len(t) == 3 and t[0] == 'call' and t[1] in params:
                    yield t[1], t[2]
                for x in t[1:]:
                    yield from calls(x)
            elif isinstance(t, list):
                for x in t:
                    yield from calls(x)
        changed = True
        while changed:
            changed = False
            for n, ps, stmts, _ in self.funs:
                for callee, args in calls(stmts):
                    for k, a in enumerate(args):
                        if (a[:1] == ('var',) and a[1] in ps and a[1] not in listy[n] and k < len(params[callee])
                                and params[callee][k] in listy[callee]):
                            listy[n].add(a[1])
                            changed = True
        out = []
        for n, ps, stmts, _ in self.funs:
            pre = [('expr', ('call', 'len', [('var', p)])) for p in ps if p in listy[n]]
            out.append((n, ps, ('seq', pre + stmts)))
        return out

    def function(self, name, params, body, extra=()):
        self.listy = set()
        saved, saved_alias = dict(self.local), dict(self.alias)
        try:
            stmts, v = self.compile(body)
            stmts = stmts + [('return', v)]
        except _Unsupported as u:
            stmts = [('unsupported', str(u))]
        self.local, self.alias = saved, saved_alias
        self.funs.append((name, list(extra) + params, stmts, set(self.listy)))

    # free variables of a Core expression
    def fv(self, e, bound=frozenset()):
        k = e[0]
        if k == 'v':
            n = e[1]
            return set() if (n in bound or n in self.globals or n in self.local or n.startswith('$')
                             or not re.search(r'_[a-zA-Z0-9]{3,5}$', n)) \
                else {n}
        if k == 'app':
            return self.fv(e[1], bound).union(*(self.fv(a, bound) for a in e[2]))
        if k == 'lam':
            return self.fv(e[2], bound | set(e[1]))
        if k == 'let':
            names = {n for n, _ in e[2]}
            inner = bound | names
            return set().union(*(self.fv(b, inner) for _, b in e[2])) | self.fv(e[3], inner)
        if k == 'case':
            out = self.fv(e[1], bound)
            for pat, body in e[2]:
                out |= self.fv(body, bound | set(pat))
            return out
        if k == 'tuple':
            return set().union(*(self.fv(a, bound) for a in e[1]))
        return set()

    # expression -> (statements, PNF value)
    def compile(self, e):
        k = e[0]
        if k == 'lit':
            return [], (('int', e[1]) if isinstance(e[1], int) else ('num', e[1]))
        if k == 'slit':
            return [], ('str', e[1])
        if k == 'nil':
            return [], ('list', [])
        if k == 'tuple':
            s, vs = self.many(e[1])
            return s, ('tuple', vs)
        if k == 'v':
            return self.var(e[1])
        if k == 'lam':
            raise _Unsupported('lambda_value')
        if k == 'let':
            return self.let(e)
        if k == 'case':
            return self.case(e)
        if k == 'app':
            return self.app(e[1], [a for a in e[2] if not dictish(a)])
        raise _Unsupported('core_' + k)

    def many(self, es):
        stmts, vals = [], []
        for x in es:
            s, v = self.compile(x)
            stmts += s
            vals.append(v)
        return stmts, vals

    def var(self, n):
        if n in ('True', 'otherwise'):
            return [], ('bool', 'true')
        if n == 'False':
            return [], ('bool', 'false')
        if n in ('()', 'void#'):
            return [], ('none',)
        if n in self.alias:
            return self.compile(self.alias[n])
        if n in self.local:
            _, free = self.local[n]
            if not free and n not in self.locfun_arity:
                return [], ('var', n)
            return self.call_local(n, [])
        if n in self.globals:
            return [], ('call', n, [])
        if n in RAISE:
            return [('raise',)], ('none',)
        return [], ('var', n)

    def let(self, e):
        _, is_join, binds, body = e
        stmts = []
        lifted = []
        for n, b in binds:
            if n.startswith('$'):
                continue
            if b[0] == 'lam' and (strip_lams(b)[0] or '_' in b[1]):    # functions, and join points `j _ = ..`
                lifted.append((n, b))
                self.locfun_arity[n] = len(strip_lams(b)[0])
        for n, b in lifted:                       # register first (mutual recursion)
            params, _ = strip_lams(b)
            free = sorted(self.fv(b) - set(params) - {x for x, _ in lifted})
            self.local[n] = (self.fresh_fun(n), free)
        for n, b in lifted:
            lname, free = self.local[n]
            params, fbody = strip_lams(b)
            outer = (self.listy, dict(self.local))
            self.function(lname, params, fbody, extra=free)
            self.listy, _ = outer[0], None
            self.local = outer[1]
        for n, b in binds:
            if n.startswith('$') or n in self.locfun_arity and (n, b) in lifted:
                continue
            if not is_join and self.alias_ok(b):   # pure: a partial application / name is inlined
                self.alias[n] = b
                continue
            self.alias.pop(n, None)
            if b[0] == 'lam' and not strip_lams(b)[0]:
                b = strip_lams(b)[1]
            s, v = self.compile(b)
            stmts += s + [('assign', ('var', n), v)]
        s, v = self.compile(body)
        return stmts + s, v

    def alias_ok(self, b):
        if b[0] == 'v':
            return not re.search(r'_[a-zA-Z0-9]{3,5}$', b[1])           # a global or builtin name
        return (b[0] == 'app' and b[1][0] == 'v' and
                (b[1][1] in BIN or b[1][1] in CALL1 or b[1][1] in CALL2 or b[1][1] in ('.', 'flip', 'rem', 'mod', 'div')
                 or b[1][1] in self.globals) and all(dictish(x) for x in b[2]))

    def fresh_fun(self, n):
        return f'{base(n)}${next(self.tmp)}'

    def call_local(self, n, args):
        lname, free = self.local[n]
        s, vs = self.many(args)
        return s, ('call', lname, [('var', f) for f in free] + vs)

    def case(self, e):
        _, scrut, alts = e
        s, v = self.compile(scrut)
        if v[0] != 'var':
            t = self.fresh()
            s, v = s + [('assign', ('var', t), v)], ('var', t)
        res = self.fresh()
        default = None
        branches = []
        for pat, body in alts:
            con = pat[0] if pat else '__DEFAULT'
            if con == '__DEFAULT' or (len(pat) == 1 and not con[:1].isupper() and con not in ('[]', '()')
                                      and not re.fullmatch(r'-?\d+\#*', con)):
                pre = [] if con == '__DEFAULT' else [('assign', ('var', con), v)]
                default = (pre, body)
                continue
            if con in ('True', 'False'):
                branches.append((v if con == 'True' else ('op', 'not', [v]), [], body))
            elif con == '[]':
                self.mark_list(v)
                branches.append((('op', 'eq', [('call', 'len', [v]), ('int', 0)]), [], body))
            elif con == ':':
                self.mark_list(v)
                h, r = pat[1], pat[2]
                branches.append((('op', 'gt', [('call', 'len', [v]), ('int', 0)]),
                                 [('assign', ('var', h), ('elem', v, ('int', 0))),
                                  ('assign', ('var', r), ('slice', v, ('int', 1), ('none',), ('none',)))], body))
            elif re.fullmatch(r'-?\d+\#*', con):
                branches.append((('op', 'eq', [v, ('int', int(con.rstrip('#')))]), [], body))
            elif con in IDENT or con in ('IP', 'IN') and len(pat) == 2:
                default = ([('assign', ('var', pat[1]), v)], body)
            elif con.startswith('(,') or con == '(':
                names = [x for x in pat[1:] if x not in (',', ')')] if con == '(' else pat[1:]
                default = ([('assign', ('var', x), ('elem', v, ('int', i))) for i, x in enumerate(names)], body)
            elif con == '()':
                default = ([], body)
            else:
                raise _Unsupported('constructor_' + con)
        tree = None
        if default is not None:
            pre, body = default
            sb, vb = self.compile(body)
            tree = ('seq', pre + sb + [('assign', ('var', res), vb)])
        for cond, pre, body in reversed(branches):
            sb, vb = self.compile(body)
            tree = ('if', cond, ('seq', pre + sb + [('assign', ('var', res), vb)]), tree or ('raise',))
        return s + [tree or ('raise',)], ('var', res)

    def mark_list(self, v):
        if v[0] == 'var':
            self.listy.add(v[1])

    def app(self, head, args):
        if head[0] == 'app':                       # ((f a) b)
            return self.app(head[1], [a for a in head[2] if not dictish(a)] + args)
        if head[0] == 'let':
            return self.compile(('let', head[1], head[2], ('app', head[3], args)))
        if head[0] != 'v':
            if head[0] == 'lam':
                return self.beta(head, args)
            raise _Unsupported('computed_head')
        h = head[1]
        if h in self.alias:
            return self.apply(self.alias[h], args)
        if not args:
            return self.var(h)
        if h in ('$', '$!') and len(args) >= 2:
            return self.apply(args[0], args[1:])
        if h == '.' and len(args) >= 3:
            return self.apply(args[0], [('app', args[1], [args[2]])] + args[3:])
        if h in ('quotRem', 'divMod') and len(args) == 2:
            s, (a, b) = self.many(args)
            return s, ('tuple', [('op', 'div', [a, b]), ('op', 'mod', [a, b])])
        if h == 'until' and len(args) == 3:
            s, x = self.compile(args[2])
            acc = self.fresh()
            sc, c = self.apply(args[0], [('v', acc)])
            sf, fx = self.apply(args[1], [('v', acc)])
            if sc:
                raise _Unsupported('until_test_statements')
            return s + [('assign', ('var', acc), x),
                        ('while', ('op', 'not', [c]), ('seq', sf + [('assign', ('var', acc), fx)]))], ('var', acc)
        if h in self.local:
            return self.call_local(h, args)
        if h in self.globals:
            s, vs = self.many(args)
            return s, ('call', h, vs)
        if h in IDENT and len(args) == 1:
            return self.compile(args[0])
        if h == 'seq' and len(args) == 2:
            return self.compile(args[1])
        if h in RAISE:
            return [('raise',)], ('none',)
        if h in BIN and len(args) == 2:
            s, vs = self.many(args)
            if h == '++':
                for x in vs:
                    self.mark_list(x)
            return s, ('op', BIN[h], vs)
        if h == ':' and len(args) == 2:
            s, vs = self.many(args)
            self.mark_list(vs[1])
            return s, ('op', 'add', [('list', [vs[0]]), vs[1]])
        if h == 'negate' and len(args) == 1:
            s, vs = self.many(args)
            return s, ('op', 'neg', vs)
        if h == 'not' and len(args) == 1:
            s, vs = self.many(args)
            return s, ('op', 'not', vs)
        if h in ('even', 'odd') and len(args) == 1:
            s, vs = self.many(args)
            return s, ('op', 'eq', [('op', 'mod', [vs[0], ('int', 2)]), ('int', 0 if h == 'even' else 1)])
        if h in ('succ', 'pred') and len(args) == 1:
            s, vs = self.many(args)
            return s, ('op', 'add' if h == 'succ' else 'sub', [vs[0], ('int', 1)])
        if h in CALL1 and len(args) == 1:
            s, vs = self.many(args)
            if h in ('sum', 'product', 'maximum', 'minimum', 'reverse', 'length', 'genericLength', 'sort'):
                self.mark_list(vs[0])
            return s, ('call', CALL1[h], vs)
        if h in CALL2 and len(args) == 2:
            s, vs = self.many(args)
            return s, ('call', CALL2[h], vs)
        if h == 'lcm' and len(args) == 2:
            s, (a, b) = self.many(args)
            return s, ('op', 'div', [('call', 'abs', [('op', 'mul', [a, b])]), ('call', 'gcd', [a, b])])
        if h in ('head', 'last', 'tail', 'init', 'null') and len(args) == 1:
            s, (q,) = self.many(args)
            self.mark_list(q)
            return s, {'head': ('elem', q, ('int', 0)), 'last': ('elem', q, ('int', -1)),
                       'tail': ('slice', q, ('int', 1), ('none',), ('none',)),
                       'init': ('slice', q, ('int', 0), ('int', -1), ('none',)),
                       'null': ('op', 'eq', [('call', 'len', [q]), ('int', 0)])}[h]
        if h == '!!' and len(args) == 2:
            s, (q, i) = self.many(args)
            self.mark_list(q)
            return s, ('elem', q, i)
        it = self.iterate_of(args[-1]) if args else None
        if h in ('take', 'takeWhile', '!!') and len(args) == 2 and (it or h == 'takeWhile'):
            return self.unfold(h, args, it)
        if h in ('zipWith', 'zip') and len(args) == (3 if h == 'zipWith' else 2):
            s, (q1, q2) = self.many(args[-2:])
            self.mark_list(q1)
            self.mark_list(q2)
            i = self.fresh()
            a1, a2 = ('elem', q1, ('var', i)), ('elem', q2, ('var', i))
            if h == 'zip':
                sb, vb = [], ('tuple', [a1, a2])
            else:
                x1, x2 = self.fresh(), self.fresh()
                sb, vb = self.apply(args[0], [('v', x1), ('v', x2)])
                sb = [('assign', ('var', x1), a1), ('assign', ('var', x2), a2)] + sb
            n = ('call', 'min', [('call', 'len', [q1]), ('call', 'len', [q2])])
            idx = ('call', 'range', [('int', 0), n])
            if not sb:
                return s, ('comp', i, idx, ('bool', 'true'), vb)
            return self.loop_over('map', idx, i, sb, vb, s)
        if h == 'uncurry' and len(args) == 2:
            s, q = self.compile(args[1])
            t = self.fresh()
            sa, va = self.apply(args[0], [('v', t + 'a'), ('v', t + 'b')])
            return s + [('assign', ('var', t + 'a'), ('elem', q, ('int', 0))),
                        ('assign', ('var', t + 'b'), ('elem', q, ('int', 1)))] + sa, va
        if h in ('take', 'drop', 'splitAt') and len(args) == 2:
            s, (n, q) = self.many(args)
            self.mark_list(q)
            if h == 'take':
                return s, ('slice', q, ('int', 0), n, ('none',))
            if h == 'drop':
                return s, ('slice', q, n, ('none',), ('none',))
            return s, ('tuple', [('slice', q, ('int', 0), n, ('none',)), ('slice', q, n, ('none',), ('none',))])
        if h in ('elem', 'notElem') and len(args) == 2:
            s, (x, q) = self.many(args)
            self.mark_list(q)
            return s, ('op', 'in' if h == 'elem' else 'not in', [x, q])
        if h == 'replicate' and len(args) == 2:
            s, (n, x) = self.many(args)
            return s, ('op', 'mul', [('list', [x]), n])
        if h == 'enumFromTo' and len(args) == 2:
            s, (a, b) = self.many(args)
            return s, ('call', 'range', [a, ('op', 'add', [b, ('int', 1)])])
        if h == 'enumFromThenTo' and len(args) == 3:
            s, (a, b, c) = self.many(args)
            step = ('op', 'sub', [b, a])
            return s, ('call', 'range', [a, ('op', 'add', [c, ('cond', ('op', 'gt', [step, ('int', 0)]),
                                                                     ('int', 1), ('int', -1))]), step])
        if h in ('map', 'filter') and len(args) == 2:
            s, q = self.compile(args[1])
            self.mark_list(q)
            x = self.fresh()
            sb, vb = self.apply(args[0], [('v', x)])
            if sb:
                return self.loop_over(h, q, x, sb, vb, s)
            if h == 'map':
                return s, ('comp', x, q, ('bool', 'true'), vb)
            return s, ('comp', x, q, vb, ('var', x))
        if h in ('foldl', "foldl'", 'foldr', 'foldl1', 'foldr1') and len(args) >= 2:
            return self.fold(h, args)
        if h in ('and', 'or', 'all', 'any') and len(args) in (1, 2):
            if len(args) == 1:
                s, (q,) = self.many(args)
                return s, ('call', 'all' if h == 'and' else 'any' if h == 'or' else h, [q])
            s, q = self.compile(args[1])
            x = self.fresh()
            sb, vb = self.apply(args[0], [('v', x)])
            if sb:
                return self.loop_over(h, q, x, sb, vb, s)
            return s, ('call', h, [('comp', x, q, ('bool', 'true'), vb)])
        if h in ('fst', 'snd') and len(args) == 1:
            s, (q,) = self.many(args)
            return s, ('elem', q, ('int', 0 if h == 'fst' else 1))
        if h in ('flip',) and len(args) >= 3:
            return self.apply(args[0], [args[2], args[1]] + args[3:])
        if h in self.params_fn:
            s, vs = self.many(args)
            return s, ('callv', ('var', h), vs)
        if h in ('IP', 'IN') and len(args) == 1:
            return self.compile(args[0])
        raise _Unsupported('function_' + h)

    def iterate_of(self, e):
        """`iterate f x` (dictionaries dropped) -> (f, x), else None."""
        if e[0] == 'app' and e[1] == ('v', 'iterate'):
            xs = [a for a in e[2] if not dictish(a)]
            if len(xs) == 2:
                return xs + [None]
        if e[0] == 'app' and e[1] == ('v', 'map'):              # map g (iterate f x)
            xs = [a for a in e[2] if not dictish(a)]
            if len(xs) == 2:
                inner = self.iterate_of(xs[1])
                if inner and inner[2] is None:
                    return inner[:2] + [xs[0]]
        return None

    def unfold(self, h, args, it):
        """take n (iterate f x) / takeWhile p (iterate f x) / iterate f x !! n / takeWhile p xs:
        explicit loops (the infinite list is never built)."""
        out, cur, cnt = self.fresh(), self.fresh(), self.fresh()
        O, C = ('var', out), ('var', cur)
        if it is None:                                          # takeWhile p xs (finite)
            s, q = self.compile(args[1])
            self.mark_list(q)
            x = self.fresh()
            sp, vp = self.apply(args[0], [('v', x)])
            return s + [('assign', O, ('list', [])),
                        ('for_each', x, q, ('seq', sp + [('if', vp, ('assign', O, ('op', 'add', [O, ('list', [('var', x)])])),
                                                          'break')]))], O
        f, x0, g = it
        s, v0 = self.compile(x0)
        sf, vf = self.apply(f, [('v', cur)])
        stepper = sf + [('assign', C, vf)]
        if g is not None:                                       # elements are g(cur)
            gv = self.fresh()
            sg, vg = self.apply(g, [('v', cur)])
            emit = sg + [('assign', ('var', gv), vg)]
            G = ('var', gv)
        else:
            emit, G = [], C
        if h == '!!':                                           # (iterate f x) !! n
            sn, n = self.compile(args[1])
            return s + sn + [('assign', C, v0), ('for_range', cnt, ('int', 0), n, ('int', 1), ('seq', stepper))] + emit, G
        if h == 'take':
            sn, n = self.compile(args[0])
            return s + sn + [('assign', C, v0), ('assign', O, ('list', [])),
                             ('for_range', cnt, ('int', 0), n, ('int', 1),
                              ('seq', emit + [('assign', O, ('op', 'add', [O, ('list', [G])]))] + stepper))], O
        sp, vp = self.apply(args[0], [('v', gv) if g is not None else ('v', cur)])   # takeWhile p (iterate f x)
        return s + [('assign', C, v0), ('assign', O, ('list', [])),
                    ('while', ('bool', 'true'), ('seq', emit + sp + [('if', vp, ('skip',), 'break'),
                                                                ('assign', O, ('op', 'add', [O, ('list', [G])]))] + stepper))], O

    def loop_over(self, h, q, x, sb, vb, s):
        """map/filter/all/any whose element function needs statements: an explicit loop."""
        acc = self.fresh()
        A = ('var', acc)
        start, step = {'map': (('list', []), [('assign', A, ('op', 'add', [A, ('list', [vb])]))]),
                       'filter': (('list', []), [('if', vb, ('assign', A, ('op', 'add', [A, ('list', [('var', x)])])),
                                                  ('skip',))]),
                       'all': (('bool', 'true'), [('if', vb, ('skip',), ('assign', A, ('bool', 'false')))]),
                       'any': (('bool', 'false'), [('if', vb, ('assign', A, ('bool', 'true')), ('skip',))])}[h]
        self.mark_list(q)
        return s + [('assign', A, start), ('for_each', x, q, ('seq', sb + step))], A

    def beta(self, lam, args):
        params, body = strip_lams(lam)
        if len(params) != len(args):
            raise _Unsupported('partial_lambda')
        stmts = []
        for p, a in zip(params, args):
            s, v = self.compile(a)
            stmts += s + [('assign', ('var', p), v)]
        s, v = self.compile(body)
        return stmts + s, v

    def apply(self, f, args):
        """Apply a function-valued Core expression (operator section, name, lambda) to args."""
        if f[0] == 'lam':
            return self.beta(f, args)
        if f[0] == 'let':
            return self.compile(('let', f[1], f[2], ('app', f[3], args)))
        if f[0] == 'v':
            return self.app(f, args)
        if f[0] == 'app':
            return self.app(f[1], [a for a in f[2] if not dictish(a)] + args)
        raise _Unsupported('apply_' + f[0])

    def fold(self, h, args):
        f, rest = args[0], args[1:]
        if h in ('foldl1', 'foldr1'):
            s, q = self.compile(rest[0])
            init = ('elem', q, ('int', 0 if h == 'foldl1' else -1))
            seq = ('slice', q, ('int', 1), ('none',), ('none',)) if h == 'foldl1' else \
                ('slice', q, ('int', 0), ('int', -1), ('none',))
        else:
            s, init = self.compile(rest[0])
            sq, q = self.compile(rest[1])
            s += sq
            seq = q
        self.mark_list(q)
        acc, x = self.fresh(), self.fresh()
        left = h.startswith('foldl')
        sb, vb = self.apply(f, [('v', acc), ('v', x)] if left else [('v', x), ('v', acc)])
        if not left:
            seq = ('call', 'reverse', [seq])
        loop = [('assign', ('var', acc), init),
                ('for_each', x, seq, ('seq', sb + [('assign', ('var', acc), vb)]))]
        return s + loop, ('var', acc)


class _Unsupported(Exception):
    pass


def haskell_normal_form(path: Path):
    binds = Parser(tokenize(core_text(path))).program()
    low = Lower(binds)
    return low.run()
