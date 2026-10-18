"""Common Lisp -> ECL C -> v0.2 facts -> prolog/route_v2.pl (the same branches as for Python).

ECL compiles every Lisp function to C of a fixed, standard shape (runtime calls ecl_minus/ecl_times,
temporaries T0.., `(ecl_floor2(a,b),values[1])` for the remainder, labels + goto for loops,
ecl_aref_unsafe / ecl_aset_unsafe for vector access). Each witness below recognises one such shape
and emits the v0.2 fact of the same meaning; nothing is executed (ECL only compiles).
"""
from __future__ import annotations

import re
from pathlib import Path

from ecl_filter import ecl_c
from static_trace import Analysis

FUN = re.compile(r'^static cl_object (L\d+([\w]*))\(([^)]*)\)\s*\{', re.M)
ASSIGN = re.compile(r'\b(T\d+|v\d+\w*)\s*=\s*([^;]+);')
REM = r'\(ecl_floor2\((\w+),([^()]+|ecl_make_fixnum\(\d+\))\),cl_env_copy->values\[1\]\)'


def bodies(c_text):
    for m in FUN.finditer(c_text):
        depth, i = 1, m.end()
        while depth and i < len(c_text):
            depth += c_text[i] == '{'
            depth -= c_text[i] == '}'
            i += 1
        params = [p.split()[-1] for p in m.group(3).split(',') if p.strip()]
        yield m.group(1), m.group(2), params, c_text[m.end():i - 1], c_text[:m.start()].count('\n') + 1


def backward_goto(body):
    """A loop: `goto Lk` after the label `Lk:` (ECL's only way to loop)."""
    for g in re.finditer(r'goto (L\d+);', body):
        lab = body.find(g.group(1) + ':')
        if 0 <= lab < g.start():
            return True
    return False


def witnesses(cname, params, body):
    facts = set()
    defs = {a: e.strip() for a, e in ASSIGN.findall(body)}        # temporaries: last definition
    calls = re.findall(rf'(T\d+|v\d+\w*)\s*=\s*{cname}\((T\d+|v\d+\w*)\);', body)
    minus = {t: e for t, e in defs.items() if re.fullmatch(r'ecl_minus\((\w+),ecl_make_fixnum\((\d)\)\)', e)}
    for p in params:
        # n * f(n - 1)
        for res, arg in calls:
            if minus.get(arg) == f'ecl_minus({p},ecl_make_fixnum(1))' and \
                    re.search(rf'ecl_times\(({p},{res}|{res},{p})\)', body):
                facts.add('linear_self_product')
        # f(n - 1) + f(n - 2)
        ks = {minus.get(arg) for _, arg in calls}
        if {f'ecl_minus({p},ecl_make_fixnum(1))', f'ecl_minus({p},ecl_make_fixnum(2))'} <= ks:
            res = [r for r, _ in calls]
            if len(res) >= 2 and re.search(rf'ecl_plus\(({res[0]},{res[1]}|{res[1]},{res[0]})\)', body):
                facts.update({'self_calls_minus_one_minus_two', 'double_self_call'})
    loop = backward_goto(body)
    for a, b in re.findall(REM, body):
        if loop and b == 'ecl_make_fixnum(10)' and re.search(rf'\b{a}\s*=\s*ecl_floor2\({a},ecl_make_fixnum\(10\)\)', body):
            facts.add('digit_decomposition')
        if loop and not b.startswith('ecl_make_fixnum') and a in params + list(defs) and b in params:
            facts.add('modulo_recurrence')
        if loop and re.search(rf'ecl_zerop\({re.escape("(ecl_floor2(" + a + "," + b + "),cl_env_copy->values[1])")}\)', body):
            facts.add('divisor_test_in_loop')
    # Euclid by recursion: return f(b, a mod b)
    if len(params) == 2 and re.search(rf'{cname}\({params[1]},\w+\)', body) and re.search(
            REM.replace(r'(\w+)', params[0], 1), body):
        facts.add('modulo_recurrence')
    # vector writes on an input: exchange = two writes storing crosswise reads
    sets = re.findall(r'ecl_aset_unsafe\(T\d+,\w+,(\w+)\);', body)
    reads = {v for v, _ in re.findall(r'\b(v\d+\w*|T\d+)\s*=\s*ecl_aref_unsafe\((T\d+),\w+\);', body)}
    if len(sets) >= 2 and len(set(sets) & reads) >= 2 and any(f'= {p};' in body for p in params):
        facts.update({'input_sequence_mutated', 'element_exchange'})
        cmp = re.search(r'if \((?:Null\(ecl_function_dispatch\(cl_env_copy,\w+\)\(2, T\d+, T\d+\)\)|'
                        r'!?\(?ecl_(?:lower|greater|lowereq|greatereq)\(T\d+,T\d+\)\)?)\) \{ goto (L\d+); \}', body)
        if cmp and body.find(cmp.group(1) + ':') > body.find('ecl_aset_unsafe'):
            facts.add('comparison_controls_exchange')
    return facts


def analyse_lisp(path: Path):
    """[(Lisp function name, Analysis with the facts)] for every function of the file."""
    out = []
    for cname, lname, params, body, line in bodies(ecl_c(path)):
        a = Analysis(lname, params)
        for f in sorted(witnesses(cname, params, body)):
            a.add(f, line)
        out.append((lname, a))
    return out
