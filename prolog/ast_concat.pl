/* `+` on lists is concat (doc 04 section 19.7), told by Python about its own programs (pyast_facts.py): tree-sitter
   gives only `+`, so the facts kept it as arithmetic op(add, [A, B]); the same join written [*a, *b] lowers to
   concat([A, B]). An add with an operand that is a list is a concat, flattened. A list: a list literal, a concat, a
   comprehension (map/filter), a name Python's ast found to hold a list (list_var/2), a slice of a list or of a sliced
   parameter (list_param/2), or a call of a function returning a list (list_func/1; the recursive call included).
     ast_concat   rewrites ret/2 and assign/3 values (called by tree_main.pl tree_load/2 after trace_returns)
*/
:- dynamic list_var/2, list_func/1, list_param/2, ac_joined/1.

ast_concat :-
    forall(( ret(S, R), stmt(S, F, _, _), ac_rewrite(F, R, R1), R1 \== R ),
           ( retract(ret(S, R)), assertz(ret(S, R1)), assertz(ac_joined(S)) )),
    forall(( assign(S, T, V), stmt(S, F, _, _), ac_rewrite(F, V, V1), V1 \== V ),
           ( retract(assign(S, T, V)), assertz(assign(S, T, V1)) )).

ac_rewrite(_, T, T) :- \+ compound(T), !.
ac_rewrite(F, op(add, [A0, B0]), T) :- !,
    ac_rewrite(F, A0, A), ac_rewrite(F, B0, B),
    (   ( ac_list(F, A) ; ac_list(F, B) )
    ->  ac_parts(A, PA), ac_parts(B, PB), append(PA, PB, Ps), T = concat(Ps)
    ;   T = op(add, [A, B])
    ).
ac_rewrite(F, T0, T) :- T0 =.. [Fn|As], maplist(ac_rewrite(F), As, Bs), T =.. [Fn|Bs].

ac_parts(concat(Ps), Ps) :- !.
ac_parts(P, [P]).

% a term that is a list in function F (named Name as pyast_facts.py names it)
ac_list(_, list(_)) :- !.
ac_list(_, concat(_)) :- !.
ac_list(_, map(_, _, _)) :- !.
ac_list(_, filter(_, _)) :- !.
ac_list(F, var(X)) :- atom(X), func(F, N, _), list_var(N, X), !.
ac_list(F, call(slice, [Q|_])) :- ( ac_list(F, Q) -> true ; Q = var(P), atom(P), func(F, N, _), list_param(N, P) ), !.
ac_list(F, call('$self', _)) :- func(F, N, _), list_func(N), !.
ac_list(_, call(G, _)) :- atom(G), G \== '$self', list_func(Q), atomic_list_concat(Parts, '.', Q), last(Parts, G), !.
