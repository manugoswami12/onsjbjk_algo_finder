/* A whole-slice write q[:] = E of a parameter q in a function that returns nothing (doc 04 section 19.7): the
   function rewrites q in place with E, so it is a write of q with value E and q is its output (the in-place result).
   A function that returns a value already names its output; its facts are left as they are.
     slice_write   rewrites the loaded facts (called by tree_main.pl tree_load/2 before trace_returns)
*/
slice_write :-
    forall(( assign(S, T, E), T = call(slice, [var(Q), other(none), other(none)]), stmt(S, F, _, L), param(F, _, Q),
             \+ ( stmt(X, F, _, _), ret(X, _) ) ),
           ( retract(assign(S, T, E)), assertz(assign(S, var(Q), E)),
             atom_concat(S, '_out', R), assertz(stmt(R, F, ret, L)), assertz(ret(R, var(Q))) )).
