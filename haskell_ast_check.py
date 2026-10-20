"""GHC's own parser checks the structure facts of a Haskell file (doc 04 section 19.10). tree-sitter's Haskell
grammar recovers from what it cannot read and may report a function that is not one (sieve-of-eratosthenes-15.hs: a
guard `| x <= y = ...` read as the definitions `<=` and `otherwise`). GHC parses the module (ghc -fno-code
-ddump-parsed-ast: parsed only, nothing compiled, linked or run), prepared as for the Core path
(haskell_core_pnf.prepared_source); every function binding it sees, local ones included, is a function of the file.
  check(facts, path)   the facts without those of a function GHC does not define; unchanged when GHC cannot parse
                       the file (nothing to check against)
Names are compared as the lowerer writes them: the last segment of outer.inner, a $suffix dropped, \\' as ',
(op) as op. A parameter count above GHC's is the lowerer's lambda lifting (free variables as parameters), not a fault.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from haskell_core_pnf import prepared_source

TOKEN = re.compile(r'\{[^{}]*\}|[()\[\]]|[^\s()\[\]{}]+')
MARK = '==================== Parser AST ===================='


def tree(text):
    """The dump (showAstData: parentheses, lists, {..} fields) as nested lists, '(' or '[' first."""
    stack, cur = [], []
    for tok in TOKEN.findall(text):
        if tok in '([':
            stack.append(cur)
            cur = [tok]
        elif tok in ')]':
            node, cur = cur, stack.pop()
            cur.append(node)
        elif tok != ',':
            cur.append(tok.rstrip(','))
    return cur


def head(n):
    return n[1] if isinstance(n, list) and len(n) > 1 and isinstance(n[1], str) else None


def occ(n):
    if isinstance(n, str):
        m = re.match(r'\{OccName: (.*)\}$', n)
        return m.group(1).strip() if m else None
    for c in n:
        r = occ(c)
        if r:
            return r
    return None


def bindings(n, out):
    """The names of every FunBind (a function or a value binding) under n."""
    if not isinstance(n, list):
        return
    if head(n) == 'FunBind' and len(n) > 3:
        name = occ(n[3])
        if name:
            out.add(name)
    for c in n:
        bindings(c, out)


def ghc_functions(path: Path, timeout=60):
    """The names GHC's parser binds in the file, or None when it cannot parse it."""
    with tempfile.TemporaryDirectory(prefix='v02_ghcast_') as td:
        f = Path(td) / 'Main.hs'
        f.write_text(prepared_source(path), encoding='utf-8')
        try:
            proc = subprocess.run(['ghc', '-fno-code', '-ddump-parsed-ast', str(f)], capture_output=True, text=True,
                                  timeout=timeout, cwd=td, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            return None
    if MARK not in proc.stdout:
        return None
    out = set()
    bindings(tree(proc.stdout.split(MARK, 1)[1]), out)
    return out


def written_name(name: str) -> str:
    base = name.split('.')[-1].split('$')[0].replace("\\'", "'").replace("\\\\", "\\")
    return base[1:-1] if base.startswith('(') and base.endswith(')') else base


FUNC = re.compile(r"^func\('([^']+)','((?:[^'\\]|\\.)*)'")
STMT = re.compile(r"^stmt\('([^']+)','([^']+)'")
IDS = re.compile(r"'([fs]\d+(?:_\w+)?)'")


def check(facts: str, path: Path) -> str:
    known = ghc_functions(path)
    if known is None or not facts.strip():
        return facts
    lines = facts.splitlines()
    dropped = {m.group(1) for m in map(FUNC.match, lines)
               if m and m.group(2) != '<toplevel>' and written_name(m.group(2)) and written_name(m.group(2)) not in known}
    if not dropped:
        return facts
    dropped |= {m.group(1) for m in map(STMT.match, lines) if m and m.group(2) in dropped}
    return '\n'.join(line for line in lines if not set(IDS.findall(line)) & dropped) + '\n'
