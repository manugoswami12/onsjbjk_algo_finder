/* AP13 v4 run entry (doc 10).  swipl ... -g run_main -- PnfFile JobsFile
   JobsFile: job(Id, FunctionName, [Arg...]).   Output, one line per job:
     RES|Id|ok|Result|FinalArgs|TraceFingerprint|TraceLength
     RES|Id|err|Reason
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'interp.pl', P), load_files(P, [if(not_loaded)]).

run_main :-
    current_prolog_flag(argv, [Pnf, Jobs|_]),
    load_files(Pnf, [encoding(utf8)]),
    read_file_to_terms(Jobs, Js, [encoding(utf8)]),
    forall(member(job(Id, F, Args), Js), run_job(Id, F, Args)).

run_job(Id, F, Args) :-
    catch(call_with_inference_limit(run_fun(F, Args, R, Fin, Tr), 2000000, Lim), E, (Lim = error(E))),
    (   Lim == inference_limit_exceeded -> format('RES|~w|err|timeout~n', [Id])
    ;   Lim = error(E2) -> ( E2 = pnf_error(Why) -> true ; Why = E2 ),
        format('RES|~w|err|~q~n', [Id, Why])
    ;   variant_sha1(Tr, H), include([X]>>(X = w(_, _, _) ; X = r(_, _)), Tr, Ev), length(Ev, NT),
        include([X]>>(X = w(_, _, _)), Tr, Ws), length(Ws, NW),
        nb_getval(ap13_printed, P0), reverse(P0, Printed),
        ( R == none, Printed \== [] -> R2 = printed(Printed) ; R2 = R ),
        format('RES|~w|ok|~q|~q|~w|~w|~w~n', [Id, R2, Fin, H, NT, NW])
    ).
