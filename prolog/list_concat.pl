/* `+` on lists is concatenation (doc 04 section 19.3). Python (and Haskell's ++, already concat) join lists with `+`,
   which the lowerer keeps as arithmetic op(add, [A, B]); the same join written [*a, *b] lowers to concat([A, B]).
   An add with an operand that is a list is a concat, flattened: a list literal list(_), a concat, or a variable of
   the function that is created as a list (x = [] or x = [...]) and never given a number. The same in every language;
   nothing names an algorithm.
     list_concat   rewrites ret/2 and assign/3 values (called by tree_main.pl tree_load/2 after trace_returns)
*/
list_concat :-
    forall(( ret(S, R), stmt(S, F, _, _), lc_rewrite(F, R, R1), R1 \== R ), ( retract(ret(S, R)), assertz(ret(S, R1)) )),
    forall(( assign(S, T, V), stmt(S, F, _, _), lc_rewrite(F, V, V1), V1 \== V ),
           ( retract(assign(S, T, V)), assertz(assign(S, T, V1)) )).

lc_rewrite(_, T, T) :- \+ compound(T), !.
lc_rewrite(F, op(add, [A0, B0]), T) :- !,
    lc_rewrite(F, A0, A), lc_rewrite(F, B0, B),
    (   ( lc_list(F, A) ; lc_list(F, B) )
    ->  lc_parts(A, PA), lc_parts(B, PB), append(PA, PB, Ps), T = concat(Ps)
    ;   T = op(add, [A, B])
    ).
lc_rewrite(F, T0, T) :- T0 =.. [Fn|As], maplist(lc_rewrite(F), As, Bs), T =.. [Fn|Bs].

lc_parts(concat(Ps), Ps) :- !.
lc_parts(P, [P]).

% a term known to be a list in F
lc_list(_, list(_)) :- !.
lc_list(_, concat(_)) :- !.
lc_list(F, var(X)) :- atom(X), once(( assign(D, V, list(_)), V == var(X), stmt(D, F, _, _) )),
    \+ ( assign(D2, V2, N), V2 == var(X), stmt(D2, F, _, _), lc_number(N) ).
lc_number(int(_)).
lc_number(num(_)).
lc_number(op(O, _)) :- memberchk(O, [sub, mul, div, mod, fdiv, pow]).
