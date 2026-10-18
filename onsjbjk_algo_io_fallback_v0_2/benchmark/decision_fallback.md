# Four-way answer test (doc 04 section 18.2): held-out Rosetta files

Each file gets one answer: the algorithm (eval_ta.py), else its class (a class relation on runs over every battery input, or a library name), else "new or incorrect implementation" (runs fully, no relation), else "not identified". Separate from the pipeline (eval_decision.py).

| language | files | algorithm | class | correct / wrong (algorithm + class) | precision | identified (recall) | new or incorrect | not identified | answered (any of the four but not identified) |
|---|---|---|---|---|---|---|---|---|---|
| C | 69 | 32 | 0 | 31 / 1 | 96.9% | 44.9% | 2 | 35 | 49.3% |
| Common-Lisp | 75 | 43 | 2 | 44 / 1 | 97.8% | 58.7% | 1 | 29 | 61.3% |
| Haskell | 144 | 31 | 4 | 33 / 2 | 94.3% | 22.9% | 5 | 104 | 27.8% |
| Python | 162 | 62 | 5 | 61 / 6 | 91.0% | 37.7% | 7 | 88 | 45.7% |
| all | 450 | 168 | 11 | 169 / 10 | 94.4% | 37.6% | 15 | 256 | 43.1% |

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

## "New or incorrect implementation" (15; every held-out task is known, so each is an implementation we cannot check)

- Task/Binary-search/Python/binary-search-7.py (task Binary-search)
- Task/Factorial/C/factorial-5.c (task Factorial)
- Task/Factorial/Haskell/factorial-10.hs (task Factorial)
- Task/Factorial/Haskell/factorial-2.hs (task Factorial)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-1.py (task Fibonacci-sequence)
- Task/Levenshtein-distance/Haskell/levenshtein-distance-2.hs (task Levenshtein-distance)
- Task/Levenshtein-distance/Python/levenshtein-distance-2.py (task Levenshtein-distance)
- Task/Palindrome-detection/C/palindrome-detection-3.c (task Palindrome-detection)
- Task/Primality-by-trial-division/Common-Lisp/primality-by-trial-division-2.lisp (task Primality-by-trial-division)
- Task/Roman-numerals-Encode/Haskell/roman-numerals-encode-1.hs (task Roman-numerals-Encode)
- Task/Sorting-algorithms-Cycle-sort/Python/sorting-algorithms-cycle-sort.py (task Sorting-algorithms-Cycle-sort)
- Task/Sorting-algorithms-Quicksort/Python/sorting-algorithms-quicksort-5.py (task Sorting-algorithms-Quicksort)
- Task/Sorting-algorithms-Selection-sort/Python/sorting-algorithms-selection-sort.py (task Sorting-algorithms-Selection-sort)
- Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-2.py (task Sum-digits-of-an-integer)
- Task/Towers-of-Hanoi/Haskell/towers-of-hanoi-1.hs (task Towers-of-Hanoi)

## Class decisions on TheAlgorithms/Python files (36), to check by hand

- **gcd** (1): maths/greatest_common_divisor.py
- **power** (2): divide_and_conquer/power.py, maths/power_using_recursion.py
- **search** (2): searches/double_linear_search.py, searches/jump_search.py
- **sorting** (31): divide_and_conquer/mergesort.py, sorts/adaptive_merge_sort.py, sorts/binary_insertion_sort.py, sorts/bubble_sort.py, sorts/bubble_sort_recursive.py, sorts/circle_sort.py, sorts/cocktail_shaker_sort.py, sorts/comb_sort.py, sorts/cycle_sort.py, sorts/double_sort.py, sorts/exchange_sort.py, sorts/gnome_sort.py, sorts/heap_sort.py, sorts/insertion_sort.py, sorts/iterative_merge_sort.py, sorts/merge_insertion_sort.py, sorts/merge_sort.py, sorts/odd_even_sort.py, sorts/odd_even_transposition_single_threaded.py, sorts/pancake_sort.py, sorts/pigeon_sort.py, sorts/pigeonhole_sort.py, sorts/quick_sort.py, sorts/recursive_insertion_sort.py, sorts/recursive_quick_sort.py, sorts/reverse_selection.py, sorts/selection_sort.py, sorts/shell_sort.py, sorts/shrink_shell_sort.py, sorts/stooge_sort.py, sorts/tim_sort.py

## Class decisions on TheAlgorithms/Python files dropped by node agreement (2)

- maths/average_mode.py: sorting, nodes []
- maths/special_numbers/triangular_numbers.py: triangular, nodes []

## Notes on the corrected run (Haskell local helpers by indentation, strict roots; witness = the file reaches a node)

| second witness | held-out class answers | wrong | held-out recall | TheAlgorithms class claims | false positives |
|---|---|---|---|---|---|
| none | 14 | 0 | 38.2 % | 38 | 1 (average_mode) |
| the file reaches a tree node (this report) | 11 | 0 | 37.6 % | 36 | 0 |
| node agreement with another TheAlgorithms file of the class | 11 | 0 | 37.6 % | 35 | 0 (also drops gcd, a singleton) |

- The class decision itself (before any witness) fired on 35 held-out files, and the class was right on all 35.
- **average_mode** is an interpreter error: `mode()` is computed as a full sort. It reaches no tree node, so the node
  witness drops it. The same witness drops 3 correct held-out prime_check files, which also reach no node. So the
  safety costs 3 files (0.6 % recall).
- The 10 wrong answers on the held-out files are the main pipeline's algorithm answers. None comes from this fallback.
