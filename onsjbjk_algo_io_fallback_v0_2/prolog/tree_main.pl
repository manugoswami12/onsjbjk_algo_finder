/* v0.2 learning (doc 04 section 14): the tree nodes of a file: the deepest family paths of its functions,
   decided by the normal process's relations (AP12, AP13 families, families_v02.pl).
     tree_main -- Facts Kind : NODE|Name|Path
   Kind lisp: ECL facts, normalised as ecl_main.pl does; any other: AP13 lowerer facts (load_family_data).
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'ecl_main.pl', P), load_files(P, [if(not_loaded)]).

tree_load(Facts, Kind) :- ( Kind == lisp -> ecl_load(Facts) ; load_family_data(Facts) ).
tree_main :-
    current_prolog_flag(argv, [Facts, Kind|_]), tree_load(Facts, Kind),
    forall(( func(F, Name, _), deepest_families_v02(F, Paths), member(P, Paths) ),
           ( atomic_list_concat(P, '>', A), format('NODE|~w|~w~n', [Name, A]) )).
