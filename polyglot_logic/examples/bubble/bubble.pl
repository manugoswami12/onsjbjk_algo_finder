pass([X,Y|T], [Y|R]) :- X > Y, !, pass([X|T], R).
pass([X|T], [X|R]) :- pass(T, R).
pass([], []).

bubble_sort(L, S) :- length(L, N), passes(N, L, S).
passes(0, L, L) :- !.
passes(K, L, S) :- pass(L, P), K1 is K - 1, passes(K1, P, S).
