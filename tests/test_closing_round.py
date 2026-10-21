"""The closing round's lowering rules (doc 04 section 19.17), each a language's own semantics: C expressions with
effects, arrays, casts, literals, / and %; Python lambdas, module constants,
sequence unpacking, library functions; Lisp case, subseq, &optional, last, map; Haskell: the Prelude's
list functions, point-free definitions by their GHC type, composition and operators as values."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools_manual')]
import crosslang_frontends

crosslang_frontends.install(lisp_sbcl=False)
import haskell_core_pnf
import io_trace


def runs(name, text, fn):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / name
        p.write_text(text, encoding='utf-8')
        d = io_trace.run_functions(p)[fn]
        return {tuple(map(lambda a: tuple(a) if isinstance(a, list) else a, a)): r[1] for a, r in zip(d['inputs'], d['runs'])}


class C(unittest.TestCase):
    def test_effects_in_expressions(self):
        src = 'int f(int n) { int s = 0, i = 0, j = 0; while (--n > 0) s += n; for (i = 0, j = 1; i < 3; i++, j++) s += j; int a = s++; return a * 100 + s; }\n'
        r = runs('m.c', src, 'f')
        self.assertEqual(r[(3,)], '910')          # s = 2 + 1 = 3, then + 1 + 2 + 3 = 9; a = 9, s = 10

    def test_arrays_sizeof_malloc(self):
        src = ('int f(int n) { int a[3] = {1, 2}; int b[] = {4, 5}; int m[2][3]; m[1][2] = n; '
               'int len = sizeof b / sizeof b[0]; int *x = malloc(n * sizeof(int)); x[0] = 7; free(x); '
               'return a[2] + b[1] + m[1][2] + m[0][2] + len; }\n')
        self.assertEqual(runs('m.c', src, 'f')[(2,)], '9')     # 0 + 5 + 2 + 0 + 2

    def test_casts_literals_division(self):
        src = 'int f(int n) { double x = n / 2.0; int k = (int) x; return k * 10 + (int)(x * 2) + 0x10 + 017 + -7 % 2 + -7 / 2; }\n'
        self.assertEqual(runs('m.c', src, 'f')[(3,)], '40')    # 10 + 3 + 16 + 15 - 1 - 3


class Python(unittest.TestCase):
    def test_lambda(self):
        src = 'from functools import reduce\ndef f(n):\n    return reduce(lambda a, b: a + b, range(n + 1), 0) + sum([i * i for i in range(n)])\n'
        self.assertEqual(runs('m.py', src, 'f')[(3,)], '11')   # 6 + 5

    def test_module_constant_read_only(self):
        src = 'TABLE = (10, 20, 30)\ndef f(n):\n    return TABLE[n % 3]\n'
        self.assertEqual(runs('m.py', src, 'f')[(4,)], '20')

    def test_appended_global_is_not_a_constant(self):
        src = 'memo = []\ndef f(n):\n    memo.append(n)\n    return len(memo)\n'
        self.assertEqual(runs('m.py', src, 'f')[(4,)], 'unbound(memo)')

    def test_written_global_is_not_a_constant(self):
        src = 'count = 0\ndef f(n):\n    global count\n    count = count + n\n    return count\n'
        self.assertNotEqual(runs('m.py', src, 'f')[(4,)], '4')

    def test_unpack_list_and_library(self):
        src = ('import bisect\ndef f(s):\n    out = []\n    for x in s:\n        bisect.insort(out, x)\n    a, b = [len(out), 1]\n'
               '    return out\ndef g(n):\n    t = "aB3"\n    return [t.upper(), [c.isalpha() for c in t], str(n).zfill(3)]\n')
        self.assertEqual(runs('m.py', src, 'f')[((3, 1, 2),)], '[1,2,3]')
        self.assertEqual(runs('m.py', src, 'g')[(7,)], '[[65,66,51],[true,true,false],[48,48,55]]')

    def test_own_function_wins_over_library(self):
        src = 'def insort(a, x):\n    return 99\ndef f(n):\n    return insort([], n)\n'
        self.assertEqual(runs('m.py', src, 'f')[(1,)], '99')


class Lisp(unittest.TestCase):
    def test_case_subseq_optional(self):
        src = ('(defun factorial (n &optional (m 1)) (if (zerop n) m (factorial (1- n) (* m n))))\n'
               '(defun pick (n) (case n (0 10) ((1 2) 20) (t 30)))\n'
               '(defun flip2 (l) (setf (subseq l 0 2) (reverse (subseq l 0 2))) l)\n'
               '(defun lastof (l) (car (last l)))\n(defun twice (l) (map \'list (lambda (x) (* 2 x)) l))\n')
        self.assertEqual(runs('m.lisp', src, 'factorial')[(4,)], '24')
        self.assertEqual([runs('m.lisp', src, 'pick')[(k,)] for k in (0, 2, 5)], ['10', '20', '30'])
        self.assertEqual(runs('m.lisp', src, 'flip2')[((3, 1, 2),)], '[1,3,2]')
        self.assertEqual(runs('m.lisp', src, 'lastof')[((3, 1, 2),)], '2')
        self.assertEqual(runs('m.lisp', src, 'twice')[((2, 1),)], '[4,2]')


class Haskell(unittest.TestCase):
    def test_prelude_lists(self):
        src = ('import Data.List (delete)\nsums :: [Int] -> [Int]\nsums xs = scanl (+) 0 xs\n'
               'dup :: [Int] -> [Int]\ndup xs = concatMap (\\x -> [x, x]) xs\ndel1 :: [Int] -> [Int]\ndel1 xs = delete 1 xs\n')
        self.assertEqual(runs('m.hs', src, 'sums')[((3, 1, 2),)], '[0,3,4,6]')
        self.assertEqual(runs('m.hs', src, 'dup')[((2, 1),)], '[2,2,1,1]')
        self.assertEqual(runs('m.hs', src, 'del1')[((3, 1, 2),)], '[3,2]')

    def test_point_free_by_type_and_operator_value(self):
        src = ('total :: [Int] -> Int\ntotal = foldr ((+) . (* 2)) 0\n'
               'sortBy\' :: (Int -> Int -> Bool) -> [Int] -> [Int]\nsortBy\' f [] = []\n'
               'sortBy\' f (x:xs) = sortBy\' f [y | y <- xs, f y x] ++ [x] ++ sortBy\' f [y | y <- xs, not (f y x)]\n'
               'qs :: [Int] -> [Int]\nqs = sortBy\' (<)\n')
        self.assertEqual(runs('m.hs', src, 'total')[((3, 1, 2),)], '12')
        self.assertEqual(runs('m.hs', src, 'qs')[((3, 1, 2),)], '[1,2,3]')


if __name__ == '__main__':
    unittest.main()
