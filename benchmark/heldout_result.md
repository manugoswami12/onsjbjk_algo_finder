# v0.2 held-out result (15 files, TheAlgorithms/Python @ 25c712f2, run once, no tuning)

```
file                                   expected                       outcome   routes
sorts/bubble_sort.py                   comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/insertion_sort.py                shift_insertion                ok        comparison_driven_reordering,sequence_rearrangement,shift_insertion 
sorts/selection_sort.py                selection_exchange             ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement 
searches/linear_search.py              indexed_lookup                 UNKNOWN   - 
searches/simple_binary_search.py       interval_lookup                WRONG     membership_lookup 
maths/fibonacci.py                     fibonacci_like                 UNKNOWN   - 
maths/sieve_of_eratosthenes.py         sieve_like                     UNKNOWN   - 
maths/prime_sieve_eratosthenes.py      sieve_like                     UNKNOWN   - 
strings/palindrome.py                  palindrome_check               ok        palindrome_check,symmetric_compare 
maths/find_max.py                      extremum_search                ok        aggregate,extremum_search 
maths/find_min.py                      extremum_search                UNKNOWN   - 
maths/number_of_digits.py              digit_processing               UNKNOWN   - 
sorts/merge_sort.py                    None                           ok(neg)   recursive_decomposition 
strings/reverse_words.py               None                           ok(neg)   - 
strings/hamming_distance.py            None                           ok(neg)   - 

PRECISION = correct / answered = 5/6 = 83.3%
RECALL    = correct / positives = 5/12 = 41.7%
WRONG ON NEGATIVES = 0 of 3
```

## Misses, explained from the trace (not fixed; any fix needs a fresh held-out set)

| File | Why |
|---|---|
| linear_search | `for index, item in enumerate(seq)`: enumerate pairs not traced |
| simple_binary_search | recursive halving on slices returning bool -> routed `membership_lookup` (family plausible, frozen narrow label wrong) |
| sieve_of_eratosthenes, prime_sieve_eratosthenes | outer stepper is `while p*p <= n: ... p += 1`, witness needs `for p in` |
| fibonacci (fib_iterative) | list recurrence `fib.append(fib[-1] + fib[-2])`, witness needs `a, b = b, a + b` |
| number_of_digits | `while True` + `n //= 10` + break; counts digits without `n % 10` |
| find_min | form not covered by best-so-far witness |

## Earlier small checks
- 3 random files before fixes: 2 ok, 1 UNKNOWN (binary_search via follower variable; factorial_recursive inline base case) -> both fixed as witnesses.
- 3 random files after fixes: prime_check ok, sum_of_digits ok, greatest_common_divisor not parseable by Python 3.13 (uses 3.14 `except A, B:`).
