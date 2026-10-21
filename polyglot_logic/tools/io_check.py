"""AP13 OPT-IN execution comparison (Satsy-style input/output agreement).

The ONLY AP13 activity that runs code. Off by default; started only by
`cli.py check`. Each run uses a fresh temp directory, a timeout and its own
stdin. It is NOT a security sandbox: only check code you are allowed to run.
Agreement is evidence, never proof. Kinds: sort, search. Candidate runners:
Python and C (others are listed as future work in doc 03).
"""
from __future__ import annotations

import random
import subprocess
import sys
import tempfile
from pathlib import Path

from env_run import ToolError, need, run
from parse_source import language_of

SEED = 13

PY_HARNESS = '''import sys, importlib.util
spec = importlib.util.spec_from_file_location("m", {source!r})
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f = getattr(m, {function!r})
for line in sys.stdin.read().splitlines():
    p = line.split(); n = int(p[1]); xs = [int(v) for v in p[2:2 + n]]
    if p[0] == "sort":
        r = f(xs); print(" ".join(map(str, xs if r is None else r)))
    else:
        print(f(xs, int(p[2 + n])))
'''

C_HARNESS = '''#include <stdio.h>
{signature}
int main(void) {{ char k[16]; int n;
  while (scanf("%15s %d", k, &n) == 2) {{ int a[64], t = 0;
    for (int i = 0; i < n; i++) scanf("%d", &a[i]);
    if (k[1] == 'e') scanf("%d", &t);
    {call} }}
  return 0; }}
'''


def cases(kind):
    rnd = random.Random(SEED)
    lists = [[], [1], [2, 1], [3, 1, 2], [5, 4, 3, 2, 1], [1, 2, 3, 4, 5], [2, 2, 1, 1]]
    lists += [[rnd.randint(-20, 20) for _ in range(rnd.randint(2, 12))] for _ in range(8)]
    if kind == 'sort':
        return [(x, None) for x in lists]
    out = []
    for x in lists:
        s = sorted(set(x))
        out += [(s, s[len(s) // 2] if s else 0), (s, 99)]
    return out


def encode(kind, data):
    lines = []
    for xs, t in data:
        lines.append(f'{kind} {len(xs)} ' + ' '.join(map(str, xs)) + (f' {t}' if kind == 'search' else ''))
    return '\n'.join(lines) + '\n'


def feed(argv, inputs, cwd):
    try:
        done = subprocess.run(argv, input=inputs, capture_output=True, text=True, timeout=30, cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f'{Path(argv[0]).name} run timed out') from exc
    if done.returncode:
        raise ToolError('run failed: ' + done.stderr[-400:])
    return done.stdout.splitlines()


def run_python(source, function, inputs, td, kind):
    (td / 'main.py').write_text(PY_HARNESS.format(source=str(Path(source).resolve()), function=function),
                                encoding='utf-8')
    return feed([sys.executable, '-I', '-B', 'main.py'], inputs, td)


def run_c(source, function, inputs, td, kind):
    if kind == 'sort':
        sig = f'void {function}(int *a, int n);'
        call = f'{function}(a, n); for (int i = 0; i < n; i++) printf(i ? " %d" : "%d", a[i]); printf("\\n");'
    else:
        sig = f'int {function}(const int *a, int n, int target);'
        call = f'printf("%d\\n", {function}(a, n, t));'
    (td / 'main.c').write_text(C_HARNESS.format(signature=sig, call=call), encoding='utf-8')
    built = run([need('gcc'), '-O0', '-o', str(td / 'prog'), str(td / 'main.c'), str(Path(source).resolve())], 60, td)
    if built.returncode:
        raise ToolError('gcc failed: ' + built.stderr[-400:])
    return feed([str(td / 'prog')], inputs, td)


RUNNERS = {'python': run_python, 'c': run_c}


def agree(kind, case, expected, actual):
    if kind == 'sort':
        return expected.split() == actual.split()
    xs, t = case
    try:
        e, a = int(expected), int(actual)
    except ValueError:
        return False
    return (0 <= e < len(xs) and xs[e] == t) == (0 <= a < len(xs) and xs[a] == t)


def main(a) -> int:
    print('AP13_CHECK: OPT-IN execution of reference and candidate (temp dirs, 30 s timeout)')
    lang = language_of(a.candidate)
    if lang not in RUNNERS:
        raise ToolError(f'check supports {sorted(RUNNERS)} candidates for now, not {lang}')
    data = cases(a.kind)
    inputs = encode(a.kind, data)
    with tempfile.TemporaryDirectory(prefix='ap13_ref_') as t1, tempfile.TemporaryDirectory(prefix='ap13_cand_') as t2:
        expected = run_python(a.reference, a.ref_function, inputs, Path(t1), a.kind)
        actual = RUNNERS[lang](a.candidate, a.cand_function, inputs, Path(t2), a.kind)
    if len(expected) != len(data) or len(actual) != len(data):
        raise ToolError('runner produced the wrong number of results')
    ok = sum(agree(a.kind, c, e, x) for c, e, x in zip(data, expected, actual))
    print(f'IO_AGREEMENT {ok}/{len(data)} (evidence only, not proof)')
    return 0
