/* v0.2 learning (doc 04 section 9): the learned rules applied to a test file at its deepest node.
     learn_apply_main -- Facts Kind Rules Io : NODE|Path for the file's tree nodes, BRANCH_AT|Node|Label for
                                              the labels with a learned branch at its deepest node(s), then
                                              LEARNED|Node|Label|Rule for every learned rule that holds
                                              at the deepest node(s) the file reaches
   Io holds io_equal(Label) facts: the training labels whose input->output behaviour the file has.
   Both predicates (learned_branch//3: logic branch, learned_branch/4: input->output rule) are asked for
   all their answers (findall): no cut, no first match, so the order of the rules decides nothing.
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'tree_main.pl', T), load_files(T, []).
:- dynamic learned_branch/4, learned_branch/5, io_equal/1.

learn_apply_main :-
    current_prolog_flag(argv, [Facts, Kind, Rules, Io|_]),
    ( Kind == lisp -> ecl_load(Facts) ; load_family_data(Facts) ),
    load_files(Rules, [if(true)]), load_files(Io, [if(true)]),
    findall(P, ( func(F, _, _), deepest_families_v02(F, Ps), member(P, Ps) ), Paths0), sort(Paths0, Paths),
    forall(member(P, Paths), ( atomic_list_concat(P, '>', A), format('NODE|~w~n', [A]) )),
    findall(Ts, ( root_function(F, _), result_tokens(F, Ts), Ts \== [] ), Streams),
    deepest(Paths, Nodes),
    % the labels with a learned branch at those nodes (whether one holds is the test, below)
    forall(( member(C, Nodes), setof(L, R^B^clause(learned_branch(C, L, R, _, _), B), Ls), member(L, Ls) ),
           ( atomic_list_concat(C, '>', CA), format('BRANCH_AT|~w|~w~n', [CA, L]) )),
    findall(C-L-R, ( member(C, Nodes), holds(C, Streams, L, R) ), Found0), sort(Found0, Found),
    forall(member(C-L-R, Found), ( atomic_list_concat(C, '>', CA), format('LEARNED|~w|~w|~w~n', [CA, L, R]) )).
% the deepest node(s): the paths of the greatest length; a file on no path is at the root
deepest([], [[]]) :- !.
deepest(Paths, Nodes) :- aggregate_all(max(N), ( member(P, Paths), length(P, N) ), Max),
    findall(P, ( member(P, Paths), length(P, Max) ), Nodes).
holds(C, Streams, L, R) :- clause(learned_branch(C, L, R, _, _), _), member(S, Streams),
    phrase(learned_branch(C, L, R), S, _).
holds(C, _, L, R) :- learned_branch(C, L, R, io).
