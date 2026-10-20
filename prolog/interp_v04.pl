/* v0.4 interpreter additions (doc 04 section 19.8), loaded before interp_v03.pl (and through it AP13's interp.pl);
   each clause applies only where the interpreter would throw: zip of any number of sequences, min/max of any number of numbers, itertools.accumulate
   (with or without a function), functools.reduce (as plain recursion over the state), a boolean operand of + - * as 0 or 1. */
:- multifile eval/4, builtin/5.
% a boolean in arithmetic is 0 or 1 (Python's True == 1, C's comparisons): only an operand that is a boolean is
% read as a number; the other operator forms are interp.pl's (lit/1 values go to its clause)
eval(op(O, [A, B]), S0, S, V) :- memberchk(O, [add, sub, mul]), \+ ( A = lit(_), B = lit(_) ), !,
    eval(A, S0, S1, AV), eval(B, S1, S2, BV), bool_number(AV, A1), bool_number(BV, B1), eval(op(O, [lit(A1), lit(B1)]), S2, S, V).
bool_number(true, 1) :- !.
bool_number(false, 0) :- !.
bool_number(X, X).
builtin(zip, Qs, S0, S, R) :- Qs = [_, _, _|_], !, S0 = s(_, H, _, _), maplist([Q, L]>>elements(Q, H, L), Qs, Ls),
    zip_n(Ls, Ts), new_list(Ts, S0, S, R).
builtin(min, [A, B, C|Rest], S, S, V) :- maplist(number, [A, B, C|Rest]), !, min_list([A, B, C|Rest], V).
builtin(max, [A, B, C|Rest], S, S, V) :- maplist(number, [A, B, C|Rest]), !, max_list([A, B, C|Rest], V).
builtin(accumulate, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L), sums(L, 0, Ys), new_list(Ys, S0, S, R).
builtin(accumulate, [Q, C], S0, S, R) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, L),
    ( L = [X|Xs] -> scan_values(Xs, C, X, Ys, S0, S1) ; Ys = [], S1 = S0 ), new_list(Ys, S1, S, R).
builtin(reduce, [C, Q], S0, S, V) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, [X|L]), fold_values(L, C, X, V, S0, S).
builtin(reduce, [C, Q, I], S0, S, V) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, L), fold_values(L, C, I, V, S0, S).
% scan_values(+Rest, +F, +Acc, -[Acc|Accs]): Acc then F(Acc, Y) for each Y (itertools.accumulate)
scan_values([], _, A, [A], S, S).
scan_values([Y|Ys], C, A0, [A0|As], S0, S) :- apply_value(C, [A0, Y], S0, S1, A), scan_values(Ys, C, A, As, S1, S).
fold_values([], _, A, A, S, S).
fold_values([Y|Ys], C, A0, A, S0, S) :- apply_value(C, [A0, Y], S0, S1, A1), fold_values(Ys, C, A1, A, S1, S).
zip_n(Ls, []) :- member([], Ls), !.
zip_n(Ls, [t(Hs)|Ts]) :- maplist([[X|Xs], X, Xs]>>true, Ls, Hs, Rest), zip_n(Rest, Ts).
sums([], _, []).
sums([X|Xs], A0, [A|As]) :- A is A0 + X, sums(Xs, A, As).
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'interp_v03.pl', P), load_files(P, [if(not_loaded)]).
