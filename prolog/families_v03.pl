/* v0.3 tree branches (doc 04 section 18.7), kept separate from the pipeline: loaded only by tree_v03.pl and
   learn_apply_v03.pl, which load the pipeline's own tree_main.pl / learn_apply.pl first and change nothing in them.
   Two shapes the v0.2 tree has no branch for, so files fell to a broad node (or none) where the only learned
   branch of a behaviourally equal label decided:

   1. Partition by recursion through variables (Rosetta quicksort-1.py): the parts are built by appends under
      comparisons with a pivot, the recursion results are stored, then joined: lesser = f(lesser); greater =
      f(greater); return lesser + equal + greater. AP13's idiom(F, partition, _) wants the self-calls inside the
      return's concat (TheAlgorithms quick_sort.py), so the file reached [sequence_query].
   2. A sequence parameter rewritten whole in place, q[:] = E with E read from q (Rosetta insertion-sort-3.py,
      binary insertion): no element write and no return, so no organizer and no node at all.

   deepest_families_v02/2 is replaced, in this process only, by the same deepest paths with these branches
   added; a broad AP13 fallback path (one level, "only when no branch below applies") is dropped when a v0.3
   branch applies, as AP13 itself drops it for its own deeper branches.
*/
:- discontiguous family_path_v03/2.

% --- 1. partition by recursion through variables ---------------------------------------------------------
family_path_v03(F, [sequence_transformation, comparison_sort, partition_recursive]) :-
    once(( seq_param(F, _), in_func(S, F), ret(S, R), joined_parts(R, Ps),
           findall(X, ( member(P, Ps), self_result(F, P, X) ), Xs), length(Xs, K), K >= 2,
           forall(member(X, Xs), compared_part(F, X)) )),
    \+ idiom(F, stooge, _).
% the parts of a join: a + b + c, concat([a, b, c])
joined_parts(op(add, [A, B]), Ps) :- !, joined_parts(A, Pa), joined_parts(B, Pb), append(Pa, Pb, Ps).
joined_parts(concat(Cs), Ps) :- !, maplist(joined_parts, Cs, Pss), append(Pss, Ps).
joined_parts(P, [P]).
% a part that is a recursion result on a variable X: f(x) itself, or a variable assigned f(x)
self_result(_, call('$self', [var(X)]), X) :- atom(X).
self_result(F, var(V), X) :- atom(V), in_func(S, F), assign(S, var(V2), call('$self', [var(X)])), V2 == V, atom(X).
% X is a part: filled by appends of elements under a comparison of an element with another value (the pivot)
compared_part(F, X) :- in_func(S, F), call_at(S, append, [var(X2), _]), X2 == X,
    guard(S, op(Op, _), true), memberchk(Op, [lt, le, gt, ge]), !.

% --- 2. a sequence parameter rewritten whole in place: q[:] = E, E read from q, in a loop ----------------
family_path_v03(F, [sequence_transformation]) :-
    once(( param(F, _, Q), in_func(S, F), assign(S, call(slice, [var(Q2), other(none), other(none)]), E), Q2 == Q,
           sub_term(R, E), R == var(Q), under(S, L), loop(L, F, _) )).

% --- the deepest paths with the v0.3 branches ------------------------------------------------------------
deepest_families_v03(F, Paths) :-
    findall(P, ( family_path(F, P) ; family_path_v02(F, P) ), Ps0),
    findall(P, family_path_v03(F, P), Vs),
    (   Vs == []
    ->  Ps1 = Ps0
    ;   exclude([P]>>( P = [_], \+ memberchk(P, Vs) ), Ps0, Ps2), append(Ps2, Vs, Ps1)
    ),
    sort(Ps1, Ps), exclude(prefix_of_other(Ps), Ps, Paths).

:- abolish(deepest_families_v02/2).
:- assertz((deepest_families_v02(F, Paths) :- deepest_families_v03(F, Paths))).
