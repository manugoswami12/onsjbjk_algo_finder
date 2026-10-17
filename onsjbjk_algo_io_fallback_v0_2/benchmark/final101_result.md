# Final test: 101 new files (TheAlgorithms/Python @ 25c712f2), key frozen and committed before the run

Learner: original AP13 io_catalog, trained on all 131 labelled files; plus v0.2 witnesses.

| System | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| v0.2 witnesses + io_catalog | 8/12 = 66.7% | 8/24 = 33.3% | 3/77 |
| v0.2 witnesses only | 5/9 = 55.6% | 5/24 = 20.8% | 3/77 |

**Success criterion (precision and recall both > 80%): NOT met.**

The 3 wrong negatives (md5, caesar_cipher, atbash) come from the accumulation witness firing on string building (`out += ch`). minimum_element_of_array got only the broad sequence family.

```
file                                   expected                       outcome   routes
dynamic_programming/factorial.py       ['factorial_like', 'recurrence ok        divisor_search,factorial_like,number_property,recurrence 
dynamic_programming/fibonacci.py       fibonacci_like                 UNKNOWN   - 
dynamic_programming/fast_fibonacci.py  fibonacci_like                 UNKNOWN   - 
dynamic_programming/tribonacci.py      recurrence                     UNKNOWN   - 
matrix/nth_fibonacci_using_matrix_exponentiation.py fibonacci_like                 ok        fibonacci_like,recurrence 
divide_and_conquer/minimum_element_of_array.py ['extremum_search', 'aggregate WRONG     sequence_rearrangement 
divide_and_conquer/power.py            recurrence                     ok        recurrence 
maths/binary_exponentiation.py         recurrence                     ok        recurrence 
maths/modular_exponential.py           recurrence                     UNKNOWN   - 
maths/geometric_mean.py                ['aggregate', 'element_accumul UNKNOWN   - 
maths/weighted_average.py              ['aggregate', 'element_accumul UNKNOWN   - 
maths/average_absolute_deviation.py    ['aggregate', 'element_accumul UNKNOWN   - 
maths/sum_of_harmonic_series.py        ['series_sum', 'recurrence']   UNKNOWN   - 
maths/sum_of_arithmetic_series.py      ['series_sum', 'recurrence']   UNKNOWN   - 
maths/reverse_factorial_recursive.py   ['factorial_like', 'recurrence UNKNOWN   - 
matrix/binary_search_matrix.py         ['interval_lookup', 'indexed_l UNKNOWN   - 
matrix/searching_in_sorted_matrix.py   ['indexed_lookup', 'membership UNKNOWN   - 
other/guess_the_number_search.py       ['interval_lookup', 'indexed_l UNKNOWN   - 
sorts/reversort.py                     ['sequence_rearrangement', 'co UNKNOWN   - 
sorts/smoothsort.py                    ['comparison_driven_reordering ok        sequence_rearrangement 
sorts/flash_sort.py                    ['comparison_driven_reordering UNKNOWN   - 
maths/chinese_remainder_theorem.py     euclid_like                    ok        euclid_like,recurrence 
maths/modular_division.py              euclid_like                    ok        euclid_like,recurrence 
maths/hardy_ramanujanalgo.py           divisor_search                 ok        divisor_search,number_property 
machine_learning/loss_functions.py     None                           ok(neg)   - 
physics/speeds_of_gas_molecules.py     None                           ok(neg)   - 
graphs/graph_centrality.py             None                           ok(neg)   - 
computer_vision/pooling_functions.py   None                           ok(neg)   - 
digital_image_processing/convert_to_negative.py None                           ok(neg)   - 
machine_learning/q_learning.py         None                           ok(neg)   - 
searches/simulated_annealing.py        None                           ok(neg)   - 
conversions/temperature_conversions.py None                           ok(neg)   - 
graphs/connected_components.py         None                           ok(neg)   - 
other/alternative_list_arrange.py      None                           ok(neg)   - 
graphs/eulerian_path_and_circuit_for_undirected_graph.py None                           ok(neg)   - 
blockchain/simple_proof_of_work.py     None                           ok(neg)   - 
neural_network/perceptron.py           None                           ok(neg)   - 
maths/line_intersection.py             None                           ok(neg)   - 
ciphers/porta_cipher.py                None                           ok(neg)   - 
strings/autocomplete_using_trie.py     None                           ok(neg)   - 
graphs/gale_shapley_bigraph.py         None                           ok(neg)   - 
hashes/md5.py                          None                           WRONG     aggregate,element_accumulation 
physics/newtons_law_of_gravitation.py  None                           ok(neg)   - 
strings/detecting_english_programmatically.py None                           ok(neg)   - 
scheduling/weighted_interval_scheduling.py None                           ok(neg)   - 
matrix/cramers_rule_2x2.py             None                           ok(neg)   - 
strings/top_k_frequent_words.py        None                           ok(neg)   - 
computer_vision/horn_schunck.py        None                           ok(neg)   - 
machine_learning/mfcc.py               None                           ok(neg)   - 
machine_learning/frequent_pattern_growth.py None                           ok(neg)   - 
physics/hamiltonian.py                 None                           ok(neg)   - 
ciphers/morse_code.py                  None                           ok(neg)   - 
conversions/rgb_cmyk_conversion.py     None                           ok(neg)   - 
data_compression/run_length_encoding.py None                           ok(neg)   - 
maths/floor.py                         None                           ok(neg)   - 
strings/rabin_karp.py                  None                           ok(neg)   - 
dynamic_programming/abbreviation.py    None                           ok(neg)   - 
greedy_methods/fractional_cover_problem.py None                           ok(neg)   - 
geometry/shoelace.py                   None                           ok(neg)   - 
graphs/check_bipatrite.py              None                           ok(neg)   - 
electronics/ind_reactance.py           None                           ok(neg)   - 
dynamic_programming/integer_partition.py None                           ok(neg)   - 
ciphers/a1z26.py                       None                           ok(neg)   - 
electronics/circular_convolution.py    None                           ok(neg)   - 
machine_learning/gradient_boosting_classifier.py None                           ok(neg)   - 
machine_learning/astar.py              None                           ok(neg)   - 
machine_learning/mab.py                None                           ok(neg)   - 
financial/fractional_differentiation.py None                           ok(neg)   - 
neural_network/convolution_neural_network.py None                           ok(neg)   - 
physics/altitude_pressure.py           None                           ok(neg)   - 
digital_image_processing/change_contrast.py None                           ok(neg)   - 
ciphers/caesar_cipher.py               None                           WRONG     aggregate,element_accumulation 
greedy_methods/gas_station.py          None                           ok(neg)   - 
geometry/braik_mac_construction.py     None                           ok(neg)   - 
maths/josephus_problem.py              None                           ok(neg)   - 
maths/area_under_curve.py              None                           ok(neg)   - 
maths/continued_fraction.py            None                           ok(neg)   - 
electronics/carrier_concentration.py   None                           ok(neg)   - 
maths/is_ipv6_address_valid.py         None                           ok(neg)   - 
blockchain/diophantine_equation.py     None                           ok(neg)   - 
conversions/hexadecimal_to_decimal.py  None                           ok(neg)   - 
boolean_algebra/nor_gate.py            None                           ok(neg)   - 
cellular_automata/wa_tor.py            None                           ok(neg)   - 
file_transfer/send_file.py             None                           ok(neg)   - 
maths/sin.py                           None                           ok(neg)   - 
conversions/rectangular_to_polar.py    None                           ok(neg)   - 
financial/ordinary_annuity_future_value.py None                           ok(neg)   - 
boolean_algebra/quine_mc_cluskey.py    None                           ok(neg)   - 
dynamic_programming/wildcard_matching.py None                           ok(neg)   - 
conversions/binary_to_excess3.py       None                           ok(neg)   - 
ciphers/atbash.py                      None                           WRONG     aggregate,element_accumulation 
graphs/greedy_best_first.py            None                           ok(neg)   - 
graphs/hopcroft_karp.py                None                           ok(neg)   - not parseable: iterable unpacking cannot be used in comprehension
physics/center_of_mass.py              None                           ok(neg)   - 
strings/bpe_tokenizer.py               None                           ok(neg)   - 
machine_learning/rmsprop.py            None                           ok(neg)   - 
graphs/graph_peripherality.py          None                           ok(neg)   - 
computer_vision/haralick_descriptors.py None                           ok(neg)   - 
physics/escape_velocity.py             None                           ok(neg)   - 
graphs/directed_and_undirected_weighted_graph.py None                           ok(neg)   - 
conversions/int_to_negative_binary_base.py None                           ok(neg)   - 

PRECISION = correct / answered = 8/12 = 66.7%
RECALL    = correct / positives = 8/24 = 33.3%
WRONG ON NEGATIVES = 3 of 77
```
