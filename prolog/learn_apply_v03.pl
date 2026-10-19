/* learn_apply.pl with the v0.3 branches (families_v03.pl); separate from the pipeline, which never loads it.
     learn_apply_main -- Facts Kind Rules Io : as learn_apply.pl
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'learn_apply.pl', A), load_files(A, [if(not_loaded)]),
   directory_file_path(Dir, 'families_v03.pl', V), load_files(V, [if(not_loaded)]).
