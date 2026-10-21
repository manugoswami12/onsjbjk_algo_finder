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
% effect(Statement, Value): an expression with an effect (C's --n, n++, a = e, a, b; lowering_v05.py)
eval(effect(St, E), S0, S, V) :- !, exec(St, S0, S1, Sig), ( Sig == normal -> eval(E, S1, S, V) ; throw(pnf_error(effect_signal(Sig))) ).
% c_array(Init, Sizes): a C array of the given sizes (outermost first), its cells from the initializer, the rest 0;
% a size left out (int b[] = {...}) is the initializer's length; every row a fresh list (lowering_v05.py)
builtin(c_array, [Init, Sizes], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Sizes, H, Ns), c_fill(Init, Ns, S0, S, R).
c_fill(Init, [N], S0, S, R) :- !, S0 = s(_, H, _, _), c_items(Init, H, L), length(L, K),
    ( N == none -> Pad = 0 ; integer(N) -> Pad is max(0, N - K) ; throw(pnf_error(c_array_size(N))) ),
    length(Z, Pad), maplist(=(0), Z), append(L, Z, L1), new_list(L1, S0, S, R).
c_fill(Init, [N|Ns], S0, S, R) :- S0 = s(_, H, _, _), c_items(Init, H, Rows), length(Rows, K),
    ( N == none -> M = K ; integer(N) -> M = N ; throw(pnf_error(c_array_size(N))) ),
    c_rows(0, M, Rows, Ns, S0, S1, Refs), new_list(Refs, S1, S, R).
c_rows(I, M, _, _, S, S, []) :- I >= M, !.
c_rows(I, M, Rows, Ns, S0, S, [R|Rs]) :- ( nth0(I, Rows, Row) -> true ; Row = t([]) ),
    c_fill(Row, Ns, S0, S1, R), I1 is I + 1, c_rows(I1, M, Rows, Ns, S1, S, Rs).
c_items(t(L), _, L) :- !.
c_items(ref(R), H, L) :- !, get_assoc(R, H, L).
c_items(V, _, [V]).
% C's / divides two integers toward zero and anything with a float exactly; C's % keeps the dividend's sign (rem)
eval(op(O, [A, B]), S0, S, V) :- memberchk(O, [div, mod]), pnf_lang(c), \+ ( A = lit(_), B = lit(_) ), !,
    eval(A, S0, S1, AV), eval(B, S1, S, BV), eval(op(O, [lit(AV), lit(BV)]), S, _, V).
eval(op(div, [lit(A), lit(B)]), S, S, V) :- pnf_lang(c), number(A), number(B), ( float(A) ; float(B) ), !,
    ( B =:= 0 -> throw(pnf_error(div0)) ; V is A / B ).
eval(op(mod, [lit(A), lit(B)]), S, S, V) :- pnf_lang(c), integer(A), integer(B), !,
    ( B =:= 0 -> throw(pnf_error(div0)) ; V is A rem B ).
% Python library functions (doc 04 section 19.17), each only where the program defines no function of that name:
% bisect.insort/insort_left insert at bisect_right/bisect_left; enumerate(s, start); str predicates and case maps on
% a character code or a string (a list of codes); s.zfill(w) pads with 0 after a sign
own_function(F) :- pnf_fun(F, _, _).
builtin(F, [ref(R), X], S0, S, none) :- memberchk(F-B, [insort-bisect_right, insort_right-bisect_right,
        insort_left-bisect_left]), \+ own_function(F), !,
    builtin(B, [ref(R), X], S0, S1, K), builtin(insert, [ref(R), K, X], S1, S, _).
builtin(F, [ref(R), X, Lo, Hi], S0, S, none) :- memberchk(F-B, [insort-bisect_right, insort_right-bisect_right,
        insort_left-bisect_left]), \+ own_function(F), !,
    builtin(B, [ref(R), X, Lo, Hi], S0, S1, K), builtin(insert, [ref(R), K, X], S1, S, _).
builtin(enumerate, [Q, K0], S0, S, R) :- integer(K0), \+ own_function(enumerate), !, S0 = s(_, H, _, _), elements(Q, H, L),
    findall(t([K, X]), ( nth0(I, L, X), K is I + K0 ), Ps), new_list(Ps, S0, S, R).
builtin(F, [X], S, S, V) :- memberchk(F, [isalpha, isdigit, isupper, islower, isspace, isalnum]), \+ own_function(F), !,
    S = s(_, H, _, _), ( integer(X) -> Cs = [X] ; elements(X, H, Cs) ),
    ( Cs \== [], forall(member(C, Cs), str_class(F, C)) -> V = true ; V = false ).
str_class(isalpha, C) :- integer(C), code_type(C, alpha), \+ code_type(C, digit(_)), C =\= 0'_.
str_class(isdigit, C) :- integer(C), code_type(C, digit(_)).
str_class(isupper, C) :- integer(C), code_type(C, upper(_)).
str_class(islower, C) :- integer(C), code_type(C, lower(_)).
str_class(isspace, C) :- integer(C), code_type(C, space).
str_class(isalnum, C) :- str_class(isalpha, C) ; str_class(isdigit, C).
builtin(F, [X], S0, S, V) :- memberchk(F, [upper, lower]), \+ own_function(F), !, S0 = s(_, H, _, _),
    ( integer(X) -> case_code(F, X, V), S = S0 ; elements(X, H, Cs), maplist(case_code(F), Cs, Ds), new_list(Ds, S0, S, V) ).
case_code(F, C, D) :- integer(C), C >= 0, !, char_code(A, C), ( F == upper -> upcase_atom(A, B) ; downcase_atom(A, B) ),
    ( atom_length(B, 1) -> char_code(B, D) ; D = C ).
case_code(_, C, C).
builtin(zfill, [X, W], S0, S, V) :- integer(W), \+ own_function(zfill), !, S0 = s(_, H, _, _), elements(X, H, Cs),
    length(Cs, N), P is max(0, W - N), length(Z, P), maplist(=(0'0), Z),
    ( Cs = [Sg|Rest], memberchk(Sg, [0'+, 0'-]) -> append([Sg|Z], Rest, Ds) ; append(Z, Cs, Ds) ), new_list(Ds, S0, S, V).
% a call through a function value that is a closure or an own function (interp_v03 apply_value); interp.pl's callv
% applies only named functions
eval(callv(FE, Args), S0, S, V) :- eval(FE, S0, S1, FV), applicable(FV), !,
    foldl([E, X, Sa, Sb]>>eval(E, Sa, Sb, X), Args, Vs, S1, S2), apply_value(FV, Vs, S2, S, V).
% Haskell's digitToInt: '0'..'9', 'a'..'f' and 'A'..'F' to 0..15, anything else an error
builtin(digit_to_int, [C], S, S, V) :- !,
    ( integer(C), C >= 0'0, C =< 0'9 -> V is C - 0'0
    ; integer(C), C >= 0'a, C =< 0'f -> V is C - 0'a + 10
    ; integer(C), C >= 0'A, C =< 0'F -> V is C - 0'A + 10
    ; throw(pnf_error(digit_to_int(C))) ).
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
% x, y = s: Python unpacks any sequence of the same length, a list as well as a tuple
store(tuple(Ts), ref(R), S0, S) :- !, S0 = s(_, H, _, _), get_assoc(R, H, Vs),
    ( length(Ts, N), length(Vs, N) -> true ; throw(pnf_error(unpack_length)) ),
    foldl([T, V, Sa, Sb]>>store(T, V, Sa, Sb), Ts, Vs, S0, S).
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
