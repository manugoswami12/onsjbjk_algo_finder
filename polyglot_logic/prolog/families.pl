/* AP13 v3 family tree (doc 08): input -> output trace, broad -> narrow.
   Branch decisions use the frozen AP12 route/2 where it already decides
   (sorting / lookup) and the roles and idioms of roles.pl elsewhere.
   A function may have several paths (mixed code); missing evidence stops at
   the parent branch, never at a guessed leaf.
*/
:- discontiguous family_path/2.

% ----- sequence -> sequence -----------------------------------------------------------
family_path(F, [sequence_transformation, comparison_sort, adjacent_exchange]) :-
    route(F, comparison_driven_reordering), idiom(F, adjacent, _),
    \+ idiom(F, gap, _), \+ idiom(F, heap, _), \+ idiom(F, stooge, _).
family_path(F, [sequence_transformation, comparison_sort, gap_exchange]) :-
    idiom(F, gap, Q), idiom(F, compared_rewrite, Q0), var(Q0) == Q.
family_path(F, [sequence_transformation, comparison_sort, heap]) :-
    idiom(F, heap, Q), ( idiom(F, compared_rewrite, Q0), var(Q0) == Q ; in_func(S, F), exchange(S, Q, _, _) ).
family_path(F, [sequence_transformation, comparison_sort, stooge_recursion]) :-
    idiom(F, stooge, _).
family_path(F, [sequence_transformation, comparison_sort, shift_insertion]) :-
    idiom(F, shift, Q), idiom(F, compared_rewrite, Q).
family_path(F, [sequence_transformation, comparison_sort, select_extreme]) :-
    role(F, most_wanted, M), scanned_holder(F, M), in_func(S, F), exchange(S, Q, _, J), J == var(M),
    role(F, organizer, Q0), var(Q0) = Q.
family_path(F, [sequence_transformation, comparison_sort, partition_recursive]) :-
    idiom(F, partition, _), \+ idiom(F, stooge, _).
family_path(F, [sequence_transformation, comparison_sort, merge]) :-
    idiom(F, merge, _).
family_path(F, [sequence_transformation, distribution_sort, histogram]) :-
    idiom(F, histogram, _).
family_path(F, [sequence_transformation, uncompared_rearrangement]) :-
    route(F, sequence_rearrangement), \+ route(F, comparison_driven_reordering),
    \+ idiom(F, compared_rewrite, _), \+ role(F, most_wanted, _),
    \+ compares_any_element(F).                  % no element is compared ANYWHERE in F
compares_any_element(F) :- role(F, organizer, Q), in_func(S, F), rel_of(S, R), compares_elements(R, Q), !.
compares_any_element(F) :-                       % ... or in a local function it calls (sift-down helper)
    in_func(C, F), call_at(C, Gn, _), Gn \== '$self', func(G, N, _), G \== F, base_name(N, Gn),
    in_func(S, G), rel_of(S, R), sub_term(E, R), compound(E), E = op(Op, [A, B]),
    memberchk(Op, [gt, ge, lt, le]), A = elem(_, _), B = elem(_, _), !.
family_path(F, [sequence_transformation, comparison_sort]) :-
    idiom(F, compared_rewrite, _), \+ idiom(F, histogram, _).

% ----- sequence -> scalar / index ----------------------------------------------------------
family_path(F, [sequence_query, target_search, interval_halving]) :-
    ( route(F, interval_lookup) ; route(F, indexed_lookup), idiom(F, midpoint, _) ).
family_path(F, [sequence_query, target_search, linear_scan]) :-
    idiom(F, index_return, _), \+ idiom(F, midpoint, _).
family_path(F, [sequence_query, target_search]) :-
    route(F, indexed_lookup).
family_path(F, [sequence_query, aggregate, gatherer]) :-
    role(F, gatherer(_), X), in_func(S, F), value(S, var(X), E), reads_param_seq(F, E),
    in_func(R, F), cret(R, var(X2)), X2 == X.
family_path(F, [sequence_query, aggregate, most_wanted]) :-
    role(F, most_wanted, X), in_func(S, F), value(S, var(X), E), reads_param_seq(F, E),
    in_func(R, F), cret(R, var(X2)), X2 == X.
% the holder takes the scanning loop's variable (m = j), not a fixed child position (heap)
scanned_holder(F, M) :- in_func(S, F), ( assign(S, var(M), var(J)) ; value(S, var(M), var(J)) ),
    under(S, L), lvar(L, var(J2)), J2 == J, !.
reads_param_seq(F, E) :- sub_term(T, E), compound(T), T = elem(var(Q), _), param(F, _, Q), !.

% ----- number -> number ------------------------------------------------------------------
family_path(F, [numeric, recurrence, pair_recurrence])    :- numeric(F), rec_class(F, pair, _).
family_path(F, [numeric, recurrence, modulo_recurrence])  :- numeric(F), rec_class(F, modulo, _).
family_path(F, [numeric, recurrence, range_accumulation]) :- numeric(F), rec_class(F, range_accumulation, _).
family_path(F, [numeric, recurrence, double_recursion])   :- numeric(F), rec_class(F, double_recursion, _).
family_path(F, [numeric, decomposition, digits])          :- numeric(F), rec_class(F, digits, _).
family_path(F, [numeric, divisor_test])                   :- numeric(F), rec_class(F, divisor_test, _).
family_path(F, [numeric, conditional_iteration])          :- numeric(F), rec_class(F, conditional, _).
% an arithmetic test: >= 2 comparisons over arithmetic on a parameter (leap year), never a
% one-comparison helper (a < b) or a delegation to another function
family_path(F, [numeric, predicate]) :-
    numeric(F), \+ loop(_, F, _), in_func(S, F), cret(S, V), V = op(O, _), memberchk(O, [and, or, not]),
    findall(c, ( sub_term(C, V), compound(C), C = op(Cmp, _), memberchk(Cmp, [eq, ne, gt, ge, lt, le]) ), Cs),
    length(Cs, NC), NC >= 2,
    once(( sub_term(A, V), compound(A), A = op(Ar, [X, _]), memberchk(Ar, [mod, div, mul, add, sub]),
           var_in(X, P), param(F, _, P) )),
    \+ ( sub_term(C2, V), compound(C2), C2 = call(_, _) ).
% numeric: no parameter is used as a sequence
numeric(F) :- func(F, _, _), \+ seq_param(F, _).

% ----- marking / tables --------------------------------------------------------------------
family_path(F, [marking, stride_marking]) :- idiom(F, stride_marking, _).
family_path(F, [marking, table_fill])     :- idiom(F, table_fill, _).

% ----- v3.1 branches (doc 09) --------------------------------------------------------
family_path(F, [sequence_query, predicate, symmetric_compare]) :-
    idiom(F, mirror_compare, _).
family_path(F, [sequence_transformation, elementwise_map]) :-
    idiom(F, elementwise_map, _), \+ idiom(F, compared_rewrite, _).
family_path(F, [sequence_transformation, construction, run_length]) :-
    idiom(F, run_length, _).
family_path(F, [search, backtracking]) :- idiom(F, backtracking, _).
family_path(F, [numeric, decomposition, greedy_denominations]) :- idiom(F, greedy_denominations, _).
family_path(F, [numeric, recurrence, josephus_recurrence]) :- rec_class(F, josephus, _).
family_path(F, [sequence_transformation, comparison_sort, prefix_reversal]) :- idiom(F, prefix_reversal, _).
% a top-level script: the same gatherer over a local sequence, nothing returned
family_path(F, [sequence_query, aggregate, gatherer]) :-
    func(F, '<toplevel>', _), role(F, gatherer(_), X), in_func(S, F), value(S, var(X), E),
    sub_term(T, E), compound(T), T = elem(var(_), _).

% ----- broadest true level: the input -> output shape (only when no branch below applies) ----
family_path(F, [sequence_transformation]) :-
    \+ deeper_path(F), role(F, organizer, Q), param(F, _, Q), \+ marking_like(F).
family_path(F, [sequence_transformation]) :-
    \+ deeper_path(F), seq_param(F, _), sequence_result(F), \+ marking_like(F),
    ( loop(_, F, _) ; in_func(S0, F), call_at(S0, '$self', _) ).
family_path(F, [sequence_query]) :-
    \+ deeper_path(F), seq_param(F, Q), \+ role(F, organizer, Q), computed_result(F), \+ marking_like(F).
family_path(F, [numeric]) :-
    \+ deeper_path(F), numeric(F), ( loop(_, F, _) ; in_func(S0, F), call_at(S0, '$self', _) ),
    computed_result(F), \+ marking_like(F), \+ ( in_func(S1, F), capp(S1, _, _) ).
deeper_path(F) :- family_path_deep(F), !.
family_path_deep(F) :- clause(family_path(F, P), Body), P = [_, _|_], call(Body).
% a SCALAR computed result: never a list, concat, filter, map, or a variable built by appends
computed_result(F) :- in_func(S, F), cret(S, V), V \= int(_), V \= bool(_), V \= list([]),
    V \= call('$self', _), !, \+ sequence_result(F).
sequence_result(F) :- in_func(S, F), cret(S, V), seq_form(F, 3, V), !.
seq_form(_, _, V) :- compound(V), functor(V, Fn, _), memberchk(Fn, [list, concat, filter, map, tail, cons]), !.
seq_form(_, _, V) :- compound(V), V = call(C, _), memberchk(C, [list, sorted, reverse, append, new, set]), !.
seq_form(F, D, var(X)) :- D > 0, D1 is D - 1, in_func(S, F),        % bounded: x = x + ... cannot loop
    ( capp(S, var(X2), _) ; value(S, elem(var(X2), _), _) ; value(S, var(X2), V0), V0 \= var(_), seq_form(F, D1, V0) ),
    X2 == X, !.
marking_like(F) :- in_func(S, F), value(S, elem(var(M), _), _), \+ param(F, _, M), !.

% ----- answer: the deepest supported paths (a path that is a prefix of another is dropped) ---
deepest_families(F, Paths) :-
    findall(P, family_path(F, P), Ps0), sort(Ps0, Ps),
    exclude(prefix_of_other(Ps), Ps, Paths).
prefix_of_other(Ps, P) :- member(Q, Ps), Q \== P, append(P, [_|_], Q), !.

% one answer per file: functions with a family that no OTHER function with a family calls
answer_function(F) :-
    family_path(F, _),
    \+ ( family_path(G, _), G \== F, func(F, N, _), base_name(N, B), in_func(S, G), call_at(S, B, _) ).
