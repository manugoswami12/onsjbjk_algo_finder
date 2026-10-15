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

load_data(File) :- load_files(File, [if(true), encoding(utf8)]).

% Learned references are read as data terms: only reference/4 facts are accepted.
load_reference(File) :-
    setup_call_cleanup(open(File, read, S, [encoding(utf8)]), read_references(S, File), close(S)).
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

% '@File' = one reference path per line (keeps the command line short on Windows)
ref_args([A], Refs) :- atom_concat('@', File, A), !,
    read_file_to_string(File, S, [encoding(utf8)]),
    split_string(S, "\n", "\r ", Parts), exclude(==(""), Parts, Strs),
    maplist([X, Y]>>atom_string(Y, X), Strs, Refs).
ref_args(Refs, Refs).

scan_main :-
    nb_setval(ap13_commute, true),
    current_prolog_flag(argv, [Facts|Args]), ref_args(Args, Refs),
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
    (   leaf_result(Label, Branch, match(Names, Funcs, Cover))
    ->  reference(Label, Branch, Rels, _), length(Rels, NR),
        atomic_list_concat(Names, ',', N), atomic_list_concat(Funcs, ',', Fs),
        ( Cover == full -> Tag = 'MATCH' ; Tag = 'CONTAINS' ),
        format('LEAF|~w|~w|~w|~w|~w|~w~n', [Tag, Label, Branch, Fs, N, NR])
    ;   leaf_result(Label, Branch, partial(Missing, Present, Total)), Present * 4 >= Total * 3
    ->  atomic_list_concat(Missing, ',', M0), ( M0 == '' -> M = 'inconsistent_bindings' ; M = M0 ),
        format('LEAF|PARTIAL|~w|~w|~w/~w|~w~n', [Label, Branch, Present, Total, M])
    ;   true
    ).

% G10: learn every function of one source in ONE process.
learn_all_main :-
    current_prolog_flag(argv, [Facts, Prefix]),
    load_data(Facts),
    assert_observations,
    forall(( func(F, Name, _), Name \== '<toplevel>' ), learn_one(F, Name, Prefix)).   % scripts are not references

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

% ----- generalisation of variants (doc 07) ------------------------------------
% Greedy maximal core: the relations of reference A that hold TOGETHER in the
% facts of variant B. A relation that fails is retried with its integer
% constants abstracted (least general generalisation over constants).
gen_main :-
    nb_setval(ap13_commute, true),
    current_prolog_flag(argv, [Facts|Args]), ref_args(Args, Refs),
    load_data(Facts), maplist(load_reference, Refs),
    forall(reference(Label, Branch, Rels, _), bounded_gen(Label, Branch, Rels)).

% Matching a conjunction is backtracking search: each reference gets a fixed
% inference budget (SWI call_with_inference_limit/3), so one large pair can
% never stall a run. Exceeding it means "no generalisation", never a guess.
bounded_gen(Label, Branch, Rels) :-
    call_with_inference_limit(gen_one(Label, Branch, Rels), 2000000, R),
    ( R == inference_limit_exceeded -> format('SKIP|~w|budget~n', [Label]) ; true ), !.
bounded_gen(_, _, _).

gen_one(Label, Branch, Rels) :-
    copy_term(Rels, R0),
    \+ ( copy_term(R0, T), consistent(T) ),            % A already matches B: nothing to learn
    informative_first(R0, R1), greedy_core(R1, [], Core),
    length(Rels, N), length(Core, NC),
    NC * 10 >= N * 6, NC < N,
    copy_term(Core, Ground), numbervars(Ground, 0, _), quality(Ground, usable), !,   % never bind the core
    core_names(Core, _, Names),
    format('GEN|~w|~w|~w~n', [Label, Branch, NC]),
    portray_clause(reference(gen, Branch, Core, Names)),
    format('END~n').
gen_one(_, _, _).

% the greedy core is order dependent: effects first, bare returns last, so a
% returned variable cannot claim a name the traced computation needs
informative_first(Rs, Sorted) :-
    map_list_to_pairs(rel_rank, Rs, Ps), keysort(Ps, S), pairs_values(S, Sorted).
rel_rank(exchange(_, _, _, _), 0) :- !.
rel_rank(capp(_, _, _), 0) :- !.
rel_rank(value(_, _, _), 1) :- !.
rel_rank(nguard(_, _, _), 2) :- !.
rel_rank(lcond(_, _), 2) :- !.
rel_rank(cret(_, V), 4) :- var_term(V), !.
rel_rank(cret(_, _), 1) :- !.
rel_rank(_, 3).
var_term(V) :- compound(V), V = var(_).

greedy_core([], Kept, Kept).
greedy_core([R|Rs], Kept, Core) :-
    (   append(Kept, [R], Try), copy_term(Try, T), once(consistent(T))
    ->  greedy_core(Rs, Try, Core)
    ;   abstract_ints(R, RA), RA \== R,
        append(Kept, [RA], Try), copy_term(Try, T), once(consistent(T))
    ->  greedy_core(Rs, Try, Core)
    ;   greedy_core(Rs, Kept, Core)
    ).

% the same test the leaf matcher applies: one binding, distinct program names
consistent(T) :- core_names(T, _, Names), maplist(call, T), all_distinct_atoms(Names).

abstract_ints(int(_), int(_)) :- !.
abstract_ints(T, T) :- \+ compound(T), !.
abstract_ints(T0, T) :- T0 =.. [F|As], maplist(abstract_ints, As, Bs), T =.. [F|Bs].

% variables that stand for program names: those inside var(_). Collected from
% term_variables/2, never with findall/3 (which would copy them: fresh variables).
core_names(Core, _, Names) :-
    term_variables(Core, Vs), include(name_var(Core), Vs, Names).
name_var(Core, V) :- sub_term(S, Core), compound(S), S = var(W), W == V, !.
