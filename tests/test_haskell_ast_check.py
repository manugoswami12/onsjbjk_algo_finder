"""GHC's parser checks the structure facts of a Haskell file (doc 04 section 19.10, haskell_ast_check.py): a
function tree-sitter reports that GHC does not bind is dropped; a file GHC cannot parse keeps its facts."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import haskell_ast_check
import haskell_logic


def functions(facts: str) -> list[str]:
    return re.findall(r"func\('[^']+','((?:[^'\\]|\\.)*)'", facts)


def checked(source: str) -> tuple[list[str], list[str]]:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'p.hs'
        path.write_text(source, encoding='utf-8')
        facts = haskell_logic.lower(path)
        return functions(facts), functions(haskell_ast_check.check(facts, path))


class HaskellAstCheckTests(unittest.TestCase):
    def test_ghc_binds_every_function(self):
        names = haskell_ast_check.ghc_functions(ROOT / 'data/rosetta/Task/Perfect-numbers/Haskell/perfect-numbers-2.hs')
        self.assertTrue({'perfect', 'isPerfect', 'isPrime'} <= names)

    def test_a_guard_read_as_definitions_is_dropped(self):
        path = ROOT / 'data/rosetta/Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-15.hs'
        facts = haskell_logic.lower(path)
        self.assertIn('otherwise', functions(facts))
        kept = functions(haskell_ast_check.check(facts, path))
        self.assertNotIn('otherwise', kept)
        self.assertNotIn('<=', kept)
        self.assertIn('siftdown', kept)

    def test_primes_operators_and_local_functions_are_kept(self):
        before, after = checked("f' :: Int -> Int\nf' n = go n 0 where\n  go 0 a = a\n  go k a = go (k - 1) (a + k)\n"
                                "(<+>) :: Int -> Int -> Int\na <+> b = a + b\n")
        self.assertEqual(before, after)

    def test_a_file_ghc_cannot_parse_is_unchanged(self):
        before, after = checked('f n =\n  let x = n\n y = 2\n  in x\n')
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
