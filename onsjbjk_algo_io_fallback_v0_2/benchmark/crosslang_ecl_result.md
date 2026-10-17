# Common Lisp through ECL: Lisp -> ECL C -> v0.2 facts -> prolog/route_v2.pl

ECL (21.2.1) compiles each defun to C (nothing is run). `ecl_witness.py` reads ECL's fixed C shapes as the
same facts the Python witnesses emit (linear_self_product, self_calls_minus_one_minus_two, modulo_recurrence,
digit_decomposition, element_exchange, comparison_controls_exchange, ...); the unchanged Prolog router branches.
No learning, no behaviour runs: knowledge = the v0.2 branch rules built for Python.

| Stage | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| clean: 3 never-used functions (quicksort, topo-sort, naive-match) | 1/1 | 1/1 | 0/2 |
| all 21 functions of the frozen key (most inspected earlier, not held-out) | 4/5 = 80% | 4/9 = 44.4% | 0/12 |

Found: naive-fib (fibonacci_like), insertion-sort and heapsort and quicksort (sorting). selection-sort got only
the broad sorting family (no ECL min-index shape yet: counted WRONG against its narrow label).
Missed (no ECL shape written yet): bin-search, bin-search-v0 (midpoint interval), mat-max (2-D best-so-far),
merge-sort (list consing).
