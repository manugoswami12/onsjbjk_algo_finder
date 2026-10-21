"""clang's parser checks the structure facts of a C file (doc 04 section 19.11, c_ast_check.py): a function-pointer
parameter tree-sitter misses comes from clang; a file clang cannot parse cleanly keeps its facts."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import c_ast_check
import learn_facts


def params(facts: str) -> list[str]:
    return re.findall(r"param\('[^']+',\d+,'([^']+)'\)", facts)


def facts_of(source: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.c'
        path.write_text(source, encoding='utf-8')
        return learn_facts.c_facts(path), learn_facts.tree_facts(path)[1]


class CAstCheckTests(unittest.TestCase):
    def test_a_function_pointer_parameter_comes_from_clang(self):
        before, after = facts_of('void sort(int *a, int n, int (*cmp)(int, int)) {\n'
                                 '  for (int i = 0; i < n; i++) if (cmp(a[i], a[0]) < 0) a[0] = a[i];\n}\n')
        self.assertNotIn('cmp', params(before))
        self.assertEqual(params(after), ['a', 'n', 'cmp'])

    def test_plain_functions_are_unchanged(self):
        before, after = facts_of('int f(int n) { int r = 1; for (int i = 2; i <= n; i++) r *= i; return r; }\n')
        self.assertEqual(before, after)

    def test_a_file_clang_cannot_parse_is_unchanged(self):
        before, after = facts_of('int f(int n) { int g(int x) { return x + n; } return g(1); }\n')
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
