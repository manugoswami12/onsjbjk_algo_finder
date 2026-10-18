/* v0.3 run entry (doc 04 section 18.4): AP13's run_main.pl with the v0.3 interpreter (prolog/interp_v03.pl).
   swipl ... -g run_main -- PnfFile JobsFile ; output as run_main.pl's (RES|Id|ok|... / RES|Id|err|Reason).
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'interp_v03.pl', P), load_files(P, [if(not_loaded)]).
:- prolog_load_context(directory, Dir), directory_file_path(Dir, '../polyglot_logic/prolog/run_main.pl', P),
   load_files(P, [if(not_loaded)]).
