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
    role(F, most_wanted, M), in_func(S, F), exchange(S, Q, _, J), J == var(M),
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

% ----- answer: the deepest supported paths (a path that is a prefix of another is dropped) ---
deepest_families(F, Paths) :-
    findall(P, family_path(F, P), Ps0), sort(Ps0, Ps),
    exclude(prefix_of_other(Ps), Ps, Paths).
prefix_of_other(Ps, P) :- member(Q, Ps), Q \== P, append(P, [_|_], Q), !.
