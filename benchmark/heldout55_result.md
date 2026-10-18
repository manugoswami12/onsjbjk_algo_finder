# v0.2 held-out result: 55 new files (TheAlgorithms/Python @ 25c712f2), key frozen before run, run once

```
file                                   expected                       outcome   routes
sorts/bubble_sort_recursive.py         comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/exchange_sort.py                 comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/cocktail_shaker_sort.py          comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/gnome_sort.py                    comparison_driven_reordering   WRONG     sequence_rearrangement 
sorts/odd_even_sort.py                 comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/comb_sort.py                     comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/shell_sort.py                    comparison_driven_reordering   UNKNOWN   - 
sorts/binary_insertion_sort.py         shift_insertion                UNKNOWN   - 
sorts/recursive_insertion_sort.py      shift_insertion                WRONG     sequence_rearrangement 
sorts/stooge_sort.py                   comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/circle_sort.py                   comparison_driven_reordering   UNKNOWN   - 
sorts/dutch_national_flag_sort.py      ['sequence_rearrangement', 'co ok        sequence_rearrangement 
sorts/heap_sort.py                     comparison_driven_reordering   WRONG     sequence_rearrangement 
sorts/wiggle_sort.py                   comparison_driven_reordering   WRONG     sequence_rearrangement 
sorts/quick_sort.py                    None                           ok(neg)   recursive_decomposition 
sorts/iterative_merge_sort.py          None                           ok(neg)   - 
sorts/bead_sort.py                     None                           ok(neg)   - 
sorts/pigeonhole_sort.py               None                           ok(neg)   - 
sorts/counting_sort.py                 None                           ok(neg)   - 
sorts/radix_sort.py                    None                           ok(neg)   - 
sorts/bucket_sort.py                   None                           ok(neg)   - not parseable: iterable unpacking cannot be used in comprehension
searches/jump_search.py                indexed_lookup                 UNKNOWN   - 
searches/sentinel_linear_search.py     indexed_lookup                 UNKNOWN   - 
searches/double_linear_search.py       indexed_lookup                 ok        indexed_lookup 
searches/double_linear_search_recursion.py indexed_lookup                 UNKNOWN   - 
searches/ternary_search.py             ['indexed_lookup', 'interval_l ok        indexed_lookup 
searches/interpolation_search.py       ['indexed_lookup', 'interval_l ok        indexed_lookup 
searches/exponential_search.py         interval_lookup                UNKNOWN   - 
searches/fibonacci_search.py           indexed_lookup                 ok        indexed_lookup 
maths/double_factorial.py              recurrence                     ok        factorial_like,recurrence 
maths/power_using_recursion.py         recurrence                     UNKNOWN   - 
maths/digital_root.py                  digit_processing               UNKNOWN   - 
maths/recursive_digit_sum.py           digit_processing               UNKNOWN   - 
maths/is_int_palindrome.py             ['palindrome_check', 'digit_pr ok        digit_processing,number_property 
maths/factors.py                       divisor_search                 ok        divisor_search,number_property 
maths/aliquot_sum.py                   divisor_search                 UNKNOWN   - 
maths/perfect_number.py                divisor_search                 ok        divisor_search,number_property 
maths/prime_numbers.py                 ['divisor_search', 'sieve_like ok        divisor_search,number_property 
maths/next_prime_number.py             divisor_search                 ok        divisor_search,number_property 
maths/twin_prime.py                    divisor_search                 UNKNOWN   - 
maths/germain_primes.py                divisor_search                 UNKNOWN   - 
maths/prime_factors.py                 divisor_search                 UNKNOWN   - 
maths/segmented_sieve.py               sieve_like                     ok        marking,sieve_like 
maths/odd_sieve.py                     sieve_like                     UNKNOWN   - 
maths/gcd_of_n_numbers.py              euclid_like                    UNKNOWN   - 
strings/can_string_be_rearranged_as_palindrome.py None                           ok(neg)   - 
strings/reverse_letters.py             None                           ok(neg)   - 
strings/naive_string_search.py         None                           ok(neg)   - 
strings/min_window_substring.py        None                           ok(neg)   - 
strings/boyer_moore_search.py          None                           ok(neg)   - 
maths/softmax.py                       None                           ok(neg)   - 
maths/minkowski_distance.py            None                           ok(neg)   - 
maths/two_sum.py                       None                           ok(neg)   - 
maths/sumset.py                        None                           ok(neg)   - 
maths/sum_of_geometric_progression.py  None                           ok(neg)   - 

PRECISION = correct / answered = 18/22 = 81.8%
RECALL    = correct / positives = 18/38 = 47.4%
WRONG ON NEGATIVES = 0 of 17
```

All 4 WRONG answers are the correct broad family (`sequence_rearrangement`) without the expected narrow branch: family-level precision 22/22. Success criterion (both > 80%) NOT met: recall 47.4%.

The 15-file set (benchmark/heldout_truth.json) is no longer held-out: it was used for the fixes and now scores 12/12, 0 wrong on negatives.
