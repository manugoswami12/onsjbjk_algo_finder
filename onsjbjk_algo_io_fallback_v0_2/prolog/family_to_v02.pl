/* v0.2 (doc 03): an AP13 family path names a v0.2 branch (route_v2.pl adds its ancestors).
   The same table serves every language; a path without a v0.2 branch names none (UNKNOWN). */
family_branch([sequence_transformation, comparison_sort, shift_insertion], _, shift_insertion).
family_branch([sequence_transformation, comparison_sort, select_extreme], _, selection_exchange).
family_branch([sequence_transformation, comparison_sort, Leaf], _, comparison_driven_reordering) :-
    memberchk(Leaf, [adjacent_exchange, gap_exchange, heap, stooge_recursion, partition_recursive,
                     prefix_reversal]).
% merging two ordered sequences is a sort only with the recursion that splits the input in two
% (merge sort); a merge alone (merge-lists) has no v0.2 branch
family_branch([sequence_transformation, comparison_sort, merge], F, comparison_driven_reordering) :-
    self_calls(F, K), K >= 2.
family_branch([sequence_transformation, comparison_sort], _, comparison_driven_reordering).
family_branch([sequence_transformation, distribution_sort, histogram], _, sequence_rearrangement).
family_branch([sequence_transformation, uncompared_rearrangement], _, sequence_rearrangement).
family_branch([sequence_query, target_search, interval_halving], _, interval_lookup).
family_branch([sequence_query, target_search, linear_scan], _, indexed_lookup).
family_branch([sequence_query, target_search], _, indexed_lookup).
family_branch([sequence_query, aggregate, gatherer], _, element_accumulation).
family_branch([sequence_query, aggregate, most_wanted], _, extremum_search).
family_branch([sequence_query, predicate, symmetric_compare], _, palindrome_check).
family_branch([numeric, recurrence, pair_recurrence], _, fibonacci_like).
family_branch([numeric, recurrence, modulo_recurrence], _, euclid_like).
family_branch([numeric, recurrence, range_accumulation], F, B) :- range_op(F, O), range_branch(O, B).
family_branch([numeric, recurrence, double_recursion], F, B) :-
    (   self_minus_one_minus_two(F) -> B = fibonacci_like
    ;   counted_down_twice(F) -> B = towers_of_hanoi
    ;   B = recursive_decomposition
    ).
family_branch([numeric, decomposition, digits], _, digit_processing).
family_branch([numeric, divisor_test], _, divisor_search).
family_branch([numeric, conditional_iteration], _, collatz_like).
family_branch([marking, stride_marking], _, sieve_like).

% range accumulation: a product is factorial-like, a sum a series sum
range_branch(mul, factorial_like).
range_branch(add, series_sum).
range_op(F, O) :- rec_class(F, range_accumulation, X), role(F, gatherer(O), X), !.
range_op(F, O) :- in_func(S, F), cret(S, op(O, Args)), memberchk(O, [mul, add]), self_count(Args, 1), !.
range_op(F, O) :- family_path_v02(F, [numeric, recurrence, range_accumulation]),   % families_v02.pl
    role(F, gatherer(O), _), memberchk(O, [mul, add]), !.
% f(n - 1) and f(n - 2): the Fibonacci recurrence (the v0.2 fact self_calls_minus_one_minus_two)
self_minus_one_minus_two(F) :- param(F, _, N),
    in_func(S1, F), call_at(S1, '$self', A1), member(op(sub, [var(N1), int(1)]), A1), N1 == N,
    in_func(S2, F), call_at(S2, '$self', A2), member(op(sub, [var(N2), int(2)]), A2), N2 == N, !.

% built, not learned (doc 04 section 15: the C Hanoi cannot be learned from the Python files): two
% recursive calls, each on n - 1, made one after the other for their effect only (their results are
% discarded), f(n-1); move; f(n-1): Towers of Hanoi. AP13's rec_class(double_recursion, F) is the
% sequential form (its third argument is the function). Fibonacci combines the results, Levenshtein
% assigns them. In Lisp ECL makes the second call a jump to the start (tail_loop) that sets n to n - 1.
% Built from towers-of-hanoi-1.c.
counted_down_twice(F) :-
    \+ combined_self_calls(F), param(F, _, N),
    (   rec_class(F, double_recursion, X), X == F,
        in_func(S1, F), call_at(S1, '$self', A1), counted_down(N, A1), discarded(S1),
        in_func(S2, F), S2 \== S1, call_at(S2, '$self', A2), counted_down(N, A2), discarded(S2)
    ;   tail_loop(L), loop(L, F, _),
        in_func(S, F), in_loop(S, L), call_at(S, '$self', A), counted_down(N, A), discarded(S),
        in_func(S3, F), S3 \== S, in_loop(S3, L),          % the jump's own update, not the call's parameter update
        ( assign(S3, var(N2), V) ; par_assign(S3, Ts, Vs), nth1(K, Ts, var(N2)), nth1(K, Vs, V) ),
        N2 == N, counted_down(N, [V])
    ), !.
counted_down(N, Args) :- member(op(sub, [V, int(1)]), Args), V == var(N), !.
combined_self_calls(F) :- in_func(S, F), cret(S, V), self_count(V, K), K >= 2, !.
% the statement's recursive call is made for its effect: no value of the statement holds the call
discarded(S) :- \+ ( ( assign(S, _, V) ; ret(S, V) ; guard(S, V, _) ), sub_term(C, V), compound(C), C = call('$self', _) ).
