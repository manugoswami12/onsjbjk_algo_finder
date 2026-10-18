# Answer for every held-out file (doc 04 section 18.2): held-out Rosetta files

Each file gets one answer, in order: the algorithm (eval_ta.py); its class (a class relation on runs over every battery input with a node witness, a proposed branch, or a library name); else the user's rule: a file that reaches a tree node where no rule matched is a variation of the family at that node, and a file that reaches no tree node is an error or a new class. Separate from the pipeline (eval_decision.py).

Identified = algorithm or class. A family answer is right when TheAlgorithms files of the task reach a node on its path; it is reported apart and never counted as identified. A root family (numeric, sequence_query, sequence_transformation) holds 9+ tasks.

| language | files | identified: correct / wrong | precision | recall | variation, deep node: right / wrong | variation, root node only: right / wrong | error or new class (no node) |
|---|---|---|---|---|---|---|---|
| C | 69 | 31 / 1 | 96.9% | 44.9% | 7 / 1 | 7 / 7 | 15 |
| Common-Lisp | 75 | 44 / 1 | 97.8% | 58.7% | 9 / 2 | 4 / 5 | 10 |
| Haskell | 144 | 33 / 2 | 94.3% | 22.9% | 3 / 3 | 17 / 29 | 57 |
| Python | 162 | 61 / 6 | 91.0% | 37.7% | 13 / 4 | 25 / 12 | 41 |
| all | 450 | 169 / 10 | 94.4% | 37.6% | 32 / 10 | 53 / 53 | 123 |

## Wrong answers (10)

- Task/Factorial/C/factorial-2.c: algorithm problem_020, task Factorial
- Task/Factorial/Haskell/factorial-8.hs: algorithm problem_020, task Factorial
- Task/Factorial/Python/factorial-7.py: algorithm problem_020, task Factorial
- Task/Fibonacci-sequence/Common-Lisp/fibonacci-sequence-9.lisp: algorithm signum, task Fibonacci-sequence
- Task/Least-common-multiple/Python/least-common-multiple-2.py: algorithm Greatest-common-divisor, task Least-common-multiple
- Task/Levenshtein-distance/Python/levenshtein-distance-5.py: algorithm problem_007, task Levenshtein-distance
- Task/Perfect-numbers/Haskell/perfect-numbers-1.hs: algorithm primelib, task Perfect-numbers
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-2.py: algorithm magicdiamondpattern, task Roman-numerals-Encode
- Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-3.py: algorithm average_mode, task Sorting-algorithms-Insertion-sort
- Task/Sorting-algorithms-Quicksort/Python/sorting-algorithms-quicksort-1.py: algorithm Sorting-algorithms-Cycle-sort, task Sorting-algorithms-Quicksort

## Variation of a deep family, family wrong (10)

- Task/Factorial/Haskell/factorial-10.hs: numeric>recurrence>double_recursion, task Factorial
- Task/Longest-common-subsequence/Python/longest-common-subsequence-3.py: sequence_query>aggregate>gatherer, task Longest-common-subsequence
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-4.py: numeric>conditional_iteration, task Roman-numerals-Encode
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-14.py: numeric>recurrence>range_accumulation, task Sieve-of-Eratosthenes
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-9.py: numeric>conditional_iteration, task Sieve-of-Eratosthenes
- Task/Sorting-algorithms-Counting-sort/Common-Lisp/sorting-algorithms-counting-sort.lisp: sequence_transformation>comparison_sort, task Sorting-algorithms-Counting-sort
- Task/Sorting-algorithms-Heapsort/C/sorting-algorithms-heapsort.c: sequence_transformation>uncompared_rearrangement, task Sorting-algorithms-Heapsort
- Task/Sorting-algorithms-Quicksort/Common-Lisp/sorting-algorithms-quicksort-3.lisp: numeric>recurrence>double_recursion, task Sorting-algorithms-Quicksort
- Task/Sorting-algorithms-Stooge-sort/Haskell/sorting-algorithms-stooge-sort-1.hs: numeric>recurrence>double_recursion, task Sorting-algorithms-Stooge-sort
- Task/Towers-of-Hanoi/Haskell/towers-of-hanoi-1.hs: sequence_transformation>comparison_sort>partition_recursive, task Towers-of-Hanoi

## Error or new class: reaches no tree node (123; every held-out task is known, so each is a program the lowering or interpreter cannot handle)

- Task/Binary-search/Haskell/binary-search-2.hs (task Binary-search)
- Task/Binary-search/Haskell/binary-search-3.hs (task Binary-search)
- Task/Binary-search/Python/binary-search-5.py (task Binary-search)
- Task/Caesar-cipher/Python/caesar-cipher-4.py (task Caesar-cipher)
- Task/Factorial/C/factorial-6.c (task Factorial)
- Task/Factorial/Haskell/factorial-2.hs (task Factorial)
- Task/Factorial/Haskell/factorial-4.hs (task Factorial)
- Task/Factorial/Haskell/factorial-5.hs (task Factorial)
- Task/Factorial/Haskell/factorial-9.hs (task Factorial)
- Task/Factorial/Python/factorial-4.py (task Factorial)
- Task/Factorial/Python/factorial-5.py (task Factorial)
- Task/Fibonacci-sequence/C/fibonacci-sequence-3.c (task Fibonacci-sequence)
- Task/Fibonacci-sequence/C/fibonacci-sequence-4.c (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-1.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-10.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-11.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-12.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-13.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-14.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-15.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-16.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-17.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-18.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-19.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-2.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-22.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-24.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-6.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-7.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Haskell/fibonacci-sequence-8.hs (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-1.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-15.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-16.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-17.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-18.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-2.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-6.py (task Fibonacci-sequence)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-9.py (task Fibonacci-sequence)
- Task/Greatest-common-divisor/Common-Lisp/greatest-common-divisor-3.lisp (task Greatest-common-divisor)
- Task/Greatest-common-divisor/Python/greatest-common-divisor-1.py (task Greatest-common-divisor)
- Task/Greatest-common-divisor/Python/greatest-common-divisor-2.py (task Greatest-common-divisor)
- Task/Hailstone-sequence/C/hailstone-sequence-2.c (task Hailstone-sequence)
- Task/Hailstone-sequence/Haskell/hailstone-sequence-1.hs (task Hailstone-sequence)
- Task/Josephus-problem/Python/josephus-problem-3.py (task Josephus-problem)
- Task/Josephus-problem/Python/josephus-problem-4.py (task Josephus-problem)
- Task/Knapsack-problem-0-1/Haskell/knapsack-problem-0-1-3.hs (task Knapsack-problem-0-1)
- Task/Knapsack-problem-0-1/Python/knapsack-problem-0-1-4.py (task Knapsack-problem-0-1)
- Task/Least-common-multiple/Common-Lisp/least-common-multiple-2.lisp (task Least-common-multiple)
- Task/Least-common-multiple/Python/least-common-multiple-1.py (task Least-common-multiple)
- Task/Longest-common-subsequence/C/longest-common-subsequence-2.c (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Common-Lisp/longest-common-subsequence-2.lisp (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Common-Lisp/longest-common-subsequence-3.lisp (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Common-Lisp/longest-common-subsequence-5.lisp (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Haskell/longest-common-subsequence-4.hs (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Haskell/longest-common-subsequence-6.hs (task Longest-common-subsequence)
- Task/Longest-common-subsequence/Python/longest-common-subsequence-2.py (task Longest-common-subsequence)
- Task/Luhn-test-of-credit-card-numbers/Common-Lisp/luhn-test-of-credit-card-numbers-2.lisp (task Luhn-test-of-credit-card-numbers)
- Task/Luhn-test-of-credit-card-numbers/Haskell/luhn-test-of-credit-card-numbers-1.hs (task Luhn-test-of-credit-card-numbers)
- Task/Luhn-test-of-credit-card-numbers/Haskell/luhn-test-of-credit-card-numbers-2.hs (task Luhn-test-of-credit-card-numbers)
- Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-2.py (task Luhn-test-of-credit-card-numbers)
- Task/N-queens-problem/C/n-queens-problem-1.c (task N-queens-problem)
- Task/N-queens-problem/Haskell/n-queens-problem-1.hs (task N-queens-problem)
- Task/N-queens-problem/Python/n-queens-problem-10.py (task N-queens-problem)
- Task/N-queens-problem/Python/n-queens-problem-2.py (task N-queens-problem)
- Task/Palindrome-detection/C/palindrome-detection-1.c (task Palindrome-detection)
- Task/Palindrome-detection/C/palindrome-detection-2.c (task Palindrome-detection)
- Task/Palindrome-detection/C/palindrome-detection-3.c (task Palindrome-detection)
- Task/Palindrome-detection/C/palindrome-detection-4.c (task Palindrome-detection)
- Task/Palindrome-detection/Python/palindrome-detection-2.py (task Palindrome-detection)
- Task/Palindrome-detection/Python/palindrome-detection-5.py (task Palindrome-detection)
- Task/Palindrome-detection/Python/palindrome-detection-6.py (task Palindrome-detection)
- Task/Palindrome-detection/Python/palindrome-detection-8.py (task Palindrome-detection)
- Task/Perfect-numbers/C/perfect-numbers-2.c (task Perfect-numbers)
- Task/Primality-by-trial-division/Haskell/primality-by-trial-division-1.hs (task Primality-by-trial-division)
- Task/Primality-by-trial-division/Haskell/primality-by-trial-division-3.hs (task Primality-by-trial-division)
- Task/Primality-by-trial-division/Python/primality-by-trial-division-3.py (task Primality-by-trial-division)
- Task/Primality-by-trial-division/Python/primality-by-trial-division-4.py (task Primality-by-trial-division)
- Task/Roman-numerals-Encode/Haskell/roman-numerals-encode-1.hs (task Roman-numerals-Encode)
- Task/Roman-numerals-Encode/Haskell/roman-numerals-encode-3.hs (task Roman-numerals-Encode)
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-1.py (task Roman-numerals-Encode)
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-5.py (task Roman-numerals-Encode)
- Task/Roman-numerals-Encode/Python/roman-numerals-encode-7.py (task Roman-numerals-Encode)
- Task/Run-length-encoding/Python/run-length-encoding-3.py (task Run-length-encoding)
- Task/Sieve-of-Eratosthenes/C/sieve-of-eratosthenes-3.c (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-1.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-13.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-2.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-21.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-22.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-23.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-24.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-25.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-3.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-4.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-6.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-8.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-9.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-10.py (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-12.py (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-13.py (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-4.py (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-5.py (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-8.py (task Sieve-of-Eratosthenes)
- Task/Sorting-algorithms-Bubble-sort/Common-Lisp/sorting-algorithms-bubble-sort-2.lisp (task Sorting-algorithms-Bubble-sort)
- Task/Sorting-algorithms-Cocktail-sort/C/sorting-algorithms-cocktail-sort-2.c (task Sorting-algorithms-Cocktail-sort)
- Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-2.py (task Sorting-algorithms-Cocktail-sort)
- Task/Sorting-algorithms-Comb-sort/Haskell/sorting-algorithms-comb-sort-2.hs (task Sorting-algorithms-Comb-sort)
- Task/Sorting-algorithms-Counting-sort/C/sorting-algorithms-counting-sort-2.c (task Sorting-algorithms-Counting-sort)
- Task/Sorting-algorithms-Counting-sort/Haskell/sorting-algorithms-counting-sort.hs (task Sorting-algorithms-Counting-sort)
- Task/Sorting-algorithms-Heapsort/Haskell/sorting-algorithms-heapsort-2.hs (task Sorting-algorithms-Heapsort)
- Task/Sorting-algorithms-Heapsort/Haskell/sorting-algorithms-heapsort-3.hs (task Sorting-algorithms-Heapsort)
- Task/Sorting-algorithms-Heapsort/Haskell/sorting-algorithms-heapsort-4.hs (task Sorting-algorithms-Heapsort)
- Task/Sorting-algorithms-Insertion-sort/Common-Lisp/sorting-algorithms-insertion-sort-1.lisp (task Sorting-algorithms-Insertion-sort)
- Task/Sorting-algorithms-Insertion-sort/Haskell/sorting-algorithms-insertion-sort.hs (task Sorting-algorithms-Insertion-sort)
- Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-4.py (task Sorting-algorithms-Insertion-sort)
- Task/Sorting-algorithms-Pancake-sort/C/sorting-algorithms-pancake-sort-3.c (task Sorting-algorithms-Pancake-sort)
- Task/Sorting-algorithms-Pancake-sort/Common-Lisp/sorting-algorithms-pancake-sort-2.lisp (task Sorting-algorithms-Pancake-sort)
- Task/Sorting-algorithms-Pancake-sort/Haskell/sorting-algorithms-pancake-sort-2.hs (task Sorting-algorithms-Pancake-sort)
- Task/Sorting-algorithms-Pancake-sort/Python/sorting-algorithms-pancake-sort-2.py (task Sorting-algorithms-Pancake-sort)
- Task/Sorting-algorithms-Stooge-sort/Haskell/sorting-algorithms-stooge-sort-2.hs (task Sorting-algorithms-Stooge-sort)
- Task/Sum-digits-of-an-integer/Common-Lisp/sum-digits-of-an-integer-2.lisp (task Sum-digits-of-an-integer)
- Task/Sum-digits-of-an-integer/Haskell/sum-digits-of-an-integer-2.hs (task Sum-digits-of-an-integer)
- Task/Sum-digits-of-an-integer/Haskell/sum-digits-of-an-integer-3.hs (task Sum-digits-of-an-integer)

## Class decisions on TheAlgorithms/Python files (36), to check by hand

- **gcd** (1): maths/greatest_common_divisor.py
- **power** (2): divide_and_conquer/power.py, maths/power_using_recursion.py
- **search** (2): searches/double_linear_search.py, searches/jump_search.py
- **sorting** (31): divide_and_conquer/mergesort.py, sorts/adaptive_merge_sort.py, sorts/binary_insertion_sort.py, sorts/bubble_sort.py, sorts/bubble_sort_recursive.py, sorts/circle_sort.py, sorts/cocktail_shaker_sort.py, sorts/comb_sort.py, sorts/cycle_sort.py, sorts/double_sort.py, sorts/exchange_sort.py, sorts/gnome_sort.py, sorts/heap_sort.py, sorts/insertion_sort.py, sorts/iterative_merge_sort.py, sorts/merge_insertion_sort.py, sorts/merge_sort.py, sorts/odd_even_sort.py, sorts/odd_even_transposition_single_threaded.py, sorts/pancake_sort.py, sorts/pigeon_sort.py, sorts/pigeonhole_sort.py, sorts/quick_sort.py, sorts/recursive_insertion_sort.py, sorts/recursive_quick_sort.py, sorts/reverse_selection.py, sorts/selection_sort.py, sorts/shell_sort.py, sorts/shrink_shell_sort.py, sorts/stooge_sort.py, sorts/tim_sort.py

## Class decisions on TheAlgorithms/Python files dropped by node agreement (2)

- maths/average_mode.py: sorting, nodes []
- maths/special_numbers/triangular_numbers.py: triangular, nodes []

## Notes (the user's rule for unanswered files)

- **Variation of a deep family: 32 right, 10 wrong (76 %).** Examples of a wrong family: a Lisp quicksort lands on
  `numeric>recurrence>double_recursion` (two self-calls, like a Fibonacci), and a C heapsort lands on
  `sequence_transformation>uncompared_rearrangement`.
- **Variation of a root family only: 53 right, 53 wrong (50 %).** A root (numeric, sequence_query,
  sequence_transformation) holds 9 or more tasks, so it names almost nothing.
- **Error or new class: 123 files reach no tree node.** Every held-out task is a known algorithm, so all 123 are
  programs the lowering or the interpreter cannot handle, not new classes (57 Haskell, 41 Python, 15 C, 10 Lisp).
- The identified answers (algorithm or class) are unchanged: 169 correct, 10 wrong, all 10 the pipeline's own.
  Proposed branches (benchmark/proposed_fallback.md) answered 2 files the pipeline missed, both right, and those 2
  are among the class answers here.
