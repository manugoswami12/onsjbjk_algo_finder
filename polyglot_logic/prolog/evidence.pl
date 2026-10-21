/* AP13 evidence: canonical relations -> the AP12 fallback vocabulary.
   The facts produced here are asserted as observed/3 and routed by the
   UNCHANGED algo_reference_corpus/ap12/prolog/route_extended.pl.
   Same conservative meaning as onsjbjk_algo_io_fallback_poc_v0_1/static_trace.py,
   now for every language.
*/
input_seq(F, var(P)) :- param(F, _, P).

evidence(F, returned_input, L) :-
    ret(S, var(P)), live(S), stmt(S, F, _, L), param(F, _, P).

evidence(F, element_exchange, L) :-
    exchange(S, Q, _, _), stmt(S, F, _, L), input_seq(F, Q).

evidence(F, input_sequence_mutated, L) :-
    evidence(F, element_exchange, L).

% A true comparison of the same two positions controls the exchange.
evidence(F, comparison_controls_exchange, L) :-
    exchange(S, Q, I, J), stmt(S, F, _, L), input_seq(F, Q),
    nguard(S, op(O, [A, B]), true), memberchk(O, [gt, ge]),
    A == elem(Q, I), B == elem(Q, J).

% return M, inside a loop, controlled by A[M] == T for distinct inputs A, T.
evidence(F, indexed_equality_controls_index_return, L) :-
    ret(S, var(M)), live(S), stmt(S, F, _, L), under(S, _),
    nguard(S, op(eq, [elem(var(A), var(M)), var(T)]), true),
    param(F, _, A), param(F, _, T), A \== T.

% loop while lo <= hi; mid = midpoint(lo, hi); lo = mid + 1 and hi = mid - 1 under guards.
evidence(F, coherent_midpoint_interval_update, L) :-
    loop(Lp, F, _), lcond(Lp, op(ge, [var(Hi), var(Lo)])),
    midpoint_in(Lp, M, Lo, Hi, Sm),
    value(Sg, var(Lo), op(add, [var(M), int(1)])), under(Sg, Lp), once(nguard(Sg, _, _)),
    value(Ss, var(Hi), op(sub, [var(M), int(1)])), under(Ss, Lp), once(nguard(Ss, _, _)),
    member(S0, [Sm, Sg, Ss]), stmt(S0, _, _, L).

% AP12 extra witness: bounded interval narrowed by comparing A[M] with input T.
evidence(F, bounded_indexed_interval_lookup, L) :-
    loop(Lp, F, _), lcond(Lp, op(O, [var(Hi), var(Lo)])), memberchk(O, [gt, ge]),
    midpoint_in(Lp, M, Lo, Hi, Sm),
    value(Sg, var(Lo), op(add, [var(M), int(1)])), under(Sg, Lp),
    nguard(Sg, C1, _), mentions(C1, elem(var(A), var(M))), mentions(C1, var(T)),
    param(F, _, A), param(F, _, T), A \== T,
    ( value(Ss, var(Hi), var(M)) ; value(Ss, var(Hi), op(sub, [var(M), int(1)])) ),
    under(Ss, Lp), nguard(Ss, C2, _), mentions(C2, elem(var(A), var(M))),
    stmt(Sm, _, _, L).

midpoint_in(Lp, M, Lo, Hi, Sm) :-
    value(Sm, var(M), Mid), under(Sm, Lp), midpoint(Mid, Lo, Hi).

midpoint(op(div, [op(add, [var(Lo), var(Hi)]), int(2)]), Lo, Hi).
midpoint(op(div, [op(add, [var(Hi), var(Lo)]), int(2)]), Lo, Hi).

mentions(T, X) :- sub_term(Y, T), Y == X, !.
