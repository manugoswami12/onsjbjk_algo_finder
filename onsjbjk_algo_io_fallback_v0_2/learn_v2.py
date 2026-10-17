"""v0.2 learning: learn algorithm branches from labelled source files, then tag new code.

Source only (stdlib `ast`, `hashlib`); no candidate or training file is executed.
  normalise   AST of each function: no docstrings, raise/validation guards, prints, annotations;
              names renamed by role (P0.. parameters, V0.. locals, SELF own name)  [Baxter et al. 1998]
  fingerprint k-gram hashes of the normalised pre-order token stream, winnowed      [Schleimer et al. 2003, MOSS]
  tag         nearest learned function (Jaccard >= TAU, fixed); its label becomes the Prolog fact
              observed(F, learned(Label), Line), routed by prolog/route_v2.pl
Files labelled null are learned as `none`, so code close to a known non-member stays UNKNOWN.

usage: python learn_v2.py <checkout root> <truth.json> [<truth.json> ...] [--out kb/learned.json]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_KB = ROOT / 'kb' / 'learned.json'
K, WINDOW, TAU, MIN_PRINTS = 5, 4, 0.5, 3
BUILTINS = {'len', 'range', 'enumerate', 'min', 'max', 'abs', 'pow', 'sum', 'sorted', 'reversed',
            'int', 'zip', 'divmod', 'list', 'str', 'bool', 'all', 'any'}
KEEP_CONST = {0, 1, 2, 10, -1}            # ints kept; True/False/None are kept by type below
NOISE_FUNCS = re.compile(r'^(main|benchmark.*|test.*|time.*|_.*|print.*)$')
LABEL = re.compile(r'^[a-z][a-z0-9_]*$')                 # labels become Prolog atoms


def is_guard(stmt):
    """`if <check>: raise ...` validation guards and bare raises/asserts/prints/docstrings."""
    if isinstance(stmt, (ast.Raise, ast.Assert, ast.Pass)):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True
    if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 'print'):
        return True
    return isinstance(stmt, ast.If) and not stmt.orelse and all(isinstance(s, ast.Raise) for s in stmt.body)


def tokens(fn) -> list[str]:
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
    names: dict[str, str] = {p: f'P{i}' for i, p in enumerate(params)}
    names[fn.name] = 'SELF'
    out: list[str] = []

    def name(n):
        if n not in names:
            names[n] = n if n in BUILTINS else f'V{sum(v.startswith("V") for v in names.values())}'
        return names[n]

    def emit(node):
        if isinstance(node, list):
            for x in node:
                if isinstance(x, ast.AST) and not (isinstance(x, ast.stmt) and is_guard(x)):
                    emit(x)
            return
        if isinstance(node, ast.Name):
            out.append(name(node.id))
            return
        if isinstance(node, ast.Constant):
            v = node.value
            keep = v is None or type(v) is bool or (type(v) is int and v in KEEP_CONST)
            out.append(repr(v) if keep else ('S' if isinstance(v, str) else 'C'))
            return
        if isinstance(node, ast.arg):
            out.append(name(node.arg))
            return
        out.append(type(node).__name__)
        if isinstance(node, ast.Attribute):
            out.append('.' + node.attr)
        for field, value in ast.iter_fields(node):
            if field in ('annotation', 'returns', 'type_comment', 'decorator_list', 'ctx', 'type_params'):
                continue
            if isinstance(value, (ast.AST, list)):
                emit(value)
    emit(fn.body)
    return out


def fingerprint(fn) -> set[int]:
    toks = tokens(fn)
    grams = [int(hashlib.md5(' '.join(toks[i:i + K]).encode()).hexdigest()[:12], 16)
             for i in range(max(1, len(toks) - K + 1))]
    if len(grams) <= WINDOW:
        return set(grams)
    prints = set()
    for i in range(len(grams) - WINDOW + 1):          # winnowing: the minimum of every window
        window = grams[i:i + WINDOW]
        prints.add(min(window))
    return prints


def algorithmic(fn) -> bool:
    """Only functions with a loop, comprehension or self-call are learned (helpers/printing are not)."""
    if NOISE_FUNCS.match(fn.name):
        return False
    return any(isinstance(n, (ast.For, ast.While, ast.comprehension)) or
               (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name)
               for n in ast.walk(fn))


def top_functions(source):
    return [f for f in ast.parse(source).body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]


def label_of(value):
    label = value[0] if isinstance(value, list) else value
    label = 'none' if label is None else label
    if not LABEL.match(label):
        raise ValueError('label is not a safe Prolog atom: ' + repr(label))
    return label


def learn(root: Path, truth_files, exclude=()) -> list[dict]:
    kb = []
    for tf in truth_files:
        for rel, value in json.loads(Path(tf).read_text(encoding='utf-8'))['files'].items():
            if rel in exclude:
                continue
            try:
                funcs = top_functions((root / rel).read_text(encoding='utf-8-sig'))
            except (SyntaxError, ValueError, OSError):
                continue
            for fn in funcs:
                prints = fingerprint(fn)
                if algorithmic(fn) and len(prints) >= MIN_PRINTS:
                    kb.append({'label': label_of(value), 'source': f'{rel}::{fn.name}', 'prints': sorted(prints)})
    return kb


def load_kb(path):
    if path is None or not Path(path).exists():
        return []
    return [dict(e, prints=set(e['prints'])) for e in json.loads(Path(path).read_text(encoding='utf-8'))]


def nearest(prints: set[int], kb):
    best, score = None, 0.0
    for entry in kb:
        p = entry['prints'] if isinstance(entry['prints'], set) else set(entry['prints'])
        s = len(prints & p) / len(prints | p) if prints | p else 0.0
        if s > score:
            best, score = entry, s
    return best, score


def tag(source: str, analyses, kb) -> None:
    """Add observed learned(Label) evidence to each analysis whose function is close to a learned one."""
    if not kb:
        return
    for fn, analysis in zip(top_functions(source), analyses):
        prints = fingerprint(fn)
        if len(prints) < MIN_PRINTS:
            continue
        entry, score = nearest(prints, kb)
        if entry and score >= TAU and entry['label'] != 'none':
            analysis.add(f"learned({entry['label']})", fn.lineno)
            analysis.outputs.append(f"learned match {entry['source']} (Jaccard {score:.2f})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('root', type=Path)
    p.add_argument('truth', nargs='+')
    p.add_argument('--out', type=Path, default=DEFAULT_KB)
    a = p.parse_args()
    kb = learn(a.root, a.truth)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(kb, indent=0), encoding='utf-8')
    labels = {}
    for e in kb:
        labels[e['label']] = labels.get(e['label'], 0) + 1
    print(f'LEARNED {len(kb)} functions -> {a.out}:', ', '.join(f'{k}={v}' for k, v in sorted(labels.items())))


if __name__ == '__main__':
    main()
