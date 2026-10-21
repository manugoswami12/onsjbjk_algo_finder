# Rosetta: learned on the same files, then re-run (memorisation test, as requested)

Popper is not used. Learners: learn_v2 (nearest neighbour, kb/learned.json, 431 functions) + original AP13 io_catalog, both trained on 395 labelled files (232 TheAlgorithms + the 163 Rosetta test files themselves).

| System | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| before learning Rosetta | 27/27 = 100% | 27/107 = 25.2% | 0/56 |
| after learning Rosetta (same files) | 70/72 = 97.2% | 70/107 = 65.4% | 2/56 |
| same, parseable files only (21 Python 2 files excluded) | 70/72 = 97.2% | 70/86 = 81.4% | 2/56 |

This measures memorisation of seen files, not recognition of new code (see final101_result.md / popper_rosetta_result.md for held-out numbers).

```
<unknown>:1: SyntaxWarning: invalid escape sequence '\w'
<unknown>:14: SyntaxWarning: invalid escape sequence '\w'
<unknown>:14: SyntaxWarning: invalid escape sequence '\w'
<unknown>:1: SyntaxWarning: invalid escape sequence '\w'
file                                   expected                       outcome   routes
Task/Ackermann-function/Python/ackermann-function-1.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-2.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-3.py None                           ok(neg)   - not parseable: invalid syntax
Task/Ackermann-function/Python/ackermann-function-4.py None                           ok(neg)   - 
Task/Ackermann-function/Python/ackermann-function-5.py None                           ok(neg)   - 
Task/Binary-search/Python/binary-search-1.py ['interval_lookup', 'indexed_l ok        indexed_lookup,interval_lookup 
Task/Binary-search/Python/binary-search-2.py ['interval_lookup', 'indexed_l ok        indexed_lookup,interval_lookup 
Task/Binary-search/Python/binary-search-3.py ['interval_lookup', 'indexed_l ok        indexed_lookup,interval_lookup 
Task/Binary-search/Python/binary-search-4.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-5.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-6.py ['interval_lookup', 'indexed_l UNKNOWN   - 
Task/Binary-search/Python/binary-search-7.py ['interval_lookup', 'indexed_l ok        indexed_lookup,interval_lookup 
Task/Caesar-cipher/Python/caesar-cipher-1.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Caesar-cipher/Python/caesar-cipher-2.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Caesar-cipher/Python/caesar-cipher-3.py None                           ok(neg)   - 
Task/Caesar-cipher/Python/caesar-cipher-4.py None                           ok(neg)   - 
Task/Dot-product/Python/dot-product-1.py ['aggregate', 'element_accumul ok        aggregate 
Task/Dot-product/Python/dot-product-2.py ['aggregate', 'element_accumul ok        aggregate 
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
Task/Fibonacci-sequence/Python/fibonacci-sequence-10.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-11.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-12.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-13.py fibonacci_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-14.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-15.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-16.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-17.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-18.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-2.py fibonacci_like                 UNKNOWN   - not parseable: unexpected indent
Task/Fibonacci-sequence/Python/fibonacci-sequence-3.py fibonacci_like                 UNKNOWN   - not parseable: invalid syntax
Task/Fibonacci-sequence/Python/fibonacci-sequence-4.py fibonacci_like                 UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Fibonacci-sequence/Python/fibonacci-sequence-5.py fibonacci_like                 ok        fibonacci_like,recurrence,recursive_decomposition 
Task/Fibonacci-sequence/Python/fibonacci-sequence-6.py fibonacci_like                 UNKNOWN   - 
Task/Fibonacci-sequence/Python/fibonacci-sequence-7.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-8.py fibonacci_like                 ok        fibonacci_like,recurrence 
Task/Fibonacci-sequence/Python/fibonacci-sequence-9.py fibonacci_like                 UNKNOWN   - not parseable: invalid syntax
Task/Greatest-common-divisor/Python/greatest-common-divisor-1.py euclid_like                    UNKNOWN   - 
Task/Greatest-common-divisor/Python/greatest-common-divisor-2.py euclid_like                    UNKNOWN   - 
Task/Greatest-common-divisor/Python/greatest-common-divisor-3.py euclid_like                    ok        euclid_like,recurrence 
Task/Greatest-common-divisor/Python/greatest-common-divisor-4.py euclid_like                    ok        euclid_like,recurrence 
Task/Greatest-common-divisor/Python/greatest-common-divisor-5.py euclid_like                    ok        euclid_like,recurrence 
Task/Hailstone-sequence/Python/hailstone-sequence-1.py collatz_like                   ok        collatz_like,number_property 
Task/Hailstone-sequence/Python/hailstone-sequence-2.py collatz_like                   ok        collatz_like,number_property 
Task/Hailstone-sequence/Python/hailstone-sequence-3.py collatz_like                   ok        collatz_like,number_property 
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
Task/Least-common-multiple/Python/least-common-multiple-2.py euclid_like                    ok        aggregate,euclid_like,recurrence 
Task/Least-common-multiple/Python/least-common-multiple-3.py euclid_like                    ok        euclid_like,recurrence 
Task/Least-common-multiple/Python/least-common-multiple-4.py euclid_like                    UNKNOWN   - not parseable: invalid syntax
Task/Least-common-multiple/Python/least-common-multiple-5.py euclid_like                    UNKNOWN   - not parseable: invalid syntax
Task/Levenshtein-distance/Python/levenshtein-distance-1.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-2.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-3.py None                           ok(neg)   - 
Task/Levenshtein-distance/Python/levenshtein-distance-4.py None                           ok(neg)   - not parseable: invalid syntax
Task/Levenshtein-distance/Python/levenshtein-distance-5.py None                           ok(neg)   - 
Task/Longest-common-subsequence/Python/longest-common-subsequence-1.py None                           ok(neg)   - 
Task/Longest-common-subsequence/Python/longest-common-subsequence-2.py None                           ok(neg)   - 
Task/Longest-common-subsequence/Python/longest-common-subsequence-3.py None                           ok(neg)   - 
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-1.py ['digit_processing', 'number_p UNKNOWN   - not parseable: invalid syntax
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-2.py ['digit_processing', 'number_p UNKNOWN   - 
Task/Luhn-test-of-credit-card-numbers/Python/luhn-test-of-credit-card-numbers-3.py ['digit_processing', 'number_p ok        digit_processing,number_property 
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
Task/N-queens-problem/Python/n-queens-problem-8.py None                           WRONG     aggregate 
Task/N-queens-problem/Python/n-queens-problem-9.py None                           ok(neg)   - 
Task/Palindrome-detection/Python/palindrome-detection-1.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-2.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-3.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-4.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-5.py palindrome_check               UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Palindrome-detection/Python/palindrome-detection-6.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-7.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Palindrome-detection/Python/palindrome-detection-8.py palindrome_check               ok        palindrome_check,symmetric_compare 
Task/Perfect-numbers/Python/perfect-numbers-1.py divisor_search                 ok        divisor_search,number_property,recurrence,series_sum 
Task/Perfect-numbers/Python/perfect-numbers-2.py divisor_search                 ok        divisor_search,number_property 
Task/Perfect-numbers/Python/perfect-numbers-3.py divisor_search                 ok        divisor_search,number_property 
Task/Perfect-numbers/Python/perfect-numbers-4.py divisor_search                 ok        divisor_search,number_property 
Task/Primality-by-trial-division/Python/primality-by-trial-division-1.py divisor_search                 ok        divisor_search,number_property 
Task/Primality-by-trial-division/Python/primality-by-trial-division-2.py divisor_search                 ok        divisor_search,number_property 
Task/Primality-by-trial-division/Python/primality-by-trial-division-3.py divisor_search                 ok        divisor_search,number_property 
Task/Primality-by-trial-division/Python/primality-by-trial-division-4.py divisor_search                 UNKNOWN   - not parseable: invalid syntax
Task/Roman-numerals-Encode/Python/roman-numerals-encode-1.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-2.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-3.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-4.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-5.py None                           ok(neg)   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Roman-numerals-Encode/Python/roman-numerals-encode-6.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-7.py None                           ok(neg)   - 
Task/Roman-numerals-Encode/Python/roman-numerals-encode-8.py None                           WRONG     collatz_like,number_property 
Task/Run-length-encoding/Python/run-length-encoding-1.py None                           ok(neg)   - 
Task/Run-length-encoding/Python/run-length-encoding-2.py None                           ok(neg)   - 
Task/Run-length-encoding/Python/run-length-encoding-3.py None                           ok(neg)   - 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-1.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-10.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-11.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-12.py sieve_like                     UNKNOWN   - not parseable: invalid syntax
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-13.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-14.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-15.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-16.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-2.py sieve_like                     ok        divisor_search,marking,number_property,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-3.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-4.py sieve_like                     UNKNOWN   - not parseable: invalid syntax
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-5.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-6.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-7.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-8.py sieve_like                     ok        marking,sieve_like 
Task/Sieve-of-Eratosthenes/Python/sieve-of-eratosthenes-9.py sieve_like                     ok        marking,sieve_like 
Task/Sorting-algorithms-Bubble-sort/Python/sorting-algorithms-bubble-sort.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-1.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-2.py comparison_driven_reordering   UNKNOWN   - not parseable: Missing parentheses in call to 'print'. Did you mean print(...)?
Task/Sorting-algorithms-Cocktail-sort/Python/sorting-algorithms-cocktail-sort-3.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Comb-sort/Python/sorting-algorithms-comb-sort.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Cycle-sort/Python/sorting-algorithms-cycle-sort.py ['sequence_rearrangement', 'co ok        sequence_rearrangement 
Task/Sorting-algorithms-Gnome-sort/Python/sorting-algorithms-gnome-sort.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Heapsort/Python/sorting-algorithms-heapsort.py comparison_driven_reordering   ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-1.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-2.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-3.py shift_insertion                ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-4.py shift_insertion                ok        comparison_driven_reordering,sequence_rearrangement,shift_insertion 
Task/Sorting-algorithms-Pancake-sort/Python/sorting-algorithms-pancake-sort-1.py ['sequence_rearrangement', 'co ok        sequence_rearrangement 
Task/Sorting-algorithms-Pancake-sort/Python/sorting-algorithms-pancake-sort-2.py ['sequence_rearrangement', 'co UNKNOWN   - 
Task/Sorting-algorithms-Selection-sort/Python/sorting-algorithms-selection-sort.py selection_exchange             ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement 
Task/Sorting-algorithms-Shell-sort/Python/sorting-algorithms-shell-sort.py comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
Task/Sorting-algorithms-Stooge-sort/Python/sorting-algorithms-stooge-sort-1.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sorting-algorithms-Stooge-sort/Python/sorting-algorithms-stooge-sort-2.py comparison_driven_reordering   UNKNOWN   - not parseable: invalid syntax
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-1.py digit_processing               ok        digit_processing,number_property 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-2.py digit_processing               ok        digit_processing,number_property 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-3.py digit_processing               ok        digit_processing,number_property 
Task/Sum-digits-of-an-integer/Python/sum-digits-of-an-integer-4.py digit_processing               ok        aggregate,digit_processing,number_property 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-1.py None                           ok(neg)   - 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-2.py None                           ok(neg)   - 
Task/Towers-of-Hanoi/Python/towers-of-hanoi-3.py None                           ok(neg)   - 

PRECISION = correct / answered = 70/72 = 97.2%
RECALL    = correct / positives = 70/107 = 65.4%
WRONG ON NEGATIVES = 2 of 56
```
