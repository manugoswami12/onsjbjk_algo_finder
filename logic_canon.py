"""The traced-logic tier on the tree's facts, in a canonical form (doc 04 section 19.13). The exact-logic tier
(eval_ta.TaLogic, AP13's learn-dir and scan) learned and scanned AP13's own facts (cli.facts_text), an older
conversion than the one the tree reads: TheAlgorithms' perfect(), sum(i for i in range(...) if n % i == 0), became
sum(var, other(for_in_clause), other(if_clause)), a trivial pattern, so no perfect-number logic was ever learned.
  facts      Python, C and Haskell files give the tree's facts (learn_facts.tree_facts) to AP13's learn and scan;
             Common Lisp keeps its own fact form
  canonical  a learned pattern is stored without what is not the algorithm's logic, written the same in every
             language: an input check (a guard `p <op> k`, k a constant, on every statement of the pattern) is the
             function's context, as families_v02.pl continuation_guard treats it; the bound of range(lo, hi) is how far
             the search runs, not what it computes (n // 2 + 1 or n - 1): a variable of the pattern
Used by eval_ta.CanonicalLogic, the second view of the traced-logic tier: AP13's literal facts are tried first
(specific before general); the canonical view only names a file the literal view names nothing for.
  facts_of(path)        (language, the tree's facts), or None
  canonical_lines(ls)   AP13 learn output with every pattern canonical
"""
from __future__ import annotations

import re
from pathlib import Path

LANGS = {'.py': 'python', '.c': 'c', '.hs': 'haskell'}
_installed = False


def split_top(text: str) -> list[str]:
    """The comma-separated items of text at bracket depth 0."""
    out, depth, cur, quote = [], 0, [], False
    for ch in text:
        if ch == "'":
            quote = not quote
        if not quote:
            if ch in '([':
                depth += 1
            elif ch in ')]':
                depth -= 1
            elif ch == ',' and depth == 0:
                out.append(''.join(cur).strip())
                cur = []
                continue
        cur.append(ch)
    if ''.join(cur).strip():
        out.append(''.join(cur).strip())
    return out


def closing(text: str, start: int) -> int:
    """The index just after the bracket closing the one at start."""
    depth, quote = 0, False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "'":
            quote = not quote
        elif not quote and ch in '([':
            depth += 1
        elif not quote and ch in ')]':
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def range_bounds(rel: str, names: dict) -> str:
    """call(range, [Lo, Hi]) with Hi a variable of the pattern (the same Hi term, the same variable)."""
    out, i = [], 0
    while True:
        j = rel.find('call(range, [', i)
        if j < 0:
            out.append(rel[i:])
            return ''.join(out)
        k = j + len('call(range, ')
        end = closing(rel, k)
        args = split_top(rel[k + 1:end - 1])
        if len(args) == 2:
            var = names.setdefault(args[1], f'Hi{len(names) + 1}')
            out.append(rel[i:k] + '[' + args[0] + ', ' + var + ']')
        else:
            out.append(rel[i:end])
        i = end


CHECK = re.compile(r"^nguard\((\w+), (op\((?:ge|gt|le|lt|eq), \[(?:int\(-?\d+\), var\(\w+\)|var\(\w+\), int\(-?\d+\))\]\)), (true|false)\)$")


def canonical(clause: str) -> str:
    """The reference clause without input checks, its range bounds variables."""
    m = re.match(r'^reference\((.*)\)\.\s*$', clause.strip(), re.S)
    if not m:
        return clause
    parts = split_top(m.group(1))
    if len(parts) != 4 or not parts[2].startswith('['):
        return clause
    rels = split_top(parts[2][1:-1])
    stmts = {split_top(r[r.index('(') + 1:-1])[0] for r in rels
             if r.split('(', 1)[0] in ('cret', 'value', 'nguard', 'guard', 'stmt_call', 'call_at')}
    checks = {}
    for r in rels:
        c = CHECK.match(r)
        if c:
            checks.setdefault((c.group(2), c.group(3)), set()).add(c.group(1))
    context = {key for key, at in checks.items() if at >= stmts - {None}}
    kept = [r for r in rels if not (CHECK.match(r) and (CHECK.match(r).group(2), CHECK.match(r).group(3)) in context)]
    names = {}
    kept = [range_bounds(r, names) for r in kept]
    if kept == rels:
        return clause
    return f'reference({parts[0]}, {parts[1]}, [{", ".join(kept)}], {parts[3]}).\n'


def canonical_terms(clauses: list[str]) -> list[str]:
    """The clauses in canonical form (prolog/logic_canon.pl, one Prolog call); unchanged if that fails."""
    if not clauses:
        return []
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix='v02_canon_') as td:
        src, dst = Path(td) / 'in.pl', Path(td) / 'out.pl'
        src.write_text('\n'.join(c.rstrip() for c in clauses) + '\n', encoding='utf-8')
        done = subprocess.run(['swipl', '-q', '-g', 'canon_main', '-t', 'halt', str(CANON_PL), '--', str(src), str(dst)],
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if done.returncode != 0 or not dst.is_file():
            return clauses
        text = dst.read_text(encoding='utf-8')
    out = [c.strip() + '\n' for c in re.split(r'(?m)^(?=reference\()', text) if c.strip()]
    return out if len(out) == len(clauses) else clauses


CANON_PL = Path(__file__).resolve().parent / 'prolog' / 'logic_canon.pl'


def facts_of(path: Path):
    """(language, the tree's facts) of a Python, C or Haskell file, or None (another language, or no facts)."""
    import learn_facts
    lang = LANGS.get(Path(path).suffix)
    if lang is None:
        return None
    kind, text = learn_facts.tree_facts(Path(path))
    return (lang, text) if kind == 'ap13' and text.strip() else None


def canonical_lines(lines: list[str]) -> list[str]:
    """AP13 learn output with the clause of every LEARN block in canonical form (prolog/logic_canon.pl)."""
    blocks, inside = [], False
    for line in lines:
        if line.startswith('LEARN|'):
            inside, block = True, []
        elif inside and line == 'END':
            blocks.append('\n'.join(block))
            inside = False
        elif inside:
            block.append(line)
    canon, out, k, inside = canonical_terms(blocks), [], 0, False
    for line in lines:
        if line.startswith('LEARN|'):
            out.append(line)
            inside = True
        elif inside and line == 'END':
            out += canon[k].rstrip('\n').split('\n') + [line]
            k, inside = k + 1, False
        elif not inside:
            out.append(line)
    return out
