/* v0.2 learning (doc 04): the logic-flow token streams of a file's root functions.
     flow_main -- Facts : STREAM|Name|Tokens (Tokens a Prolog term)
   Roots: functions no other function of the file calls (they reach the rest through links);
   driver code (<toplevel>, main) only when the file has nothing else (a script).
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'flow_tokens.pl', T), load_files(T, []).

flow_main :-
    current_prolog_flag(argv, [Facts|_]), load_files(Facts, [if(true)]),
    forall(( root_function(F, Name), result_tokens(F, Ts), Ts \== [] ),
           format('STREAM|~w|~q~n', [Name, Ts])).
% driver code (<toplevel>, C's main) neither makes a function non-root nor is a root itself
% unless the file has nothing else
root_function(F, Name) :-
    func(F, Name, _), \+ called(Name),
    ( \+ driver(Name) -> true ; \+ ( func(_, N2, _), \+ driver(N2) ) ).
driver('<toplevel>').
driver(main).
called(Name) :- func(G, GN, _), \+ driver(GN), GN \== Name, stmt(S, G, _, _),
    ( call_at(S, Name, _) ; ( assign(S, _, V) ; ret(S, V) ), sub_term(C, V), compound(C), C = call(Name, _) ), !.
