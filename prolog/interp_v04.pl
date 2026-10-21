/* v0.4 interpreter additions (doc 04 section 19.8), loaded before interp_v03.pl (and through it AP13's interp.pl);
   each clause applies only where the interpreter would throw: zip of any number of sequences, min/max of any number of numbers, itertools.accumulate
   (with or without a function), functools.reduce (as plain recursion over the state), a boolean operand of + - * as 0 or 1. */
:- multifile eval/4, builtin/5.
% a boolean in arithmetic is 0 or 1 (Python's True == 1, C's comparisons): only an operand that is a boolean is
% read as a number; the other operator forms are interp.pl's (lit/1 values go to its clause)
eval(op(O, [A, B]), S0, S, V) :- memberchk(O, [add, sub, mul]), \+ ( A = lit(_), B = lit(_) ), !,
    eval(A, S0, S1, AV), eval(B, S1, S2, BV), bool_number(AV, A1), bool_number(BV, B1), eval(op(O, [lit(A1), lit(B1)]), S2, S, V).
% Python's // of two integers floors (-1 // 2 == -1); Prolog's // truncates toward zero
eval(op(div, [A, B]), S0, S, V) :- pnf_lang(python), \+ ( A = lit(_), B = lit(_) ), !,
    eval(A, S0, S1, AV), eval(B, S1, S, BV), eval(op(div, [lit(AV), lit(BV)]), S, _, V).
eval(op(div, [lit(A), lit(B)]), S, S, V) :- pnf_lang(python), integer(A), integer(B), !,
    ( B =:= 0 -> throw(pnf_error(div0)) ; V is A div B ).
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
% a[i:j:k] = ... with a step other than 1 (Python's extended slice store): the values go to the positions of
% range(i, j, k) as Python normalises them, one each; the other slice stores are interp.pl's
:- multifile store/4.
store(slice(Q, A, B, C), V, S0, S) :- C \== none, \+ C = lit(1),
    eval(C, S0, S1, CV), integer(CV), CV =\= 1, CV =\= 0, !,
    eval(Q, S1, S2, ref(R)), eval(A, S2, S3, AV), eval(B, S3, S4, BV),
    S4 = s(E, H0, N, T), get_assoc(R, H0, L0), length(L0, Len), elements(V, H0, New),
    step_positions(AV, BV, CV, Len, Ks),
    ( length(Ks, M), length(New, M) -> true ; throw(pnf_error(slice_length)) ),
    foldl([K, X, La, Lb]>>set_nth0(K, La, X, Lb), Ks, New, L0, L), put_assoc(R, H0, L, H), S = s(E, H, N, T).
step_positions(A, B, St, Len, Ks) :- St > 0, !,
    slice_end(A, Len, 0, 0, Len, I0), slice_end(B, Len, Len, 0, Len, I1), positions_up(I0, I1, St, Ks).
step_positions(A, B, St, Len, Ks) :- Hi is Len - 1,
    slice_end(A, Len, Hi, -1, Hi, I0), slice_end(B, Len, -1, -1, Hi, I1), positions_down(I0, I1, St, Ks).
slice_end(none, _, D, _, _, D) :- !.
slice_end(X, Len, _, Lo, Hi, I) :- integer(X), ( X < 0 -> Y is X + Len ; Y = X ), I is max(Lo, min(Hi, Y)).
positions_up(I, J, _, []) :- I >= J, !.
positions_up(I, J, St, [I|Ks]) :- I1 is I + St, positions_up(I1, J, St, Ks).
positions_down(I, J, _, []) :- I =< J, !.
positions_down(I, J, St, [I|Ks]) :- I1 is I + St, positions_down(I1, J, St, Ks).
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'interp_v03.pl', P), load_files(P, [if(not_loaded)]).
