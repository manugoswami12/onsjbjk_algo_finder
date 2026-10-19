/* v0.2 learning (doc 04 section 14): the tree nodes of a file: the deepest family paths of its functions,
   decided by the normal process's relations (AP12, AP13 families, families_v02.pl).
     tree_main -- Facts Kind : NODE|Name|Path
   Kind lisp: ECL facts, normalised as ecl_main.pl does; any other: AP13 lowerer facts (load_family_data), with a
   returned value traced through the variable that holds a recursive call (trace_returns.pl).
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'ecl_main.pl', P), load_files(P, [if(not_loaded)]),
   directory_file_path(Dir, 'trace_returns.pl', R), load_files(R, [if(not_loaded)]).

tree_load(Facts, Kind) :-
    ( Kind == lisp -> ecl_load(Facts) ; load_data(Facts), normalise_accessors, row_major, trace_returns, assert_observations ).
% AP13's load_family_data with one more normalisation: a row-major index q[r * d + c] with a non-constant
% stride d (C's flat 2-D arrays) is q[r][c], as ecl_norm.pl already reads ECL's (aref m i j)
row_major :-
    forall(member(P/N, [assign/3, par_assign/3, guard/3, ret/2, call_at/3, loop_cond/2, loop_iter/2]),
           ( functor(H, P, N), forall(retract(H), ( rm_term(H, H1), assertz(H1) )) )).
rm_term(T, T) :- \+ compound(T), !.
rm_term(elem(Q0, op(add, [op(mul, [R0, D]), C0])), elem(elem(Q, R), C)) :- D \= int(_), !,
    rm_term(Q0, Q), rm_term(R0, R), rm_term(C0, C).
rm_term(T0, T) :- T0 =.. [F|As], maplist(rm_term, As, Bs), T =.. [F|Bs].
tree_main :-
    current_prolog_flag(argv, [Facts, Kind|_]), tree_load(Facts, Kind),
    forall(( func(F, Name, _), deepest_families_v02(F, Paths), member(P, Paths) ),
           ( atomic_list_concat(P, '>', A), format('NODE|~w|~w~n', [Name, A]) )).
