"""Differential test (translation validation) of the Haskell and Lisp front ends.

Small programs WRITTEN FOR THIS TEST (not candidates) are run natively (runghc / sbcl) and through
the front end + AP13 interpreter on the same inputs; every output must agree.
Skipped when ghc / sbcl / swipl are missing.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HASKELL = {
    'fact': ('fact n = if n <= 1 then 1 else n * fact (n - 1)', [[0], [1], [5], [10]]),
    'fib': ('fib n = go n 0 1\n  where\n    go 0 a _ = a\n    go k a b = go (k - 1) b (a + b)', [[0], [1], [7], [20]]),
    'gcd2': ('gcd2 a 0 = a\ngcd2 a b = gcd2 b (a `mod` b)', [[12, 18], [7, 5], [100, 75]]),
    'isort': ('isort :: [Int] -> [Int]\nisort [] = []\nisort (x:xs) = ins x (isort xs)\n'
              'ins x [] = [x]\nins x (y:ys) | x <= y = x : y : ys\n             | otherwise = y : ins x ys',
              [[[3, 1, 2]], [[]], [[5, 4, 3, 2, 1]]]),
    'pal': ('pal :: [Int] -> Bool\npal s = s == reverse s', [[[1, 2, 1]], [[1, 2]], [[]]]),
    'dsum': ('dsum 0 = 0\ndsum n = n `mod` 10 + dsum (n `div` 10)', [[0], [123], [9999]]),
    'prime': ('prime n = n > 1 && all (\\d -> n `mod` d /= 0) [2 .. n - 1]', [[1], [2], [9], [13]]),
    'hail': ('hail n = takeWhile (/= 1) (iterate step n) ++ [1]\n'
             '  where step k = if even k then k `div` 2 else 3 * k + 1', [[1], [3], [6]]),
    'qs': ('qs :: [Int] -> [Int]\nqs [] = []\nqs (p:xs) = qs [x | x <- xs, x < p] ++ [p] ++ qs [x | x <- xs, x >= p]',
           [[[3, 1, 2]], [[2, 2, 1]], [[]]]),
    'dot': ('dot :: [Int] -> [Int] -> Int\ndot a b = sum (zipWith (*) a b)', [[[1, 2, 3], [4, 5, 6]], [[], []]]),
}

LISP = {
    'fact': ('(defun fact (n) (if (<= n 1) 1 (* n (fact (- n 1)))))', [[0], [5], [10]]),
    'fact-loop': ('(defun fact-loop (n) (loop for r = 1 then (* r i) for i from 2 to n finally (return r)))',
                  [[0], [1], [5]]),
    'gcd2': ('(defun gcd2 (a b) (do () ((zerop b) a) (shiftf a b (mod a b))))', [[12, 18], [7, 5]]),
    'sum-to': ('(defun sum-to (n) (loop for i from 1 to n sum i))', [[0], [4], [10]]),
    'odd-squares': ('(defun odd-squares (xs) (loop for x in xs when (oddp x) collect (* x x)))',
                    [[[1, 2, 3]], [[]]]),
    'lcm-all': ('(defun lcm-all (&rest xs) (reduce (lambda (m n) (/ (* m n) (gcd m n))) xs :initial-value 1))',
                [[[4, 6]], [[3, 5, 7]]]),
    'pal': ('(defun pal (s) (equal s (reverse s)))', [[[1, 2, 1]], [[1, 2]]]),
}


def hs_lit(v):
    return '[' + ','.join(map(str, v)) + ']' if isinstance(v, list) else (f'({v})' if v < 0 else str(v))


def lisp_lit(v):
    return "'(" + ' '.join(map(str, v)) + ')' if isinstance(v, list) else str(v)


def norm(s):
    """Haskell `show` / Lisp `print` / interpreter output -> one spelling. In Lisp NIL is both
    false and the empty list, so both spell `nil`."""
    s = s.strip()
    if s.startswith('('):                                    # Lisp list (1 9)
        s = '[' + ','.join(s[1:-1].split()) + ']'
    s = s.replace(' ', '')
    s = {'True': 'true', 'False': 'false', 'T': 'true', 'NIL': 'false'}.get(s, s)
    return 'nil' if s in ('false', '[]') else s


def interp_outputs(path, name, inputs):
    import crosslang_frontends
    crosslang_frontends.install()
    import io_trace
    from to_prolog import render  # noqa: F401  (AP13 tools on sys.path after install)
    lang, funs = io_trace.normal_form(path)
    pnf = ['pnf_lang(%s).' % io_trace.term(lang)] + \
        [f"pnf_fun({io_trace.term(n)},{io_trace.term(list(ps))},{io_trace.render(b)})." for n, ps, b in funs]
    jobs = ''.join(f"job({i},{io_trace.term(name)},{io_trace.prolog_value(x)}).\n" for i, x in enumerate(inputs))
    with tempfile.TemporaryDirectory() as td:
        pf, jf = Path(td) / 'p.pl', Path(td) / 'j.pl'
        pf.write_text('\n'.join(pnf) + '\n', encoding='utf-8')
        jf.write_text(jobs, encoding='utf-8')
        lines = io_trace.swipl('run_main', [io_trace.PROLOG_DIR / 'run_main.pl'], [str(pf), str(jf)], timeout=60)
    out = {}
    for line in lines:
        m = io_trace._RES.match(line)
        if m:
            out[int(m.group(1))] = io_trace.split_ok(m.group(3))[0] if m.group(2) == 'ok' else 'ERR:' + m.group(3)
    return [out.get(i, 'missing') for i in range(len(inputs))]


@unittest.skipUnless(shutil.which('ghc') and shutil.which('swipl'), 'ghc / swipl missing')
class HaskellFrontEnd(unittest.TestCase):
    def test_native_equals_translation(self):
        src = '\n'.join(code for code, _ in HASKELL.values())
        main = ['main = do']
        for name, (_, inputs) in HASKELL.items():
            for x in inputs:
                main.append(f'  print ({name} {" ".join(hs_lit(a) for a in x)})')
        with tempfile.TemporaryDirectory() as td:
            prog = Path(td) / 'T.hs'
            prog.write_text(src + '\n' + '\n'.join(main) + '\n', encoding='utf-8')
            native = subprocess.run(['runghc', str(prog)], capture_output=True, text=True, timeout=300,
                                    check=True).stdout.splitlines()
            lib = Path(td) / 'L.hs'
            lib.write_text(src + '\n', encoding='utf-8')
            k = 0
            for name, (_, inputs) in HASKELL.items():
                got = interp_outputs(lib, name, inputs)
                for x, g in zip(inputs, got, strict=True):
                    with self.subTest(fn=name, x=x):
                        self.assertEqual(norm(native[k]), norm(g))
                    k += 1


@unittest.skipUnless(shutil.which('sbcl') and shutil.which('swipl'), 'sbcl / swipl missing')
class LispFrontEnd(unittest.TestCase):
    def test_native_equals_translation(self):
        src = '\n'.join(code for code, _ in LISP.values())
        calls = []
        for name, (_, inputs) in LISP.items():
            for x in inputs:
                args = ' '.join(lisp_lit(a) for a in x) if name != 'lcm-all' else ' '.join(map(str, x[0]))
                calls.append(f'(print ({name} {args}))')
        with tempfile.TemporaryDirectory() as td:
            prog = Path(td) / 't.lisp'
            prog.write_text(src + '\n' + '\n'.join(calls) + '\n', encoding='utf-8')
            native = [ln for ln in subprocess.run(['sbcl', '--script', str(prog)], capture_output=True, text=True,
                                                  timeout=120, check=True).stdout.splitlines() if ln.strip()]
            lib = Path(td) / 'l.lisp'
            lib.write_text(src + '\n', encoding='utf-8')
            k = 0
            for name, (_, inputs) in LISP.items():
                got = interp_outputs(lib, name, inputs)
                for x, g in zip(inputs, got, strict=True):
                    with self.subTest(fn=name, x=x):
                        self.assertEqual(norm(native[k]), norm(g))
                    k += 1


if __name__ == '__main__':
    unittest.main()
