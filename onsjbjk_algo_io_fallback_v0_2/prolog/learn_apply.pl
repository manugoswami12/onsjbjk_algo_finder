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
:- dynamic learned_branch/4, learned_branch/5, learned_ref/4, io_equal/1.

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
    findall(C-L-R, ( member(C, Nodes), holds(C, Streams, L, R) ), Found0), sort(Found0, Found1),
    closest(Found1, Streams, Found),
    forall(member(C-L-R, Found), ( atomic_list_concat(C, '>', CA), format('LEARNED|~w|~w|~w~n', [CA, L, R]) )).
% several labels hold: the label is computed, not blocked (sum(2,X,10)): how much of each clause's example
% the file holds (pattern with the shared part unbound, flow_tokens.pl shared/2), as a share of the
% example's logic tokens; an input->output rule is equal behaviour, a full match. The closest stay; a tie
% keeps them all (ambiguous: UNKNOWN in eval_learn.py).
closest(Found, _, Found) :- findall(L, member(_-L-_, Found), Ls0), sort(Ls0, Ls), length(Ls, N), N =< 1, !.
closest(Found, Streams, Closest) :-
    findall(Sc-(C-L-R), ( member(C-L-R, Found), closeness(C, L, R, Streams, Sc),
                          atomic_list_concat(C, '>', CA), format('CLOSE|~w|~w|~w|~4f~n', [CA, L, R, Sc]) ), Scored),
    aggregate_all(max(Sc), member(Sc-_, Scored), Max),
    findall(X, member(Max-X, Scored), Closest).
closeness(C, L, R, _, 1.0) :- learned_branch(C, L, R, io), !.
closeness(C, L, R, Streams, Sc) :- learned_ref(C, L, R, Ref), length(Ref, N), N > 0, !,
    aggregate_all(max(K), ( member(S, Streams), include(logic_token, S, Ls0), include(ground, Ls0, Ls),
                            ( shared([Ref, Ls], G) -> length(G, K) ; K = 0 ) ), K0),
    Sc is K0 / N.
closeness(_, _, _, _, 0.0).
% the deepest node(s): the paths of the greatest length; a file on no path is at the root
deepest([], [[]]) :- !.
deepest(Paths, Nodes) :- aggregate_all(max(N), ( member(P, Paths), length(P, N) ), Max),
    findall(P, ( member(P, Paths), length(P, Max) ), Nodes).
holds(C, Streams, L, R) :- clause(learned_branch(C, L, R, _, _), _), member(S, Streams),
    phrase(learned_branch(C, L, R), S, _).
holds(C, _, L, R) :- learned_branch(C, L, R, io).
