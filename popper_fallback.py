"""v0.2 SEPARATE Popper fallback: inductive logic programming (Popper, Cropper & Morel 2021)
learns one Prolog rule set per branch from labelled files; the rules are applied only to
files the v0.2 system (witnesses + learners) leaves UNKNOWN.

  features   per file, generic static facts (stdlib `ast`; nothing executed): the v0.2 witness facts
             plus AST operator/constant/call/control features of its top-level functions
  learn      for each branch L: pos = training files labelled L; neg = files with an unrelated label
             (same-lineage labels are neither); bias = unary features seen in a positive;
             Popper (no noise: no negative may be covered) -> rules  L(A) :- f1(A), f2(A).
  apply      a rule fires when its body features are all present; the label becomes
             observed(F, learned(L), Line) for prolog/route_v2.pl

usage: python popper_fallback.py learn <checkout root> <truth.json>... [--out kb/popper_rules.json]
Requires Popper v3.1.0 (git clone; POPPER_DIR env var or --popper) with clingo, pyswip, python-sat.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from static_trace_v2 import analyze_source

ROOT = Path(__file__).resolve().parent
DEFAULT_RULES = ROOT / 'kb' / 'popper_rules.json'
OPS = {ast.Add: 'add', ast.Sub: 'sub', ast.Mult: 'mul', ast.Div: 'div', ast.FloorDiv: 'fdiv', ast.Mod: 'mod',
       ast.Pow: 'pow', ast.BitAnd: 'band', ast.BitOr: 'bor', ast.BitXor: 'bxor', ast.RShift: 'rsh', ast.LShift: 'lsh'}
CMPS = {ast.Eq: 'eq', ast.NotEq: 'ne', ast.Lt: 'lt', ast.LtE: 'le', ast.Gt: 'gt', ast.GtE: 'ge', ast.In: 'in',
        ast.NotIn: 'notin', ast.Is: 'is', ast.IsNot: 'isnot'}
CONSTS = {0: '0', 1: '1', 2: '2', 3: '3', 10: '10', -1: 'm1'}
CALLS = {'sum', 'len', 'min', 'max', 'range', 'sorted', 'reversed', 'abs', 'pow', 'int', 'str', 'ord', 'chr',
         'divmod', 'enumerate', 'zip', 'map', 'filter', 'all', 'any', 'list', 'set', 'dict', 'isqrt', 'sqrt',
         'gcd', 'append', 'pop', 'insert', 'extend', 'reverse', 'sort', 'join', 'split', 'index', 'count',
         'lower', 'upper', 'isdigit', 'isalpha', 'factorial', 'reduce', 'lcm', 'heappush', 'heappop'}
SAFE = re.compile(r'^[a-z][a-z0-9_]*$')
LINEAGE = {'comparison_driven_reordering': {'sequence_rearrangement', 'shift_insertion', 'selection_exchange'},
           'shift_insertion': {'comparison_driven_reordering', 'sequence_rearrangement'},
           'selection_exchange': {'comparison_driven_reordering', 'sequence_rearrangement'},
           'sequence_rearrangement': {'comparison_driven_reordering', 'shift_insertion', 'selection_exchange'},
           'indexed_lookup': {'interval_lookup', 'membership_lookup'}, 'interval_lookup': {'indexed_lookup', 'membership_lookup'},
           'membership_lookup': {'indexed_lookup', 'interval_lookup'},
           'aggregate': {'element_accumulation', 'extremum_search'}, 'element_accumulation': {'aggregate'},
           'extremum_search': {'aggregate'},
           'recurrence': {'fibonacci_like', 'euclid_like', 'factorial_like', 'series_sum'},
           'fibonacci_like': {'recurrence'}, 'euclid_like': {'recurrence'}, 'factorial_like': {'recurrence'},
           'series_sum': {'recurrence'},
           'number_property': {'digit_processing', 'divisor_search', 'collatz_like'},
           'digit_processing': {'number_property'}, 'divisor_search': {'number_property', 'sieve_like'},
           'collatz_like': {'number_property'}, 'sieve_like': {'marking', 'divisor_search'}, 'marking': {'sieve_like'},
           'palindrome_check': {'symmetric_compare'}, 'symmetric_compare': {'palindrome_check'}}


def function_features(fn) -> set[str]:
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.While):
            out.add('loop_while')
        elif isinstance(n, ast.For):
            out.add('loop_for')
        elif isinstance(n, (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)):
            out.add('comprehension')
        elif isinstance(n, (ast.Yield, ast.YieldFrom)):
            out.add('yields')
        elif isinstance(n, ast.BinOp) and type(n.op) in OPS:
            r = n.right
            k = CONSTS.get(r.value) if isinstance(r, ast.Constant) and type(r.value) is int else None
            out.add(f'op_{OPS[type(n.op)]}_' + (k if k else ('k' if isinstance(r, ast.Constant) else 'v')))
        elif isinstance(n, ast.AugAssign) and type(n.op) in OPS:
            out.add(f'aug_{OPS[type(n.op)]}')
        elif isinstance(n, ast.Compare):
            for op, c in zip(n.ops, n.comparators):
                if type(op) in CMPS:
                    k = CONSTS.get(c.value) if isinstance(c, ast.Constant) and type(c.value) is int else None
                    out.add(f'cmp_{CMPS[type(op)]}' + (f'_{k}' if k else ''))
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name == fn.name:
                out.add('self_call')
            elif name in CALLS:
                out.add('call_' + name)
        elif isinstance(n, ast.Subscript):
            if isinstance(n.ctx, ast.Store):
                out.add('subscript_store')
            if isinstance(n.slice, ast.Slice):
                out.add('slice_step_m1' if n.slice.step is not None and ast.unparse(n.slice.step) == '-1' else 'slice')
            elif isinstance(n.slice, ast.UnaryOp) or (isinstance(n.slice, ast.Constant) and n.slice.value == -1):
                out.add('negative_index')
        elif isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple) and isinstance(n.value, ast.Tuple):
            out.add('tuple_assign')
        elif isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and type(n.value.value) is bool:
            out.add('return_bool')
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value == '':
            out.add('empty_string')
    if sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name for n in ast.walk(fn)) >= 2:
        out.add('self_call_2')
    return out


def file_features(source: str) -> set[str]:
    tree = ast.parse(source)
    funcs = [f for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
    feats = set()
    for fn in funcs:
        feats |= function_features(fn)
    for a in analyze_source(source):
        feats |= {'w_' + e for e in a.evidence if SAFE.match(e)}
    return {f for f in feats if SAFE.match(f)}


def first_label(value):
    return None if value is None else (value[0] if isinstance(value, list) else value)


def run_popper(popper: Path, label: str, pos: list[set], neg: list[set], timeout: int):
    preds = sorted(set().union(*pos)) if pos else []
    if not pos or not preds:
        return []
    with tempfile.TemporaryDirectory(prefix='v02_popper_') as td:
        d = Path(td)
        (d / 'exs.pl').write_text(''.join(f'pos(target(p{i})).\n' for i in range(len(pos))) +
                                  ''.join(f'neg(target(n{i})).\n' for i in range(len(neg))), encoding='utf-8')
        bk = [f'f_{f}(p{i}).' for i, fs in enumerate(pos) for f in sorted(fs)] + \
             [f'f_{f}(n{i}).' for i, fs in enumerate(neg) for f in sorted(fs) if f in preds]
        (d / 'bk.pl').write_text(':- discontiguous ' + ', '.join(f'f_{p}/1' for p in preds) + '.\n' +
                                 '\n'.join(sorted(bk)) + '\n', encoding='utf-8')
        (d / 'bias.pl').write_text('head_pred(target,1).\n' + ''.join(f'body_pred(f_{p},1).\n' for p in preds) +
                                   'max_vars(1).\n', encoding='utf-8')
        proc = subprocess.run([sys.executable, str(popper / 'popper.py'), str(d), '--timeout', str(timeout),
                               '--max-body', '3', '-q'], capture_output=True, text=True, timeout=timeout + 60,
                              stdin=subprocess.DEVNULL)
    rules = []
    for line in proc.stdout.splitlines():
        m = re.match(r'^target\(A\)\s*:-\s*(.+)\.$', line.strip())
        if m:
            body = [b.strip() for b in re.findall(r'f_([a-z0-9_]+)\(A\)', m.group(1))]
            if body:
                rules.append(sorted(body))
    return rules


def learn(root: Path, truth_files, popper: Path, timeout=60) -> dict:
    data = []
    for tf in truth_files:
        for rel, value in json.loads(Path(tf).read_text(encoding='utf-8'))['files'].items():
            try:
                data.append((first_label(value), set(value) if isinstance(value, list) else {value},
                             file_features((root / rel).read_text(encoding='utf-8-sig'))))
            except (SyntaxError, ValueError, OSError):
                continue
    labels = sorted({l for l, _, _ in data if l})
    out = {}
    for label in labels:
        related = LINEAGE.get(label, set()) | {label}
        pos = [f for l, _, f in data if l == label]
        neg = [f for l, accepted, f in data if l != label and not (accepted & related) and l not in related]
        rules = run_popper(popper, label, pos, neg, timeout)
        if rules:
            out[label] = rules
        print(f'POPPER {label}: pos={len(pos)} neg={len(neg)} rules={rules}', flush=True)
    return out


def load_rules(path):
    return json.loads(Path(path).read_text(encoding='utf-8')) if path and Path(path).exists() else {}


def labels_for(source: str, rules: dict) -> set[str]:
    try:
        feats = file_features(source)
    except (SyntaxError, ValueError):
        return set()
    return {label for label, body_list in rules.items() if any(set(b) <= feats for b in body_list)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cmd', choices=['learn'])
    p.add_argument('root', type=Path)
    p.add_argument('truth', nargs='+')
    p.add_argument('--out', type=Path, default=DEFAULT_RULES)
    p.add_argument('--popper', type=Path, default=Path(os.environ.get('POPPER_DIR', 'Popper')))
    p.add_argument('--timeout', type=int, default=60)
    a = p.parse_args()
    rules = learn(a.root, a.truth, a.popper, a.timeout)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rules, indent=1), encoding='utf-8')
    print(f'POPPER RULES: {sum(map(len, rules.values()))} rules for {len(rules)} branches -> {a.out}')


if __name__ == '__main__':
    main()
