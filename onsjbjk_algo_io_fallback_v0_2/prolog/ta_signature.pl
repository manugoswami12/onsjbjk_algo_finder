/* v0.2 helper for writing file rules by hand (doc 04 section 17.5): every statement's relation (AP13 rel_of/2) with
   its local variables renamed to v, its parameters to their position p(K), and the file's own function names to fn,
   so that the same component written with other names gives the same term. Constants, operators and library calls are
   kept.
     signature_main -- Facts Kind : prints SIG|Term for every distinct abstracted relation of the file
   ta_file_rules.pl matches a written signature with has_rel/2 (the same abstraction).
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'tree_main.pl', T), load_files(T, []).

signature_main :-
    current_prolog_flag(argv, [Facts, Kind|_]), tree_load(Facts, Kind),
    forall(distinct(A, ( in_func(S, F), rel_of(S, R), abstract(F, R, A) )), format('SIG|~q~n', [A])).

% abstract(+F, +Term, -Abstract): a parameter of F -> var(p(K)); another var(Name) -> var(v);
% call(own function, Args) -> call(fn, Args); the rest kept
abstract(_, T, T) :- var(T), !.
abstract(F, var(N), var(p(K))) :- param(F, K, N), !.
abstract(_, var(_), var(v)) :- !.
abstract(F, call(G, As), call(fn, Bs)) :- atom(G), G \== '$self', own_function(G), !, maplist(abstract(F), As, Bs).
abstract(_, T, T) :- \+ compound(T), !.
abstract(F, T0, T) :- T0 =.. [Fn|As], maplist(abstract(F), As, Bs), T =.. [Fn|Bs].
own_function(G) :- func(_, N, _), base_name(N, G), !.

% has_rel(F, A): a statement of F has the abstracted relation A
has_rel(F, A) :- in_func(S, F), rel_of(S, R), abstract(F, R, A0), A0 == A, !.
