/* tree_main.pl with the v0.3 branches (families_v03.pl); separate from the pipeline, which never loads it.
     tree_main -- Facts Kind : NODE|Name|Path
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'tree_main.pl', T), load_files(T, [if(not_loaded)]),
   directory_file_path(Dir, 'families_v03.pl', V), load_files(V, [if(not_loaded)]).
