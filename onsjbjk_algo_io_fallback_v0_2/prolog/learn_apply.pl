/* v0.2 learning (doc 04): the learned DCGs applied to a test file.
     learn_apply_main -- Facts Rules : LEARNED|Name|Label|Rule for every root function a rule parses
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'flow_main.pl', T), load_files(T, []).
:- dynamic learned_pattern/4.

learn_apply_main :-
    current_prolog_flag(argv, [Facts, Rules|_]), load_files(Facts, [if(true)]), load_files(Rules, [if(true)]),
    forall(( root_function(F, Name), result_tokens(F, Ts), Ts \== [],
             once(phrase(learned_pattern(L, R), Ts)) ),
           format('LEARNED|~w|~w|~w~n', [Name, L, R])).
