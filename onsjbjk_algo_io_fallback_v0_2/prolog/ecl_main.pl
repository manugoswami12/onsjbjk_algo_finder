/* v0.2 (doc 03): Common Lisp via ECL C, traced by the UNCHANGED AP13 v3 rules.
     ecl_main -- Facts : FAMILY|F|Name|Path|Branch lines (Branch = none: no v0.2 branch)
     ecl_dump -- Facts : AP13 dump_main after the ECL normalisation (debugging)
   Load order: the frozen AP12 router (as AP13 cli.py does), AP13 family_main.pl (main, roles, families), then ecl_norm.pl, family_to_v02.pl. */
:- prolog_load_context(directory, Dir),
   directory_file_path(Dir, '../../algo_reference_corpus/ap12/prolog/route_extended.pl', AP12),
   load_files(AP12, [if(not_loaded)]),
   directory_file_path(Dir, '../../polyglot_logic/prolog/family_main.pl', AP13),
   load_files(AP13, [if(not_loaded)]),
   forall(member(F, ['ecl_norm.pl', 'family_to_v02.pl']),
          ( directory_file_path(Dir, F, P), load_files(P, [if(not_loaded)]) )).

ecl_load(Facts) :- load_data(Facts), ecl_normalise, normalise_accessors, assert_observations.

ecl_main :-
    current_prolog_flag(argv, [Facts|_]), ecl_load(Facts),
    forall(func(F, Name, _),
           ( deepest_families(F, Paths),
             forall(member(P, Paths),
                    ( ( family_branch(P, F, B) -> true ; B = none ),
                      atomic_list_concat(P, '>', A), format('FAMILY|~w|~w|~w|~w~n', [F, Name, A, B]) )) )).

ecl_dump :-
    current_prolog_flag(argv, [Facts|_]), ecl_load(Facts),
    forall(func(F, Name, _), (
        format('== ~w ~w~n', [F, Name]),
        forall(( stmt(S, F, K, L) ), format('  stmt ~w ~w ~w~n', [S, K, L])),
        forall(( stmt(S, F, _, _), assign(S, T, V) ), format('  assign ~w ~q := ~q~n', [S, T, V])),
        forall(( stmt(S, F, _, _), par_assign(S, T, V) ), format('  par ~w ~q := ~q~n', [S, T, V])),
        forall(( stmt(S, F, _, _), ret(S, V) ), format('  ret ~w ~q~n', [S, V])),
        forall(( stmt(S, F, _, _), call_at(S, C, V) ), format('  call ~w ~q ~q~n', [S, C, V])),
        forall(( stmt(S, F, _, _), guard(S, C, P) ), format('  guard ~w ~q ~w~n', [S, C, P])),
        forall(( loop(L, F, Kd) ), format('  loop ~w ~w~n', [L, Kd])),
        forall(( loop(L, F, _), loop_cond(L, C) ), format('  lcond ~w ~q~n', [L, C])),
        forall(( loop(L, F, _), loop_var(L, V) ), format('  lvar ~w ~q~n', [L, V])),
        forall(( stmt(S, F, _, _), in_loop(S, L) ), format('  in ~w ~w~n', [S, L])),
        forall(( stmt(S, F, _, _), exchange(S, Q, I, J) ), format('  exch ~w ~q ~q ~q~n', [S, Q, I, J])),
        forall(( role(F, R, X) ), format('  role ~q ~q~n', [R, X])),
        forall(( rec_class(F, R, X) ), format('  rec ~q ~q~n', [R, X])),
        forall(( idiom(F, R, X) ), format('  idiom ~q ~q~n', [R, X])),
        forall(observed(F, X, _), format('  observed ~w~n', [X])),
        forall(family_path(F, P), format('  family ~w~n', [P]))
    )).
