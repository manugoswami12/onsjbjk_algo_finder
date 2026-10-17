/* v0.2 branch rules over the AP13 language-neutral relations (value/3, nguard/3, exchange/4,
   under/2, loop/3); polyglot_logic is not changed. AP13 reaches comparison_sort only when an
   element-element comparison guards the write itself, and select_extreme only with m = j. A
   comparison of the sequence's values that decides WHICH POSITION is exchanged (through a holder:
   best = q[k]; idx = k; swap(q[i], q[idx])) had no branch, so the tree fell to the broad
   [sequence_transformation] instead of stopping at its parent comparison_sort.
*/
% a value of sequence Q: one of its elements, or a variable that only ever holds its elements
seq_value(_, Q, T) :- T = elem(V, _), V == var(Q), !.
seq_value(F, Q, var(B)) :- atom(B), once(( in_func(S0, F), value(S0, var(B), _) )),
    forall(( in_func(S, F), value(S, var(B2), V) , B2 == B ), ( V = elem(Vq, _), Vq == var(Q) )).
compares_values(F, C, Q) :- sub_term(O, C), compound(O), O = op(Op, [A, B]), memberchk(Op, [gt, ge, lt, le]),
    seq_value(F, Q, A), seq_value(F, Q, B), !.
% the exchanged position var(K) is set under a comparison of Q's values
decided_position(F, Q, S, K, Sk) :-
    in_func(S, F), exchange(S, var(Q), _, J), J = var(K), atom(K),
    in_func(Sk, F), value(Sk, var(K2), _), K2 == K, nguard(Sk, C, _), compares_values(F, C, Q).

family_path_v02(F, [sequence_transformation, comparison_sort]) :- once(decided_position(F, _, _, _, _)).
% the deciding comparison scans in a loop that does not hold the exchange: select, then exchange
family_path_v02(F, [sequence_transformation, comparison_sort, select_extreme]) :-
    once(( decided_position(F, _, S, _, Sk), under(Sk, L), loop(L, F, Kind), Kind \== recursion, \+ under(S, L) )).

% deepest paths of AP13 family_path and these branches together (AP13 prefix_of_other/2 reused)
deepest_families_v02(F, Paths) :-
    findall(P, ( family_path(F, P) ; family_path_v02(F, P) ), Ps0), sort(Ps0, Ps),
    exclude(prefix_of_other(Ps), Ps, Paths).
