/* AP13 v4 (doc 10): a Prolog SOURCE is already the normal form; run it natively.
   swipl ... -g native_main -- Source JobsFile
   Clauses are read as terms and asserted into the isolated module ap13cand; directives
   are NEVER executed (no :- initialization(main)). Each job calls Name with the input
   arguments plus one output argument (Mode = out) or none (Mode = test: true/false).
   Output is captured, the inference limit bounds every call.
     job(Id, Name, Mode, [Arg...]).
     RES|Id|ok|Result        RES|Id|err|Reason
*/
native_main :-
    current_prolog_flag(argv, [Src, Jobs|_]),
    load_candidate(Src),
    read_file_to_terms(Jobs, Js, [encoding(utf8)]),
    forall(member(job(Id, F, Mode, Args), Js), native_job(Id, F, Mode, Args)),
    forall(cand_pred(N, A), format('PRED|~w|~w~n', [N, A])).

:- dynamic cand_pred/2.

load_candidate(Src) :-
    setup_call_cleanup(open(Src, read, S, [encoding(utf8)]), read_clauses(S), close(S)).
read_clauses(S) :-
    catch(read_term(S, T, []), error(syntax_error(_), _), T = '$skip'),
    (   T == end_of_file -> true
    ;   T = (:- op(P, Ty, Ns)) -> catch(op(P, Ty, ap13cand:Ns), _, true), read_clauses(S)
    ;   T = (:- _) -> read_clauses(S)                       % never execute a directive
    ;   T == '$skip' -> read_clauses(S)
    ;   T = (H --> B) -> catch(( dcg_translate_rule((H --> B), C), assertz(ap13cand:C), note(C) ), _, true),
        read_clauses(S)
    ;   catch(( assertz(ap13cand:T), note(T) ), _, true), read_clauses(S)
    ).
note((H :- _)) :- !, note(H).
note(H) :- callable(H), functor(H, N, A), ( cand_pred(N, A) -> true ; assertz(cand_pred(N, A)) ).

native_job(Id, F, Mode, Args) :-
    (   Mode == out -> append(Args, [Out], All) ; All = Args ),
    G =.. [F|All],
    catch(call_with_inference_limit(
              with_output_to(string(_), ( ap13cand:G -> R0 = yes ; R0 = no )), 2000000, Lim),
          E, Lim = error(E)),
    (   Lim == inference_limit_exceeded -> format('RES|~w|err|timeout~n', [Id])
    ;   Lim = error(E2) -> format('RES|~w|err|~q~n', [Id, E2])
    ;   Mode == test -> ( R0 == yes -> format('RES|~w|ok|true~n', [Id]) ; format('RES|~w|ok|false~n', [Id]) )
    ;   R0 == no -> format('RES|~w|err|failed~n', [Id])
    ;   ground(Out) -> format('RES|~w|ok|~q~n', [Id, Out])
    ;   format('RES|~w|err|nonground~n', [Id])
    ).
