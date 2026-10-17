# v0.2 learning test (learn_v2.py: AST normalisation + winnowing, nearest neighbour)

Learned from 76 labelled files (55 + 15 + 6), 105 functions. TheAlgorithms/Python @ 25c712f2.

| Test | Precision | Recall | Wrong on negatives | Meaning |
|---|---|---|---|---|
| same 55 after learning | 36/36 = 100% | 36/38 = 94.7% | 0/17 | memorisation |
| leave-one-out on the 55 | 19/23 = 82.6% | 19/38 = 50.0% | 0/17 | honest estimate |
| fresh 55 (key frozen first) | 9/11 = 81.8% | 9/25 = 36.0% | 0/30 | real test: **not met** |

Note: polyglot_logic (AP13) already contains learners (learn-dir traced references; io_catalog behaviour catalog). learn_v2.py duplicates that idea and should be replaced by reusing them.

## fresh 55
```
file                                   expected                       outcome   routes
sorts/bitonic_sort.py                  comparison_driven_reordering   WRONG     sequence_rearrangement 
sorts/cycle_sort.py                    ['sequence_rearrangement', 'co UNKNOWN   - 
sorts/cyclic_sort.py                   sequence_rearrangement         ok        sequence_rearrangement 
sorts/double_sort.py                   comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/odd_even_transposition_single_threaded.py comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/pancake_sort.py                  ['sequence_rearrangement', 'co UNKNOWN   - 
sorts/reverse_selection.py             ['sequence_rearrangement', 'co ok        comparison_driven_reordering,selection_exchange,sequence_rearrangement 
sorts/shrink_shell_sort.py             comparison_driven_reordering   UNKNOWN   - 
sorts/slowsort.py                      comparison_driven_reordering   ok        comparison_driven_reordering,sequence_rearrangement 
sorts/intro_sort.py                    ['comparison_driven_reordering ok        comparison_driven_reordering,sequence_rearrangement,shift_insertion 
sorts/quick_sort_3_partition.py        comparison_driven_reordering   WRONG     recursive_decomposition,sequence_rearrangement 
maths/least_common_multiple.py         euclid_like                    UNKNOWN   - 
maths/extended_euclidean_algorithm.py  euclid_like                    UNKNOWN   - 
maths/lucas_series.py                  fibonacci_like                 ok        fibonacci_like,recurrence,recursive_decomposition 
maths/padovan_sequence.py              recurrence                     UNKNOWN   - 
maths/pell_number.py                   recurrence                     ok        fibonacci_like,recurrence,recursive_decomposition 
maths/sylvester_sequence.py            recurrence                     UNKNOWN   - 
maths/persistence.py                   digit_processing               UNKNOWN   - 
maths/disarium.py                      digit_processing               UNKNOWN   - 
maths/keith_number.py                  digit_processing               UNKNOWN   - 
maths/remove_digit.py                  digit_processing               UNKNOWN   - 
maths/sieve_of_atkin.py                sieve_like                     UNKNOWN   - 
maths/primelib.py                      ['divisor_search', 'sieve_like ok        divisor_search,factorial_like,number_property,recurrence 
maths/average_mean.py                  ['aggregate', 'element_accumul UNKNOWN   - 
strings/manacher.py                    ['symmetric_compare', 'palindr UNKNOWN   - 
strings/edit_distance.py               None                           ok(neg)   - 
maths/ceil.py                          None                           ok(neg)   - 
maths/euclidean_distance.py            None                           ok(neg)   - 
maths/manhattan_distance.py            None                           ok(neg)   - 
maths/addition_without_arithmetic.py   None                           ok(neg)   - 
maths/decimal_isolate.py               None                           ok(neg)   - 
maths/bearing.py                       None                           ok(neg)   - 
sorts/pigeon_sort.py                   None                           ok(neg)   - 
strings/word_occurrence.py             None                           ok(neg)   - 
strings/check_anagrams.py              None                           ok(neg)   - 
maths/area.py                          None                           ok(neg)   - 
strings/is_pangram.py                  None                           ok(neg)   - 
maths/perfect_square.py                None                           ok(neg)   - 
strings/strip.py                       None                           ok(neg)   - 
strings/anagrams.py                    None                           ok(neg)   - 
strings/pig_latin.py                   None                           ok(neg)   - 
maths/entropy.py                       None                           ok(neg)   - 
maths/check_polygon.py                 None                           ok(neg)   - 
maths/trapezoidal_rule.py              None                           ok(neg)   - 
maths/chebyshev_distance.py            None                           ok(neg)   - 
maths/line_length.py                   None                           ok(neg)   - 
strings/remove_duplicate.py            None                           ok(neg)   - 
strings/capitalize.py                  None                           ok(neg)   - 
strings/count_vowels.py                None                           ok(neg)   - 
maths/gaussian.py                      None                           ok(neg)   - 
maths/binary_multiplication.py         None                           ok(neg)   - 
maths/monte_carlo_dice.py              None                           ok(neg)   - 
maths/pythagoras.py                    None                           ok(neg)   - 
strings/dna.py                         None                           ok(neg)   - 
maths/jaccard_similarity.py            None                           ok(neg)   - 

PRECISION = correct / answered = 9/11 = 81.8%
RECALL    = correct / positives = 9/25 = 36.0%
WRONG ON NEGATIVES = 0 of 30
```
