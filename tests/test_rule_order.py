"""Rule order in the tree (prolog/families_v02.pl deepest_families_v02/2): AP13's one-level fallbacks ([numeric],
[sequence_query], [sequence_transformation]) hold only when no branch below applies (families.pl deeper_path/1), and
that holds for the v0.2 branches too. Before, deeper_path/1 saw AP13's own clauses only, so a function on a v0.2 branch
also reached an unrelated fallback node (mergesort's merge_sort: ...>merge and sequence_query)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts

CORPUS = ROOT / 'data' / 'TheAlgorithms-Python'
EXPECTED = {
    'divide_and_conquer/mergesort.py': {'merge_sort': {'sequence_transformation>comparison_sort>merge'}},
    'knapsack/recursive_approach_knapsack.py': {'knapsack': {'numeric>recurrence>capacity_reduction'}},
    'maths/josephus_problem.py': {'josephus_iterative': {'sequence_transformation>elimination_cycle'}},
    'other/number_container_system.py': {
        'NumberContainer.binary_search_insert': {'sequence_query>target_search>interval_halving'}},
}


def function_nodes(path: Path) -> dict[str, set[str]]:
    kind, text = learn_facts.tree_facts(path)
    out = {}
    for line in learn_facts.swipl_facts('tree_main', learn_facts.TREE_MAIN, kind, text):
        if line.startswith('NODE|'):
            _, fn, node = line.split('|', 2)
            out.setdefault(fn, set()).add(node)
    return out


class RuleOrderTests(unittest.TestCase):
    def test_fallback_dropped_below_a_v02_branch(self):
        for rel, want in EXPECTED.items():
            got = function_nodes(CORPUS / rel)
            for fn, nodes in want.items():
                with self.subTest(file=rel, function=fn):
                    self.assertEqual(got[fn], nodes)

    def test_fallback_kept_without_a_branch_below(self):
        got = function_nodes(CORPUS / 'sorts' / 'cycle_sort.py')
        self.assertEqual(got['cycle_sort'], {'sequence_query'})


if __name__ == '__main__':
    unittest.main()
