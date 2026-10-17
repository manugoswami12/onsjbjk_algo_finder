/* v0.2 learning (doc 04 section 8): the learned branches applied to a test file, deepest node first.
     learn_apply_main -- Facts Kind Rules : NODE|Path for the file's tree nodes, then
                                           LEARNED|Node|Label|Rule for the learned children of the deepest
                                           reached node that has a child holding a root stream
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'tree_main.pl', T), load_files(T, []).
:- dynamic learned_branch/5.

learn_apply_main :-
    current_prolog_flag(argv, [Facts, Kind, Rules|_]),
    ( Kind == lisp -> ecl_load(Facts) ; load_family_data(Facts) ),
    load_files(Rules, [if(true)]),
    findall(P, ( func(F, _, _), deepest_families_v02(F, Ps), member(P, Ps) ), Paths0), sort(Paths0, Paths),
    forall(member(P, Paths), ( atomic_list_concat(P, '>', A), format('NODE|~w~n', [A]) )),
    findall(Ts, ( root_function(F, _), result_tokens(F, Ts), Ts \== [] ), Streams),
    % the reached nodes: every prefix of a path (the root [] included), deepest first
    findall(N-C, ( member(P, Paths), append(C, _, P), length(C, N) ), NCs0), ( NCs0 == [] -> NCs1 = [0-[]] ; NCs1 = NCs0 ),
    sort(NCs1, NCs2), reverse(NCs2, NCs), pairs_values(NCs, Nodes),
    (   member(C, Nodes),
        findall(L-R, ( clause(learned_branch(C, L, R, _, _), _), member(S, Streams),
                       once(phrase(learned_branch(C, L, R), S, _)) ), Found0),
        Found0 \== []
    ->  sort(Found0, Found), atomic_list_concat(C, '>', CA),
        forall(member(L-R, Found), format('LEARNED|~w|~w|~w~n', [CA, L, R]))
    ;   true
    ).
