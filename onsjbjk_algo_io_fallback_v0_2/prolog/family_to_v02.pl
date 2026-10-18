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
% built branches (doc 04 section 15, families_v02.pl): one task each
family_branch([numeric, recurrence, nested_recursion], _, ackermann).
family_branch([marking, table_fill, capacity_reduction], F, knapsack_01) :- larger_with_value(F).
family_branch([numeric, recurrence, capacity_reduction], F, knapsack_01) :- larger_with_value(F).
family_branch([sequence_transformation, elementwise_map, alphabet_rotation], _, caesar_cipher).
family_branch([sequence_transformation, construction, matrix_product], _, matrix_multiplication).
family_branch([sequence_transformation, construction, run_length], F, run_length_encoding) :-
    ( v02_run_length(F) -> true ; run_counted(F) ).
family_branch([numeric, recurrence, josephus_recurrence], F, josephus) :- josephus_count(F).
family_branch([search, permutation_filter], _, n_queens).
family_branch([sequence_transformation, elimination_cycle], _, josephus).
family_branch([numeric, predicate, leap_rule], _, leap_year).
family_branch([search, diagonal_conflict], _, n_queens).
family_branch([sequence_query, two_sequence_match, longest_common], _, lcs).
family_branch([sequence_query, two_sequence_match, edit_distance], _, levenshtein).
family_branch([library, roman_numerals], _, roman_encode).
family_branch([numeric, decomposition, symbol_table], _, roman_encode).

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
    \+ combined_self_calls(F), param(F, _, N), \+ ( self_calls(F, K), K > 2 ),   % two moves of n - 1 (a fractal has more)
    (   rec_class(F, double_recursion, X), X == F,
        in_func(S1, F), call_at(S1, '$self', A1), counted_down(N, A1), discarded(S1),
        in_func(S2, F), S2 \== S1, call_at(S2, '$self', A2), counted_down(N, A2), discarded(S2)
    ;   tail_loop(L), loop(L, F, _),
        in_func(S, F), in_loop(S, L), call_at(S, '$self', A), counted_down(N, A), discarded(S),
        in_func(S3, F), S3 \== S, in_loop(S3, L),          % the jump's own update, not the call's parameter update
        ( assign(S3, var(N2), V) ; par_assign(S3, Ts, Vs), nth1(K, Ts, var(N2)), nth1(K, Vs, V) ),
        N2 == N, counted_down(N, [V])
    ), !.
% the functional form: the two results joined with the move between them, f(n-1) ++ [move] ++ f(n-1)
counted_down_twice(F) :- param(F, _, N), in_func(S, F), ret(S, concat(Parts)),
    append(_, [call('$self', A1), Mid, call('$self', A2)|_], Parts), Mid \= call('$self', _),
    counted_down(N, A1), counted_down(N, A2), !.
% the accumulator form: h(n-1, ..., (move : h(n-1, ..., acc))), the inner result passed on in the outer call
counted_down_twice(F) :- param(F, _, N), in_func(S, F), ( ret(S, V) ; call_at(S, '$self', As), V = call('$self', As) ),
    sub_term(O, V), compound(O), O = call('$self', A1), counted_down(N, A1),
    member(A, A1), sub_term(C, A), compound(C), C = cons(_, call('$self', A2)), counted_down(N, A2), !.
counted_down(N, Args) :- member(op(sub, [V, int(1)]), Args), V == var(N), !.
combined_self_calls(F) :- in_func(S, F), cret(S, V), self_count(V, K), K >= 2, !.
% the statement's recursive call is made for its effect: no value of the statement holds the call
discarded(S) :- \+ ( ( assign(S, _, V) ; ret(S, V) ; guard(S, V, _) ), sub_term(C, V), compound(C), C = call('$self', _) ).
% AP13's josephus_recurrence with its modulus the number of people: the recursion counts it down, f(n - 1, k) mod n
% (modular exponentiation also takes a self-call's result mod a parameter, but keeps the modulus); or AP13's
% iterative form, the stepper itself the modulus
josephus_count(F) :- in_func(S, F), cret(S, op(mod, [_, var(N)])), param(F, _, N), in_func(C, F),
    call_at(C, '$self', As), member(op(sub, [V, int(1)]), As), V == var(N), !.
josephus_count(F) :- in_func(S, F), value(S, var(X), op(mod, [op(add, [var(X2), var(K)]), var(I)])), X2 == X, K \== X,
    role(F, stepper, I), !.
% run-length: the v0.2 forms (families_v02.pl), or AP13's run idiom with the run's length emitted: a counter raised in
% the run loop (a count, never an index), or the span j - i, in what is appended (a duplicate skip in three-sum has
% the loop, no count)
v02_run_length(F) :- clause(family_path_v02(F, [sequence_transformation, construction, run_length]), B), call(B), !.
run_counted(F) :- loop(L, F, _), in_func(S, F), under(S, L), value(S, var(C), op(add, [var(C2), int(1)])), C == C2,
    in_func(S2, F), ( capp(S2, _, E) ; value(S2, _, E) ; cret(S2, E) ), S2 \== S, sub_term(V, E), V == var(C),
    \+ ( rel_of(_, R), sub_term(X, R), compound(X), X = elem(_, I), sub_term(V2, I), V2 == var(C) ), !.   % not an index
run_counted(F) :- in_func(S, F), ( capp(S, _, E) ; value(S, _, E) ), sub_term(D, E), compound(D),
    D = op(sub, [var(J), var(I)]), J \== I, !.
% 0-1 knapsack: the larger of skipping and taking, taking adding the item's value (max(T[i-1][j], T[i-1][j - w] + v));
% or taking written as T[i-1][j - w] + v (a ternary, an if); subset sum and partition take `or` of the two,
% combination sum collects
larger_with_value(F) :- in_func(S, F), rel_of(S, R), sub_term(M, R), compound(M), M = call(max, Args),
    member(A, Args), sub_term(Ad, A), compound(Ad), ( Ad = op(add, _) ; Ad = call('$self', _) ), !.
larger_with_value(F) :- in_func(S, F), rel_of(S, R), sub_term(Ad, R), compound(Ad), Ad = op(add, [A, B]),
    ( reduced_capacity(A), B \= int(_) ; reduced_capacity(B), A \= int(_) ), !.   % taking: T[i-1][j - w] + v
larger_with_value(F) :- in_func(S, F), ( nguard(S, C, _) ; cret(S, C) ), sub_term(O, C), compound(O),
    O = op(Cmp, [X, Y]), memberchk(Cmp, [gt, ge, lt, le]), ( X = op(add, _) ; Y = op(add, _) ),
    ( sub_term(T, X) ; sub_term(T, Y) ), compound(T), T = call('$self', _), !.
% the cell (or the recursion) at a capacity reduced by a non-constant amount: T[i-1][j - w], f(i - 1, c - w)
reduced_capacity(X) :- sub_term(R, X), compound(R), ( R = elem(_, op(sub, [_, W])) ; R = call('$self', As),
    member(op(sub, [_, W]), As) ), W \= int(_), !.
