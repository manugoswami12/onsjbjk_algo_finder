# Separate Popper fallback: Rosetta test (163 Python files, 36 tasks, key frozen first)

Training for all learners: 232 labelled TheAlgorithms/Python files. Popper v3.1.0 (no-noise mode), 48 rules for 19 branches (kb/popper_rules.json), applied only to files the system leaves UNKNOWN.

| System | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| witnesses + io_catalog | 27/27 = 100% | 27/107 = 25.2% | 0/56 |
| + separate Popper fallback | 30/39 = 76.9% | 30/107 = 28.0% | 4/56 |

Popper fallback: 12 new answers, 3 correct, 9 wrong (rules learned from 1-11 positives overfit, e.g. sieve_like :- cmp_ge_3). Success criterion not met. Recall ceiling: 21 of 107 positive files are Python 2 (not parseable by Python 3.13), 6 have no top-level function.

## With Popper
```
<unknown>:14: SyntaxWarning: invalid escape sequence '\w'
<unknown>:1: SyntaxWarning: invalid escape sequence '\w'
<unknown>:14: SyntaxWarning: invalid escape sequence '\w'
<unknown>:14: SyntaxWarning: invalid escape sequence '\w'
file                                   expected                       outcome   routes
Task/Ackermann-function/Python/ackermann-function-1.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-2.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-3.py None                           ok(neg)   - not parseable: invalid syntax
Task/Ackermann-function/Python/ackermann-function-4.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-5.py None                           WRONG     recurrence popper
Task/Binary-search/Python/binary-search-1.py ['interval_lookup', 'indexed_l ok        indexed_lookup 
Task/Binary-search/Python/binary-search-2.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-3.py ['interval_lookup', 'indexed_l ok        indexed_lookup 
Task/Binary-search/Python/binary-search-4.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-5.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-6.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-7.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Caesar-cipher/Python/caesar-cipher-1.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Caesar-cipher/Python/caesar-cipher-2.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Caesar-cipher/Python/caesar-cipher-3.py None                           ok(neg)   - 
Task/Caesar-cipher/Python/caesar-cipher-4.py None                           ok(neg)   - 
Task/Dot-product/Python/dot-product-1.py ['aggregate', 'element_accumul UNKNOWN   - 
Task/Dot-product/Python/dot-product-2.py ['aggregate', 'element_accumul UNKNOWN   - 
Task/Factorial/Python/factorial-1.py   factorial_like                 UNKNOWN   - 
Task/Factorial/Python/factorial-2.py   factorial_like                 ok        divisor_search,factorial_like,number_property,recurrence 
Task/Factorial/Python/factorial-3.py   factorial_like                 UNKNOWN   - 
Task/Factorial/Python/factorial-4.py   factorial_like                 UNKNOWN   - 
Task/Factorial/Python/factorial-5.py   factorial_like                 UNKNOWN   - 
Task/Factorial/Python/factorial-6.py   factorial_like                 UNKNOWN   - 
Task/Factorial/Python/factorial-7.py   factorial_like                 ok        divisor_search,factorial_like,number_property,recurrence 
Task/Factorial/Python/factorial-8.py   factorial_like                 ok        divisor_search,factorial_like,number_property,recurrence 
Task/Factorial/Python/factorial-9.py   factorial_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-1.py fibonacci_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-10.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-11.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-12.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-13.py fibonacci_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-14.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-15.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-16.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-17.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-18.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-2.py fibonacci_like                 UNKNOWN   - not parseable: unexpected indent
Task/Fibonacci-sequence/Python/fibonacci-sequence-3.py fibonacci_like                 UNKNOWN   - not parseable: invalid syntax
Task/Fibonacci-sequence/Python/fibonacci-sequence-4.py fibonacci_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-5.py fibonacci_like                 ok        fibonacci_like,recurrence,recursive_decomposition 
Task/Fibonacci-sequence/Python/fibonacci-sequence-6.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-7.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-8.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-9.py fibonacci_like                 UNKNOWN   - not parseable: invalid syntax
Task/Greatest-common-divisor/Python/greatest-common-divisor-1.py euclid_like                    UNKNOWN   - 
Task/Greatest-common-divisor/Python/greatest-common-divisor-2.py euclid_like                    UNKNOWN   - 
Task/Greatest-common-divisor/Python/greatest-common-divisor-3.py euclid_like                    ok        euclid_like,recurrence 
Task/Greatest-common-divisor/Python/greatest-common-divisor-4.py euclid_like                    ok        euclid_like,recurrence 
Task/Greatest-common-divisor/Python/greatest-common-divisor-5.py euclid_like                    ok        euclid_like,recurrence 
Task/Hailstone-sequence/Python/hailstone-sequence-1.py collatz_like                   UNKNOWN   - 
Task/Hailstone-sequence/Python/hailstone-sequence-2.py collatz_like                   UNKNOWN   - 
Task/Hailstone-sequence/Python/hailstone-sequence-3.py collatz_like                   UNKNOWN   - 
Task/Josephus-problem/Python/josephus-problem-1.py None                           ok(neg)   - not parseable: invalid syntax
Task/Josephus-problem/Python/josephus-problem-2.py None                           ok(neg)   - not parseable: invalid syntax
Task/Josephus-problem/Python/josephus-problem-3.py None                           ok(neg)   - 
Task/Josephus-problem/Python/josephus-problem-4.py None                           ok(neg)   - 
Task/Knapsack-problem-0-1/Python/knapsack-problem-0-1-1.py None                           ok(neg)   - 
Task/Knapsack-problem-0-1/Python/knapsack-problem-0-1-2.py None                           ok(neg)   - 
Task/Knapsack-problem-0-1/Python/knapsack-problem-0-1-3.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Knapsack-problem-0-1/Python/knapsack-problem-0-1-4.py None                           ok(neg)   - 
Task/Leap-year/Python/leap-year-1.py   None                           ok(neg)   - 
Task/Leap-year/Python/leap-year-2.py   None                           ok(neg)   - 
Task/Leap-year/Python/leap-year-3.py   None                           ok(neg)   - 
Task/Least-common-multiple/Python/least-common-multiple-1.py euclid_like                    UNKNOWN   - not parseable: invalid syntax
Task/Least-common-multiple/Python/least-common-multiple-2.py euclid_like                    ok        euclid_like,recurrence 
Task/Least-common-multiple/Python/least-common-multiple-3.py euclid_like                    UNKNOWN   - 
Task/Least-common-multiple/Python/least-common-multiple-4.py euclid_like                    UNKNOWN   - not parseable: invalid syntax
Task/Least-common-multiple/Python/least-common-multiple-5.py euclid_like                    UNKNOWN   - not parseable: invalid syntax
Task/Levenshtein-distance/Python/levenshtein-distance-1.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-2.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-3.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-4.py None                           ok(neg)   - not parseable: invalid syntax
Task/Levenshtein-distance/Python/levenshtein-distance-5.py None                           WRONG     symmetric_compare popper
Task/Longest-common-subsequence/Python/longest-common-subsequence-1.py None                           ok(neg)   - 
Task/Longest-common-subsequence/Python/longest-common-subsequence-2.py None                           ok(neg)   - 
Task/Longest-common-subsequence/Python/longest-common-subsequence-3.py None                           ok(neg)   - 
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-1.py ['digit_processing', 'number_p UNKNOWN   - not parseable: invalid syntax
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-2.py ['digit_processing', 'number_p UNKNOWN   - 
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-3.py ['digit_processing', 'number_p UNKNOWN   - 
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-4.py ['digit_processing', 'number_p UNKNOWN   - not parseable: invalid syntax
Task/Matrix-multiplication/Python/matrix-multiplication-1.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Matrix-multiplication/Python/matrix-multiplication-2.py None                           ok(neg)   - 
Task/Matrix-multiplication/Python/matrix-multiplication-3.py None                           ok(neg)   - 
Task/Matrix-multiplication/Python/matrix-multiplication-4.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-1.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-10.py None                           ok(neg)   - not parseable: invalid syntax
Task/N-queens-problem/Python/n-queens-problem-2.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-3.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-4.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-5.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-6.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-7.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-8.py None                           ok(neg)   - 
Task/N-queens-problem/Python/n-queens-problem-9.py None                           ok(neg)   - 
Task/Palindrome-detection/Python/palindrome-detection-1.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-2.py palindrome_check               UNKNOWN   - 
Task/Palindrome-detection/Python/palindrome-detection-3.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-4.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-5.py palindrome_check               UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Palindrome-detection/Python/palindrome-detection-6.py palindrome_check               WRONG     fibonacci_like,recurrence popper
Task/Palindrome-detection/Python/palindrome-detection-7.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-8.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Perfect-numbers/Python/perfect-numbers-1.py divisor_search                 ok        divisor_search,number_property,recurrence,series_sum 
Task/Perfect-numbers/Python/perfect-numbers-2.py divisor_search                 WRONG     euclid_like,recurrence popper
Task/Perfect-numbers/Python/perfect-numbers-3.py divisor_search                 UNKNOWN   - 
Task/Perfect-numbers/Python/perfect-numbers-4.py divisor_search                 UNKNOWN   - 
Task/Primality-by-trial-division/Python/primality-by-trial-division-1.py divisor_search                 UNKNOWN   - 
Task/Primality-by-trial-division/Python/primality-by-trial-division-2.py divisor_search                 UNKNOWN   - 
Task/Primality-by-trial-division/Python/primality-by-trial-division-3.py divisor_search                 ok        divisor_search,number_property 
Task/Primality-by-trial-division/Python/primality-by-trial-division-4.py divisor_search                 UNKNOWN   - not parseable: invalid syntax
Task/Roman-numerals-Encode/Python/roman-numerals-encode-1.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-2.py None                           WRONG     digit_processing,number_property popper
Task/Roman-numerals-Encode/Python/roman-numerals-encode-3.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-4.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-5.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-6.py None                           WRONG     comparison_driven_reordering,sequence_rearrangement popper
Task/Roman-numerals-Encode/Python/roman-numerals-encode-7.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-8.py None                           ok(neg)   - 
Task/Run-length-encoding/Python/run-length-encoding-1.py None                           ok(neg)   - 
Task/Run-length-encoding/Python/run-length-encoding-2.py None                           ok(neg)   - 
Task/Run-length-encoding/Python/run-length-encoding-3.py None                           ok(neg)   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-1.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-10.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-11.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-12.py sieve_like                     UNKNOWN   - not parseable: invalid syntax
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-13.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-14.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-15.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-16.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-2.py sieve_like                     ok        divisor_search,marking,number_property,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-3.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-4.py sieve_like                     UNKNOWN   - not parseable: invalid syntax
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-5.py sieve_like                     WRONG     recurrence popper
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-6.py sieve_like                     WRONG     recurrence popper
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-7.py sieve_like                     UNKNOWN   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-8.py sieve_like                     ok        marking,sieve_like popper
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-9.py sieve_like                     WRONG     comparison_driven_reordering,sequence_rearrangement,symmetric_compare popper popper popper
Task/Sorting-algorithms-Bubble-sort/Python/sorting-algorithms-bubble-sort.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-1.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-2.py comparison_driven_reordering   UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-3.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Comb-sort/Python/sorting-algorithms-comb-sort.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Cycle-sort/Python/sorting-algorithms-cycle-sort.py ['sequence_rearrangement', 'co UNKNOWN   - 
Task/Sorting-algorithms-Gnome-sort/Python/sorting-algorithms-gnome-sort.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Heapsort/Python/sorting-algorithms-heapsort.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-1.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-2.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-3.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-4.py shift_insertion                UNKNOWN   - 
Task/Sorting-algorithms-Pancake-sort/Python/sorting-algorithms-pancake-sort-1.py ['sequence_rearrangement', 'co ok        sequence_rearrangement popper
Task/Sorting-algorithms-Pancake-sort/Python/sorting-algorithms-pancake-sort-2.py ['sequence_rearrangement', 'co UNKNOWN   - 
Task/Sorting-algorithms-Selection-sort/Python/sorting-algorithms-selection-sort.py selection_exchange             UNKNOWN   - 
Task/Sorting-algorithms-Shell-sort/Python/sorting-algorithms-shell-sort.py comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement popper
Task/Sorting-algorithms-Stooge-sort/Python/sorting-algorithms-stooge-sort-1.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Stooge-sort/Python/sorting-algorithms-stooge-sort-2.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-1.py digit_processing               UNKNOWN   - 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-2.py digit_processing               UNKNOWN   - 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-3.py digit_processing               UNKNOWN   - 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-4.py digit_processing               UNKNOWN   - 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-1.py None                           ok(neg)   - 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-2.py None                           ok(neg)   - 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-3.py None                           ok(neg)   - 

PRECISION = correct / answered = 30/39 = 76.9%
RECALL    = correct / positives = 30/107 = 28.0%
WRONG ON NEGATIVES = 4 of 56
```
