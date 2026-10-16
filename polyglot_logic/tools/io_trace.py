"""AP13 v4 (doc 10): run the Prolog normal form of every function on a fixed input
battery; return its input->output behaviour and its logic traces.

  logical input   lists and integers; a C-style length parameter (n, len, size, ...) gets
                  the length of the preceding list, so sort(a, n) and sort(a) take the same input
  effective output  the returned value, or (in-place functions) the final input lists
  trace           writes to input positions w(ListParam, Index, Value), fingerprinted
"""
from __future__ import annotations

import random
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_run import PROLOG_DIR, ToolError, swipl  # noqa: E402
from to_prolog import normal_form, render  # noqa: E402
from fact_io import term  # noqa: E402

LENGTH_NAMES = {'n', 'len', 'length', 'size', 'count', 'num', 'sz', 'high', 'hi', 'right', 'last', 'end'}
LOW_NAMES = {'low', 'lo', 'left', 'first', 'start', 'begin', 'l'}


def _uses(body, p):
    """How a parameter is used: 'list' if indexed, measured or iterated."""
    found = []

    def walk(t):
        if isinstance(t, tuple):
            if t[:1] == ('elem',) and t[1] == ('var', p):
                found.append('list')
            if t[:2] == ('call', 'len') and t[2] and t[2][0] == ('var', p):
                found.append('list')
            if t[:1] == ('for_each',) and t[2] == ('var', p):
                found.append('list')
            for x in t[1:]:
                walk(x)
        elif isinstance(t, list):
            for x in t:
                walk(x)
    walk(body)
    return 'list' if found else 'int'


def kinds(params, body):
    out = []
    for p in params:
        k = _uses(body, p)
        if k == 'int' and out and 'list' in out and p.lower() in LENGTH_NAMES:
            k = 'len'
        if k == 'int' and out and 'list' in out and p.lower() in LOW_NAMES:
            k = 'zero'
        out.append(k)
    return tuple(out)


def logical(ks):
    """The logical signature: what a caller really provides."""
    return tuple(k for k in ks if k in ('list', 'int'))


def battery(sig, seed=13):
    """Deterministic logical inputs for a logical signature."""
    rnd = random.Random(seed)
    lists = [[], [1], [2, 1], [3, 1, 2], [1, 2, 3, 4], [5, 4, 3, 2, 1], [4, 1, 3, 1, 2],
             [rnd.randint(0, 20) for _ in range(6)], [rnd.randint(0, 20) for _ in range(8)],
             [7, 7, 7], [9, 0, 8, 1, 7, 2]]
    ints = list(range(0, 41)) + [64, 97, 100, 121, 128, 496]
    if sig == ('list',):
        return [[x] for x in lists]
    if sig == ('int',):
        return [[i] for i in ints]
    if sig == ('int', 'int'):
        return [[a, b] for a, b in [(12, 18), (7, 5), (0, 4), (21, 6), (100, 75), (13, 13), (1, 9), (48, 36)]]
    if sig == ('list', 'int'):                       # search-like: sorted list, present and absent targets
        out = []
        for L in ([1, 3, 5, 7, 9, 11], [2, 4, 6, 8], [1], [0, 5, 10, 15, 20, 25, 30]):
            out += [[L, L[0]], [L, L[-1]], [L, L[len(L) // 2]], [L, -1], [L, 100]]
        return out
    if sig == ('list', 'int', 'int'):
        return [[L, a, b] for L, a, b in [([1, 3, 5, 7, 9], 0, 4), ([5, 1, 4], 0, 2), ([2, 2, 1], 1, 2),
                                         ([9, 8, 7, 6, 5, 4], 1, 4), ([1], 0, 0), ([3, 1, 2], 0, 2)]]
    if sig and all(k == 'int' for k in sig):        # any arity: every position varies
        r = random.Random(seed + len(sig))
        return [[r.choice([0, 1, 2, 3, 4, 5, 7, 10]) for _ in sig] for _ in range(14)]
    if sig == ('list', 'list'):
        return [[a, b] for a, b in [([1, 3, 5], [2, 4, 6]), ([], [1]), ([1, 2], []), ([5, 1], [1, 5]),
                                    ([1, 2, 3], [1, 2, 3])]]
    return []


def concrete(ks, logical_args):
    """Map logical inputs onto the function's own parameters (length / low parameters derived)."""
    it = iter(logical_args)
    out, last_list = [], None
    for k in ks:
        if k in ('list', 'int'):
            v = next(it)
            out.append(v)
            if k == 'list':
                last_list = v
        elif k == 'len':
            out.append(len(last_list) if last_list is not None else 0)
        elif k == 'zero':
            out.append(0)
    return out


_RES = re.compile(r'^RES\|(\d+)\|(ok|err)\|(.*)$')


SIGS = [('list',), ('int',), ('int', 'int'), ('list', 'int'), ('list', 'list'), ('list', 'int', 'int'),
        ('int', 'int', 'int')]


def run_native_prolog(path: Path, timeout=120):
    """A Prolog source is its own normal form: every predicate is tried as a function
    (inputs + one output argument) and as a test (inputs only) on each battery signature."""
    with tempfile.TemporaryDirectory(prefix='ap13_v4p_') as td:
        jf = Path(td) / 'jobs.pl'
        jf.write_text('', encoding='utf-8')
        preds = [tuple(l.split('|')[1:3]) for l in
                 swipl('native_main', [PROLOG_DIR / 'native_main.pl'], [str(path.resolve()), str(jf)], timeout)
                 if l.startswith('PRED|')]
        jobs, slots = [], []
        for name, ar in preds:
            ar = int(ar)
            for sig in SIGS:
                for mode, need in (('out', ar - 1), ('test', ar)):
                    if len(sig) != need:
                        continue
                    key = f'{name}/{ar}@{mode}:' + ','.join(sig)
                    slots.append((key, sig))
                    for x in battery(sig):
                        jobs.append((len(jobs), key, name, mode, x))
        if not jobs:
            return {}
        jf.write_text(''.join(f"job({i},{term(n)},{m},{prolog_value(a)}).\n" for i, _, n, m, a in jobs),
                      encoding='utf-8')
        lines = swipl('native_main', [PROLOG_DIR / 'native_main.pl'], [str(path.resolve()), str(jf)], timeout)
    by_id = {int(m.group(1)): (m.group(2), m.group(3)) for m in map(_RES.match, lines) if m}
    info = {}
    for key, sig in slots:
        info[key] = {'kinds': sig, 'sig': sig, 'inputs': battery(sig), 'runs': [], 'unsupported': False}
    for i, key, _, _, _ in jobs:
        st, rest = by_id.get(i, ('err', 'no result'))
        info[key]['runs'].append((st == 'ok', rest, None))
    return {k: d for k, d in info.items() if sum(r[0] for r in d['runs']) >= 0.7 * len(d['runs'])}


def run_functions(path: Path, functions=None, timeout=120):
    """{function: {'kinds', 'sig', 'runs': [(ok, output, trace_hash) ...], 'error'}}"""
    lang, funs = normal_form(path)
    if lang == 'prolog':
        return run_native_prolog(path, timeout)
    if not funs:
        return {}
    pnf = ["pnf_lang(%s)." % term(lang)] + \
          [f"pnf_fun({term(n)},{term(list(ps))},{render(b)})." for n, ps, b in funs]
    info, jobs = {}, []
    for name, params, body in funs:
        if functions and name not in functions:
            continue
        ks = kinds(params, body)
        sig = logical(ks)
        inputs = battery(sig)
        info[name] = {'kinds': ks, 'sig': sig, 'inputs': inputs, 'runs': [], 'unsupported': has_unsupported(body)}
        for x in inputs:
            jobs.append((len(jobs), name, concrete(ks, x)))
    if not jobs:
        return info
    with tempfile.TemporaryDirectory(prefix='ap13_v4_') as td:
        pf, jf = Path(td) / 'pnf.pl', Path(td) / 'jobs.pl'
        pf.write_text('\n'.join(pnf) + '\n', encoding='utf-8')
        jf.write_text(''.join(f"job({i},{term(n)},{prolog_value(a)}).\n" for i, n, a in jobs), encoding='utf-8')
        lines = swipl('run_main', [PROLOG_DIR / 'run_main.pl'], [str(pf), str(jf)], timeout=timeout)
    by_id = {}
    for line in lines:
        m = _RES.match(line)
        if m:
            by_id[int(m.group(1))] = (m.group(2), m.group(3))
    for i, name, args in jobs:
        status, rest = by_id.get(i, ('err', 'no result'))
        if status == 'ok':
            result, finals, h, nt, nw = split_ok(rest)
            if result == 'false' and int(nw) > 0:          # Lisp: sorts in place, returns NIL
                result = 'none'
            info[name]['runs'].append((True, effective(result, finals, info[name]['kinds']),
                                       h if int(nt) > 0 else None))     # no input event: no logic trace
        else:
            info[name]['runs'].append((False, rest, None))
    return info


def has_unsupported(body):
    """Only constructs the interpreter cannot run make a function unrunnable."""
    return "('unsupported'," in repr(body)


def split_ok(rest):
    # Result|Finals|Hash|Events|Writes   (Result and Finals are Prolog terms without '|')
    parts = rest.rsplit('|', 4)
    return parts[0], parts[1], parts[2], parts[3], parts[4]


def effective(result, finals, ks):
    """Returned value, or the final first input list for in-place functions."""
    if result != 'none':
        return result
    m = re.match(r'^\[(.*)\]$', finals)
    if 'list' in ks and m is not None:
        first_list = ks.index('list')
        items = split_top(m.group(1))
        return items[first_list] if first_list < len(items) else finals
    return 'none'


def split_top(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
            continue
        depth += ch in '[(' or 0
        depth -= ch in '])' or 0
        cur += ch
    if cur:
        out.append(cur)
    return out


def prolog_value(v):
    if isinstance(v, list):
        return '[' + ','.join(prolog_value(x) for x in v) + ']'
    return str(v)


if __name__ == '__main__':
    for name, d in run_functions(Path(sys.argv[1])).items():
        ok = sum(r[0] for r in d['runs'])
        print(f"{name}: kinds={d['kinds']} runs={ok}/{len(d['runs'])} outputs={[r[1] for r in d['runs']][:6]}")
