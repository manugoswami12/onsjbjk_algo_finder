/* v0.2 (doc 03): Common Lisp via ECL C, traced by the UNCHANGED AP13 v3 rules.
     ecl_main -- Facts : FAMILY|F|Name|Path|Branch lines (Branch = none: no v0.2 branch)
     ecl_dump -- Facts : AP13 dump_main after the ECL normalisation (debugging)
   Load order: the frozen AP12 router (as AP13 cli.py does), AP13 family_main.pl (main, roles, families), then ecl_norm.pl, families_v02.pl, family_to_v02.pl. */
:- prolog_load_context(directory, Dir),
   directory_file_path(Dir, '../older_code/algo_reference_corpus/ap12/prolog/route_extended.pl', AP12),
   load_files(AP12, [if(not_loaded)]),
   directory_file_path(Dir, '../polyglot_logic/prolog/family_main.pl', AP13),
   load_files(AP13, [if(not_loaded)]),
   forall(member(F, ['ecl_norm.pl', 'families_v02.pl', 'family_to_v02.pl']),
          ( directory_file_path(Dir, F, P), load_files(P, [if(not_loaded)]) )).

ecl_load(Facts) :- load_data(Facts), ecl_normalise, normalise_accessors, assert_observations.

ecl_main :-
    current_prolog_flag(argv, [Facts|_]), ecl_load(Facts),
    ( no_algorithm -> format('NOCODE~n') ; true ),
    forall(func(F, Name, _),
           ( deepest_families_v02(F, Paths),
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
        forall(( family_path(F, P) ; family_path_v02(F, P) ), format('  family ~w~n', [P]))
    )).

% the normal process's output for the fallback (ecl_fallback.py): the facts after ecl_norm and the
% FAMILY answers, as Prolog terms (read by prolog/fallback_main.pl only)
ecl_export :-
    current_prolog_flag(argv, [Facts|_]), ecl_load(Facts),
    forall(member(P/N, [func/3, param/3, stmt/4, loop/3, in_loop/2, loop_var/2, loop_cond/2, loop_iter/2, tail_loop/1,
                        guard/3, assign/3, par_assign/3, call_at/3, ret/2]),
           ( functor(H, P, N), forall(H, portray_clause(H)) )),
    forall(func(F, _, _),
           ( deepest_families_v02(F, Paths),
             forall(member(Pa, Paths), ( ( family_branch(Pa, F, B) -> true ; B = none ),
                                         portray_clause(family(F, Pa, B)) )) )).

% a file without an algorithm of its own: it defines no function (only top-level code) and that code
% calls a function defined elsewhere (a driver: (bubble-sort (list 5 4 3 2 1))) or neither loops
% nor recurses (a REPL transcript: (lcm 12 18)); decided from the traced facts, never the text
no_algorithm :-
    func(_, _, _), \+ ( func(_, N, _), N \== '<toplevel>' ),
    ( delegated_call(_) -> true ; \+ loop(_, _, _) ).
delegated_call(G) :-
    ( call_at(_, G, _) ; ( assign(_, _, V) ; ret(_, V) ; call_at(_, _, V) ; guard(_, V, _) ),
      sub_term(C, V), compound(C), C = call(G, _) ),
    atom(G), \+ runtime_or_defined(G), !.
runtime_or_defined(G) :- func(_, G, _), !.
runtime_or_defined(G) :- memberchk(G, ['$self', len, reverse, compare, append, collect, rplacd, slice,
                                       ecl_function, ecl_symbol, ecl_keyword, ecl_key_default, expr]), !.
runtime_or_defined(G) :- member(P, [cl_, ecl_, si_, 'ECL_', '_ecl', 'FE', va_]), sub_atom(G, 0, _, _, P), !.
