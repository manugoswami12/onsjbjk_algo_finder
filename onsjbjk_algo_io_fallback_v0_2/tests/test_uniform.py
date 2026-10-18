"""Uniform conversion (user: the same program component is the same Prolog term in every language): the
same algorithm written with the same structure in two languages reaches the same tree node (the normal
process's relations, learn_facts.nodes)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts

DATA = ROOT / 'tests' / 'data' / 'uniform'
PAIRS = [
    ('cmp_le.py', 'cmp_gt.c'),                    # take if w <= cap  /  skip if w > cap; counting loops
    ('caesar_loop.py', 'caesar_loop.lisp'),       # ord / chr = char-code / code-char; append = push
    ('matrix_collect.py', 'matrix_collect.lisp'),  # append to a result = loop ... collect
    ('matrix_table.py', 'matrix_table.lisp'),     # [[0] * n ...] = make-array; c[i][j] = (aref c i j)
]


class UniformTests(unittest.TestCase):
    def test_same_component_same_term(self):
        for a, b in PAIRS:
            with self.subTest(pair=(a, b)):
                self.assertEqual(learn_facts.nodes(DATA / a), learn_facts.nodes(DATA / b))


class BuiltBranchTests(unittest.TestCase):
    def test_hanoi_built_branch(self):
        """Built branch (doc 04 section 15): f(n-1); move; f(n-1) is towers_of_hanoi in every language; the
        combined fib(n-1) + fib(n-2) stays fibonacci_like; a walk on left/right, Ackermann (its jump sets n to 1)
        and an edit distance (its call results are used) stay the broad branch."""
        import learn_apply
        for f, branch in [('hanoi.py', 'towers_of_hanoi'), ('hanoi.c', 'towers_of_hanoi'), ('hanoi.lisp', 'towers_of_hanoi'),
                          ('fib.py', 'fibonacci_like'), ('inorder.py', 'recursive_decomposition')]:
            with self.subTest(file=f):
                self.assertEqual(learn_apply.apply(DATA / f)[3], {branch})
        for f in ('ack.lisp', 'edit.lisp'):
            self.assertNotIn('towers_of_hanoi', learn_apply.apply(DATA / f)[3])


    def test_built_branches(self):
        """Built branches (doc 04 section 15): each task's relation holds in every language; close negatives do
        not get it."""
        import learn_apply
        cases = {'ackermann': (['ack.py', 'ack.c', 'ack.lisp'], ['mc91.py', 'fib.py']),
                 'towers_of_hanoi': (['hanoi.py', 'hanoi.c', 'hanoi.lisp', 'hanoi.hs', 'hanoi_acc.hs'],
                                     ['fib.hs', 'fib.py', 'count_down.hs']),
                 'knapsack_01': (['knap.py', 'knap.c', 'knap_rec.py', 'knap_rec.hs'], ['lcs_table.py', 'matrix_table.py', 'count_down.hs']),
                 'caesar_cipher': (['caesar_loop.py', 'caesar_loop.lisp', 'caesar_pf.hs', 'caesar_base.hs', 'caesar_table.py'],
                                   ['vigenere.py', 'fib.hs', 'upper_table.py']),
                 'matrix_multiplication': (['matrix_table.py', 'matrix_table.lisp', 'matrix_collect.py', 'matrix_collect.lisp',
                                            'matrix_fn.lisp'],
                                           ['dot.py', 'knap.py']),
                 'run_length_encoding': (['rle_group.lisp', 'rle_scan.py', 'rle_span.hs', 'rle_lib.hs'], ['dedup.py', 'sorted_lib.hs']),
                 'n_queens': (['queens_perm.py', 'queens_perm.hs', 'queens_bt.py', 'queens_bt.c', 'queens_fold.hs', 'queens_zip.hs'],
                              ['perm_sort.py', 'grid_paths.py']),
                 'lcs': (['lcs_rec.py', 'lcs_rec.lisp', 'lcs_table.py', 'lcs_memo.hs', 'lcs_pair.lisp'], ['lev_table.py', 'lev_rec.c', 'knap.py']),
                 'levenshtein': (['lev_table.py', 'lev_table.c', 'lev_rec.c'], ['lcs_table.py', 'lcs_rec.py']),
                 'leap_year': (['leap.py', 'leap.c'], ['even.py']),
                 'josephus': (['josephus_sim.py'], ['rotate_pop.py']),
                 'roman_encode': (['roman_fmt.lisp', 'roman_table.c', 'roman_table.py'], ['plain_fmt.lisp', 'coin_change.c'])}
        for task, (positives, negatives) in cases.items():
            for f in positives:
                with self.subTest(task=task, file=f):
                    self.assertIn(task, learn_apply.apply(DATA / f)[3])
            for f in negatives:
                with self.subTest(task=task, negative=f):
                    self.assertNotIn(task, learn_apply.apply(DATA / f)[3])


class HandRuleTests(unittest.TestCase):
    """The hand rules for TheAlgorithms/Python (prolog/ta_rules.pl, doc 04 section 17) on own programs: each positive
    gets exactly its label, each close negative none."""
    POSITIVES = {'ta_bubble.py': 'bubble_sort', 'ta_bubble.c': 'bubble_sort', 'ta_cocktail.c': 'cocktail_shaker_sort',
                 'ta_gnome.py': 'gnome_sort', 'ta_odd_even.c': 'odd_even_sort', 'ta_insertion_shift.py': 'insertion_sort',
                 'ta_insertion_shift.c': 'insertion_sort', 'ta_selection.c': 'selection_sort', 'ta_shell.py': 'shell_sort',
                 'ta_comb.py': 'comb_sort', 'ta_stooge.c': 'stooge_sort', 'ta_quick.py': 'quick_sort',
                 'ta_counting.py': 'counting_sort', 'ta_merge.py': 'merge_sort', 'ta_fact.c': 'factorial',
                 'ta_fact_rec.py': 'factorial', 'ta_fib.c': 'fibonacci', 'ta_fib_rec.lisp': 'fibonacci',
                 'ta_gcd.c': 'greatest_common_divisor', 'ta_lcm.py': 'least_common_multiple',
                 'ta_sieve.c': 'sieve_of_eratosthenes', 'ta_prime.py': 'prime_check', 'ta_perfect.py': 'perfect_number',
                 'ta_digits.c': 'sum_of_digits', 'ta_collatz.py': 'collatz_sequence', 'ta_luhn.py': 'luhn',
                 'ta_bsearch.c': 'binary_search', 'ta_palindrome.py': 'palindrome', 'ta_linear.c': 'linear_search',
                 'ta_hamming.py': 'hamming_distance', 'ta_atbash.py': 'atbash', 'ta_xor.py': 'xor_cipher',
                 'ta_kernighan.c': 'count_1s_brian_kernighan_method', 'ta_bin2dec.py': 'binary_to_decimal',
                 'ta_dec2bin.py': 'decimal_to_binary', 'ta_kadane.py': 'max_subarray', 'ta_floyd.py': 'floyd_warshall',
                 'ta_powsq.py': 'binary_exponentiation', 'ta_dijkstra.py': 'dijkstra', 'ta_bellman.py': 'bellman_ford',
                 'ta_bfs.py': 'breadth_first_search', 'ta_dfs.py': 'depth_first_search', 'ta_kahn.py': 'kahns_algorithm_topo'}
    NEGATIVES = ['ta_neg_reverse.c', 'ta_neg_rotate.py', 'ta_neg_wordcount.py', 'dedup.py', 'perm_sort.py',
                 'ta_neg_double_fact.py', 'ta_neg_lucas.py', 'ta_neg_pell.py', 'ta_neg_ext_gcd.py', 'ta_neg_factorize.py',
                 'ta_neg_reverse_num.py', 'ta_neg_jump.py', 'ta_neg_matches.py', 'ta_neg_shift_count.c',
                 'ta_neg_heap_index.py', 'ta_neg_power_loop.py', 'ta_neg_rpn.py', 'ta_neg_grid_dp.py']

    def hand(self, f):
        import learn_apply
        found = set()
        learn_apply.apply(DATA / f, hand=found)
        return found

    def test_rules_load_cleanly(self):
        import subprocess
        out = subprocess.run(['swipl', '-g', "consult('prolog/learn_apply.pl'), halt"], cwd=ROOT, capture_output=True,
                             text=True)
        self.assertEqual(out.stderr.strip(), '')

    def test_positives(self):
        for f, label in self.POSITIVES.items():
            with self.subTest(f=f):
                self.assertEqual(self.hand(f), {label})

    def test_negatives(self):
        for f in self.NEGATIVES:
            with self.subTest(f=f):
                self.assertEqual(self.hand(f), set())


if __name__ == '__main__':
    unittest.main()
