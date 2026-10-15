/* AP13 entry points. Loads the UNCHANGED AP12 router first (it declares
   program/2 and observed/3 dynamic), then the AP13 rules, then data files.
   Run (via tools/env_run.swipl):
     swipl -q -s route_extended.pl -s main.pl -g scan_main  -t halt -- Facts Refs...
     swipl -q -s route_extended.pl -s main.pl -g learn_main -t halt -- Facts Function Label
   Output is a line protocol parsed by tools/report.py. Labels are candidates only.
*/
:- dynamic lang/1, func/3, param/3, stmt/4, loop/3, in_loop/2, loop_var/2, loop_cond/2,
           guard/3, assign/3, par_assign/3, call_at/3, ret/2, next_stmt/2, unsupported/3, loop_iter/2.
:- discontiguous lang/1, func/3, param/3, stmt/4, loop/3, in_loop/2, loop_var/2, loop_cond/2,
                guard/3, assign/3, par_assign/3, call_at/3, ret/2, next_stmt/2, unsupported/3, loop_iter/2.

:- prolog_load_context(directory, Dir),
   forall(member(F, ['canon.pl', 'evidence.pl', 'slice.pl', 'leaf.pl']),
          ( directory_file_path(Dir, F, P), load_files(P, [if(not_loaded)]) )).

% most specific branch first
specificity(interval_lookup, 4).
specificity(indexed_lookup, 3).
specificity(comparison_driven_reordering, 2).
specificity(sequence_rearrangement, 1).
specificity(unknown, 0).

load_data(File) :- load_files(File, [if(true)]).

% Learned references are read as data terms: only reference/4 facts are accepted.
load_reference(File) :-
    setup_call_cleanup(open(File, read, S), read_references(S, File), close(S)).
read_references(S, File) :-
    read_term(S, T, []),
    (   T == end_of_file -> true
    ;   T = reference(_, _, _, _) -> assertz(T), read_references(S, File)
    ;   format(user_error, 'AP13: rejected non-reference term in ~w~n', [File]), halt(2)
    ).

% Feed AP13 evidence into the frozen AP12 router.
assert_observations :-
    retractall(program(_, _)), retractall(observed(_, _, _)),
    forall(func(F, _, _), assertz(program(F, anonymous))),
    forall(distinct(F-X-L, evidence(F, X, L)), assertz(observed(F, X, L))).

routes(F, Rs) :- findall(R, route(F, R), R0), sort(R0, Rs).

scan_main :-
    current_prolog_flag(argv, [Facts|Refs]),
    load_data(Facts), maplist(load_reference, Refs),
    assert_observations,
    forall(func(F, Name, Line), (
        format('FUNC|~w|~w|~w~n', [F, Name, Line]),
        routes(F, Rs), forall(member(R, Rs), format('ROUTE|~w|~w~n', [F, R])),
        forall(observed(F, X, L), format('OBS|~w|~w|~w~n', [F, X, L])),
        forall(unsupported(F, W, L), format('UNSUP|~w|~w|~w~n', [F, W, L]))
    )),
    findall(B, (func(F, _, _), route(F, B), B \== unknown), Bs0), sort([unknown|Bs0], Bs),
    forall(( reference(Label, Branch, _, _), memberchk(Branch, Bs) ),
           leaf_line(Label, Branch)).

leaf_line(Label, Branch) :-
    (   leaf_result(Label, Branch, match(Names, Funcs))
    ->  reference(Label, Branch, Rels, _), length(Rels, NR),
        atomic_list_concat(Names, ',', N), atomic_list_concat(Funcs, ',', Fs),
        format('LEAF|MATCH|~w|~w|~w|~w|~w~n', [Label, Branch, Fs, N, NR])
    ;   leaf_result(Label, Branch, partial(Missing, Present, Total))
    ->  atomic_list_concat(Missing, ',', M0), ( M0 == '' -> M = 'inconsistent_bindings' ; M = M0 ),
        format('LEAF|PARTIAL|~w|~w|~w/~w|~w~n', [Label, Branch, Present, Total, M])
    ;   true
    ).

% G10: learn every function of one source in ONE process.
learn_all_main :-
    current_prolog_flag(argv, [Facts, Prefix]),
    load_data(Facts),
    assert_observations,
    forall(func(F, Name, _), learn_one(F, Name, Prefix)).

learn_one(F, Name, Prefix) :-
    safe_label(Prefix, Name, Label),
    (   catch(slice(F, Rels), _, fail)
    ->  findall(B-S, (reaches(F, G), route(G, B), specificity(B, S)), BS),
        best_branch(BS, Branch),
        quality(Rels, Quality),
        variabilise(Rels, VRels, Names),
        length(Rels, N),
        format('LEARN|~w|~w|~w|~w|~w~n', [Label, Branch, N, Quality, Name]),
        portray_clause(reference(Label, Branch, VRels, Names)),
        format('END~n')
    ;   format('LEARN_EMPTY|~w|~w~n', [Label, Name])
    ).

safe_label(Prefix, Name, Label) :-
    atom_codes(Name, Cs), maplist(safe_code, Cs, Ds), atom_codes(Safe, Ds),
    atomic_list_concat([Prefix, '__', Safe], Label).
safe_code(C, C) :- code_type(C, alnum), !.
safe_code(_, 0'_).

learn_main :-
    current_prolog_flag(argv, [Facts, Function, Label]),
    load_data(Facts),
    assert_observations,
    (   func(F, Name, _), ( Name == Function ; base_name(Name, Function) )
    ->  true
    ;   format('LEARN_ERROR|function not found: ~w~n', [Function]), halt(3)
    ),
    (   slice(F, Rels)
    ->  findall(B-S, (reaches(F, G), route(G, B), specificity(B, S)), BS),
        best_branch(BS, Branch),
        variabilise(Rels, VRels, Names),
        length(Rels, N), quality(Rels, Quality),
        format('LEARN|~w|~w|~w|~w~n', [Label, Branch, N, Quality]),
        portray_clause(reference(Label, Branch, VRels, Names))
    ;   format('LEARN_EMPTY|~w|no effects (no exchange, element write or loop return)~n', [Label])
    ).

best_branch([], unknown).
best_branch(BS, B) :- BS \== [], findall(S-B0, member(B0-S, BS), P), max_member(_-B, P).
