# Four-way answer test (doc 04 section 18.2): held-out Rosetta files

Each file gets one answer: the algorithm (eval_ta.py), else its class (a class relation on runs over every battery input, or a library name), else "new or incorrect implementation" (runs fully, no relation), else "not identified". Separate from the pipeline (eval_decision.py).

| language | files | algorithm | class | correct / wrong (algorithm + class) | precision | identified (recall) | new or incorrect | not identified | answered (any of the four but not identified) |
|---|---|---|---|---|---|---|---|---|---|
| C | 69 | 32 | 0 | 31 / 1 | 96.9% | 44.9% | 4 | 33 | 52.2% |
| Common-Lisp | 75 | 43 | 2 | 44 / 1 | 97.8% | 58.7% | 1 | 29 | 61.3% |
| Haskell | 144 | 31 | 6 | 35 / 2 | 94.6% | 24.3% | 9 | 98 | 31.9% |
| Python | 162 | 62 | 6 | 62 / 6 | 91.2% | 38.3% | 13 | 81 | 50.0% |
| all | 450 | 168 | 14 | 172 / 10 | 94.5% | 38.2% | 27 | 241 | 46.4% |

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

## "New or incorrect implementation" (27; every held-out task is known, so each is an implementation we cannot check)

- Task/Binary-search/Python/binary-search-7.py (task Binary-search)
- Task/Factorial/C/factorial-5.c (task Factorial)
- Task/Factorial/Haskell/factorial-10.hs (task Factorial)
- Task/Factorial/Haskell/factorial-2.hs (task Factorial)
- Task/Fibonacci-sequence/Python/fibonacci-sequence-1.py (task Fibonacci-sequence)
- Task/Hailstone-sequence/Haskell/hailstone-sequence-1.hs (task Hailstone-sequence)
- Task/Hailstone-sequence/Python/hailstone-sequence-3.py (task Hailstone-sequence)
- Task/Levenshtein-distance/Haskell/levenshtein-distance-2.hs (task Levenshtein-distance)
- Task/Levenshtein-distance/Python/levenshtein-distance-2.py (task Levenshtein-distance)
- Task/Longest-common-subsequence/Haskell/longest-common-subsequence-5.hs (task Longest-common-subsequence)
- Task/Palindrome-detection/C/palindrome-detection-3.c (task Palindrome-detection)
- Task/Primality-by-trial-division/Common-Lisp/primality-by-trial-division-2.lisp (task Primality-by-trial-division)
- Task/Roman-numerals-Encode/Haskell/roman-numerals-encode-1.hs (task Roman-numerals-Encode)
- Task/Run-length-encoding/Haskell/run-length-encoding-4.hs (task Run-length-encoding)
- Task/Run-length-encoding/Python/run-length-encoding-1.py (task Run-length-encoding)
- Task/Sieve-of-Eratosthenes/Haskell/sieve-of-eratosthenes-7.hs (task Sieve-of-Eratosthenes)
- Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-9.py (task Sieve-of-Eratosthenes)
- Task/Sorting-algorithms-Cocktail-sort/C/sorting-algorithms-cocktail-sort-3.c (task Sorting-algorithms-Cocktail-sort)
- Task/Sorting-algorithms-Cycle-sort/Python/sorting-algorithms-cycle-sort.py (task Sorting-algorithms-Cycle-sort)
- Task/Sorting-algorithms-Heapsort/C/sorting-algorithms-heapsort.c (task Sorting-algorithms-Heapsort)
- Task/Sorting-algorithms-Quicksort/Python/sorting-algorithms-quicksort-5.py (task Sorting-algorithms-Quicksort)
- Task/Sorting-algorithms-Selection-sort/Python/sorting-algorithms-selection-sort.py (task Sorting-algorithms-Selection-sort)
- Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-2.py (task Sum-digits-of-an-integer)
- Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-4.py (task Sum-digits-of-an-integer)
- Task/Towers-of-Hanoi/Haskell/towers-of-hanoi-1.hs (task Towers-of-Hanoi)
- Task/Towers-of-Hanoi/Python/towers-of-hanoi-2.py (task Towers-of-Hanoi)
- Task/Towers-of-Hanoi/Python/towers-of-hanoi-3.py (task Towers-of-Hanoi)

## Class decisions on TheAlgorithms/Python files (57), to check by hand

- **digit_sum** (3): maths/sum_of_digits.py, project_euler/problem_020/sol1.py, project_euler/problem_065/sol1.py
- **gcd** (1): maths/greatest_common_divisor.py
- **is_even** (1): bit_manipulation/is_even.py
- **lcm** (1): maths/least_common_multiple.py
- **palindrome_check** (1): strings/palindrome.py
- **perfect_number** (1): maths/perfect_number.py
- **power** (3): divide_and_conquer/power.py, maths/binary_exponentiation.py, maths/power_using_recursion.py
- **prime_check** (3): ciphers/rabin_miller.py, maths/next_prime_number.py, project_euler/problem_060/sol1.py
- **search** (2): searches/double_linear_search.py, searches/jump_search.py
- **sorting** (35): divide_and_conquer/mergesort.py, maths/average_mode.py, sorts/adaptive_merge_sort.py, sorts/binary_insertion_sort.py, sorts/bubble_sort.py, sorts/bubble_sort_recursive.py, sorts/circle_sort.py, sorts/cocktail_shaker_sort.py, sorts/comb_sort.py, sorts/counting_sort.py, sorts/cycle_sort.py, sorts/double_sort.py, sorts/exchange_sort.py, sorts/gnome_sort.py, sorts/heap_sort.py, sorts/insertion_sort.py, sorts/intro_sort.py, sorts/iterative_merge_sort.py, sorts/merge_insertion_sort.py, sorts/merge_sort.py, sorts/odd_even_sort.py, sorts/odd_even_transposition_single_threaded.py, sorts/pancake_sort.py, sorts/pigeon_sort.py, sorts/pigeonhole_sort.py, sorts/quick_sort.py, sorts/quick_sort_3_partition.py, sorts/recursive_insertion_sort.py, sorts/recursive_quick_sort.py, sorts/reverse_selection.py, sorts/selection_sort.py, sorts/shell_sort.py, sorts/shrink_shell_sort.py, sorts/stooge_sort.py, sorts/tim_sort.py
- **square** (4): maths/area.py, maths/numerical_analysis/integration_by_simpson_approx.py, maths/numerical_analysis/simpson_rule.py, maths/trapezoidal_rule.py
- **triangular** (2): maths/special_numbers/triangular_numbers.py, matrix/matrix_based_game.py
