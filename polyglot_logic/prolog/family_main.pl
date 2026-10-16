/* AP13 v3 entry points (doc 08). Loads the UNCHANGED main.pl (and with it canon,
   evidence, slice, leaf and the frozen AP12 router) and ADDS roles.pl and
   families.pl. No existing predicate is redefined.
     family_main  -- Facts         : FAMILY|F|Name|Path lines
     dump_main    -- Facts         : canonical relations per function (debugging)
*/
:- prolog_load_context(directory, Dir),
   forall(member(F, ['main.pl', 'roles.pl', 'families.pl']),
          ( directory_file_path(Dir, F, P), load_files(P, [if(not_loaded)]) )).

% Accessor calls the lowerers leave as calls (Lisp elt/aref/nth) become elem/2 for the
% family layer only: base facts are rewritten after loading, no lowerer is changed.
accessor(call(A, [Q, I]), elem(Q, I)) :- memberchk(A, [elt, aref, svref, char, schar, at, get]).
accessor(call(nth, [I, Q]), elem(Q, I)).
accessor(call(A, [Q]), elem(Q, int(0))) :- memberchk(A, [car, first, head, hd]).
accessor(call(A, [Q]), tail(Q, 1)) :- memberchk(A, [cdr, rest, tail, tl]).
accessor(call(A, [_, Q]), filter(Q, other(predicate))) :- memberchk(A, ['remove-if-not', 'remove-if', filter]).
norm_access(T, T) :- \+ compound(T), !.
norm_access(T0, T) :- accessor(T0, T1), !, norm_access(T1, T).
norm_access(T0, T) :- T0 =.. [F|As], maplist(norm_access, As, Bs), T =.. [F|Bs].
normalise_accessors :-
    forall(member(P/N, [assign/3, par_assign/3, guard/3, ret/2, call_at/3, loop_cond/2, loop_iter/2]),
           ( functor(H, P, N),
             forall(( retract(H) ), ( norm_access(H, H1), assertz(H1) )) )).

load_family_data(Facts) :- load_data(Facts), normalise_accessors, assert_observations.

family_main :-
    current_prolog_flag(argv, [Facts|_]),
    load_family_data(Facts),
    forall(func(F, Name, _),
           ( deepest_families(F, Paths),
             forall(member(P, Paths),
                    ( atomic_list_concat(P, '>', A), format('FAMILY|~w|~w|~w~n', [F, Name, A]) )) )).

dump_main :-
    current_prolog_flag(argv, [Facts|_]),
    load_family_data(Facts),
    forall(func(F, Name, _), (
        format('== ~w ~w~n', [F, Name]),
        forall(param(F, K, P), format('  param ~w ~w~n', [K, P])),
        forall(( loop(L, F, Kd) ), format('  loop ~w ~w~n', [L, Kd])),
        forall(( stmt(S, F, _, _), value(S, T, V) ), format('  value ~w ~q := ~q~n', [S, T, V])),
        forall(( stmt(S, F, _, _), cret(S, V) ), format('  cret ~w ~q~n', [S, V])),
        forall(( stmt(S, F, _, _), capp(S, Q, X) ), format('  capp ~w ~q ~q~n', [S, Q, X])),
        forall(( stmt(S, F, _, _), exchange(S, Q, I, J) ), format('  exch ~w ~q ~q ~q~n', [S, Q, I, J])),
        forall(( stmt(S, F, _, _), nguard(S, C, P) ), format('  guard ~w ~q ~w~n', [S, C, P])),
        forall(( loop(L, F, _), lcond(L, C) ), format('  lcond ~w ~q~n', [L, C])),
        forall(( loop(L, F, _), lvar(L, V) ), format('  lvar ~w ~q~n', [L, V])),
        forall(( loop(L, F, _), loop_iter(L, Q) ), format('  liter ~w ~q~n', [L, Q])),
        forall(( stmt(S, F, _, _), under(S, L) ), format('  under ~w ~w~n', [S, L])),
        forall(( stmt(S, F, _, _), seed(V, C) ), true),
        forall(observed(F, X, _), format('  observed ~w~n', [X])),
        forall(route(F, R), format('  route ~w~n', [R]))
    )).
