/* v0.2 learning round 3 (doc 04 section 8): the tree node and the logic streams of a file, one process.
     tree_main -- Facts Kind : NODE|Name|Path for the deepest family paths of every function (the normal
                               process's tree), STREAM|Name|Tokens for every root function
   Kind lisp: ECL facts, normalised as ecl_main.pl does; any other: AP13 lowerer facts (load_family_data).
*/
:- prolog_load_context(directory, Dir),
   forall(member(F, ['ecl_main.pl', 'flow_main.pl']),
          ( directory_file_path(Dir, F, P), load_files(P, [if(not_loaded)]) )).

tree_main :-
    current_prolog_flag(argv, [Facts, Kind|_]),
    ( Kind == lisp -> ecl_load(Facts) ; load_family_data(Facts) ),
    forall(( func(F, Name, _), deepest_families_v02(F, Paths), member(P, Paths) ),
           ( atomic_list_concat(P, '>', A), format('NODE|~w|~w~n', [Name, A]) )),
    forall(( root_function(F, Name), result_tokens(F, Ts), Ts \== [] ),
           format('STREAM|~w|~q~n', [Name, Ts])).
