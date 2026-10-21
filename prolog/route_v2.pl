% v0.2 router. Loaded facts use anonymous f1/f2 identifiers.
% Routes are candidate BRANCHES (broad family -> narrow branch), never algorithm
% identifications. A narrow branch always requires its broad parent plus more evidence.
% Larger variations stay in the broad branch; acceptance is never relaxed.
:- dynamic program/2.
:- dynamic observed/3.
:- discontiguous route/2.

% ---- v0.1 rules, verbatim (prolog/route.pl) ----
route(F, sequence_rearrangement) :-
    observed(F, input_sequence_mutated, _),
    observed(F, element_exchange, _).

route(F, comparison_driven_reordering) :-
    route(F, sequence_rearrangement),
    observed(F, comparison_controls_exchange, _).

route(F, indexed_lookup) :-
    observed(F, indexed_equality_controls_index_return, _).

route(F, interval_lookup) :-
    route(F, indexed_lookup),
    observed(F, coherent_midpoint_interval_update, _).

% ---- v0.2: sequence rearrangement by shifting; sorting sub-branches ----
route(F, sequence_rearrangement) :-
    observed(F, input_sequence_mutated, _),
    observed(F, adjacent_shift_write, _).

route(F, comparison_driven_reordering) :-
    route(F, sequence_rearrangement),
    observed(F, comparison_controls_shift, _).

route(F, comparison_driven_reordering) :-
    route(F, sequence_rearrangement),
    observed(F, min_index_then_exchange, _).

route(F, shift_insertion) :-
    route(F, comparison_driven_reordering),
    observed(F, adjacent_shift_write, _),
    observed(F, comparison_controls_shift, _).

route(F, selection_exchange) :-
    route(F, comparison_driven_reordering),
    observed(F, min_index_then_exchange, _).

% ---- lookup without an index result ----
route(F, membership_lookup) :-
    observed(F, element_equality_controls_true_return, _).

% recursive halving on slices with a boolean result: an interval lookup without an index
route(F, interval_lookup) :-
    route(F, membership_lookup),
    observed(F, slice_halving_self_call, _).

% ---- aggregate over input elements ----
route(F, aggregate) :- observed(F, input_element_accumulated, _).
route(F, aggregate) :- observed(F, best_so_far_update, _).

route(F, element_accumulation) :-
    route(F, aggregate),
    observed(F, input_element_accumulated, _).

route(F, extremum_search) :-
    route(F, aggregate),
    observed(F, best_so_far_update, _).

% ---- recurrences driven by an integer input ----
recurrence_evidence(pair_recurrence).
recurrence_evidence(modulo_recurrence).
recurrence_evidence(range_product).
recurrence_evidence(range_sum).
recurrence_evidence(linear_self_product).
recurrence_evidence(self_calls_minus_one_minus_two).
recurrence_evidence(list_recurrence_two_terms).

route(F, recurrence) :-
    once((recurrence_evidence(E), observed(F, E, _))).

route(F, fibonacci_like) :-
    route(F, recurrence),
    once((observed(F, pair_recurrence, _) ; observed(F, self_calls_minus_one_minus_two, _) ;
          observed(F, list_recurrence_two_terms, _))).

route(F, euclid_like) :-
    route(F, recurrence),
    observed(F, modulo_recurrence, _).

route(F, factorial_like) :-
    route(F, recurrence),
    once((observed(F, range_product, _) ; observed(F, linear_self_product, _))).

route(F, series_sum) :-
    route(F, recurrence),
    observed(F, range_sum, _).

% ---- recursion with two self-calls (tree recursion); broad only ----
route(F, recursive_decomposition) :-
    observed(F, double_self_call, _).

% ---- number properties ----
route(F, number_property) :- observed(F, digit_decomposition, _).
route(F, number_property) :- observed(F, divisor_test_in_loop, _).
route(F, number_property) :- observed(F, parity_halving_or_triple, _).

route(F, digit_processing) :-
    route(F, number_property),
    observed(F, digit_decomposition, _).

route(F, divisor_search) :-
    route(F, number_property),
    observed(F, divisor_test_in_loop, _).

route(F, collatz_like) :-
    route(F, number_property),
    observed(F, parity_halving_or_triple, _).

% ---- marking ----
route(F, marking) :-
    observed(F, stride_marking, _).

route(F, sieve_like) :-
    route(F, marking),
    observed(F, flag_guards_stride, _).

% ---- symmetric comparison ----
route(F, symmetric_compare) :-
    observed(F, mirror_compare, _).

route(F, palindrome_check) :-
    route(F, symmetric_compare),
    observed(F, mirror_compare_decides_result, _).

% ---- learned: nearest learned algorithm (learn_v2.py); the branch plus its ancestors ----
parent(comparison_driven_reordering, sequence_rearrangement).
parent(shift_insertion, comparison_driven_reordering).
parent(selection_exchange, comparison_driven_reordering).
parent(interval_lookup, indexed_lookup).
parent(element_accumulation, aggregate).
parent(extremum_search, aggregate).
parent(fibonacci_like, recurrence).
parent(euclid_like, recurrence).
parent(factorial_like, recurrence).
parent(series_sum, recurrence).
parent(digit_processing, number_property).
parent(divisor_search, number_property).
parent(collatz_like, number_property).
parent(sieve_like, marking).
parent(palindrome_check, symmetric_compare).

ancestor(B, P) :- parent(B, P).
ancestor(B, P) :- parent(B, Q), ancestor(Q, P).

route(F, B) :- observed(F, learned(B), _).
route(F, P) :- observed(F, learned(B), _), ancestor(B, P).

% ---- UNKNOWN: no broad family has its evidence (replaces the v0.1 two-family rule) ----
broad(sequence_rearrangement).
broad(indexed_lookup).
broad(membership_lookup).
broad(aggregate).
broad(recurrence).
broad(recursive_decomposition).
broad(number_property).
broad(marking).
broad(symmetric_compare).

route(F, unknown) :-
    \+ (broad(B), route(F, B)).

main :-
    current_prolog_flag(argv, [FactsFile|_]),
    consult(FactsFile),
    forall(program(F, _), (
        findall(Route, route(F, Route), Routes0),
        sort(Routes0, Routes),
        forall(member(Route, Routes), format('ROUTE ~w ~w~n', [F, Route]))
    )),
    halt.
