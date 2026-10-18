/* v0.2 learning (doc 04 section 14): the learned branches applied to a test file at its deepest node(s).
     learn_apply_main -- Facts Kind Rules Io : NODE|Path for the file's tree nodes, NORMAL|Node|Branch for the
                                              normal process's branch there, BRANCH_AT|Node|Label for the
                                              labels with a learned branch there, LEARNED|Node|Label|Rule for
                                              every branch that holds
   Io holds io_equal(Label) facts: the training labels whose input->output behaviour the file has, and
   io_trace_equal(Label) facts: those whose write trace it has too. All
   answers are collected (findall): no cut, no first match, so the order of the clauses decides nothing.
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'tree_main.pl', T), load_files(T, []).
:- dynamic learned_branch/4, io_equal/1, io_trace_equal/1.

learn_apply_main :-
    current_prolog_flag(argv, [Facts, Kind, Rules, Io|_]), tree_load(Facts, Kind),
    load_files(Rules, [if(true)]), load_files(Io, [if(true)]),
    findall(P, ( func(F, _, _), deepest_families_v02(F, Ps), member(P, Ps) ), Paths0), sort(Paths0, Paths),
    forall(member(P, Paths), ( atomic_list_concat(P, '>', A), format('NODE|~w~n', [A]) )),
    deepest(Paths, Nodes),
    % the normal process's own branch at those nodes (family_to_v02.pl: built branches included)
    forall(( func(F, _, _), deepest_families_v02(F, Ps), member(C, Ps), memberchk(C, Nodes),
             family_branch(C, F, B), B \== none ),
           ( atomic_list_concat(C, '>', CA), format('NORMAL|~w|~w~n', [CA, B]) )),
    forall(( member(C, Nodes), setof(L, R^B^clause(learned_branch(C, L, R, io), B), Ls), member(L, Ls) ),
           ( atomic_list_concat(C, '>', CA), format('BRANCH_AT|~w|~w~n', [CA, L]) )),
    findall(C-L-R, ( member(C, Nodes), learned_branch(C, L, R, io) ), Found0), sort(Found0, Found),
    forall(member(C-L-R, Found), ( atomic_list_concat(C, '>', CA), format('LEARNED|~w|~w|~w~n', [CA, L, R]) )).
% the deepest node(s): the paths of the greatest length; a file on no path is at the root
deepest([], [[]]) :- !.
deepest(Paths, Nodes) :- aggregate_all(max(N), ( member(P, Paths), length(P, N) ), Max),
    findall(P, ( member(P, Paths), length(P, Max) ), Nodes).
