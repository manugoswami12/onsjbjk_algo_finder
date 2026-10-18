/* v0.2 call roots (doc 04 section 18.2), for the separate four-way answer test only: which of the file's own
   functions no other own function calls. A class decided on a helper (an is_prime inside next_prime, f(x) = x*x inside
   Simpson's rule) is not the file's algorithm; the file's algorithm is what its roots compute.
     roots_main -- Facts Kind : prints FUNC|Name for every function and ROOT|Name for every root
   Calls from top-level code or main (a demo, a print) do not make a function a helper; operator methods
   (__lt__) are not roots.
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'ta_signature.pl', T), load_files(T, []).

roots_main :-
    current_prolog_flag(argv, [Facts, Kind|_]), tree_load(Facts, Kind),
    forall(( func(F, N, _), \+ demo(N) ), ( format('FUNC|~w~n', [N]),
        ( \+ called_by_other(F), \+ operator_method(N) -> format('ROOT|~w~n', [N]) ; true ) )).
% demo code: top-level statements and a main function (C's main, Python's main()): their calls do not make a function
% a helper, and they are not the algorithm
demo('<toplevel>').
demo(N) :- base_name(N, main).
% an operator method (__lt__, __eq__) is called by an operator, never by name
operator_method(N) :- sub_atom(N, _, _, 0, '__'), sub_atom(N, B, _, _, '.__'), B > 0, !.
% called_by_other(G): a statement of another own function (not top-level code) calls G
called_by_other(G) :-
    func(G, GN, _), base_name(GN, B),
    in_func(S, F), F \== G, func(F, FN, _), \+ demo(FN), \+ nested_in(GN, FN),
    calls(S, B, GN), !.
called_by_other(G) :-                      % a function nested in another (a where clause, an inner def) is its helper
    func(G, GN, _), func(F, FN, _), F \== G, \+ demo(FN), nested_in(FN, GN), !.
% nested_in(Outer, Inner): Inner is defined inside Outer (Outer.inner)
nested_in(Outer, Inner) :- atom_concat(Outer, '.', P), atom_concat(P, _, Inner).
% calls(S, B, GN): statement S calls B (or GN), as a call statement or inside its relation (a loop condition, a guard)
calls(S, B, GN) :- ( call_at(S, N, _) ; component(S, R), sub_term(C, R), compound(C), C = call(N, _) ), atom(N),
    ( N == B ; N == GN ), !.
