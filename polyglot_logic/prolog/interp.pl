/* AP13 v4 (doc 10): a definitional interpreter for the Prolog normal form (PNF).
   The SOURCE program is never executed; its Prolog translation runs here.

   State  s(Env, Heap, NextRef, Trace)
     Env    assoc: variable name -> value
     Heap   assoc: ref id -> list of values (sequences have reference semantics,
            so in-place sorts and helper functions mutate the same list)
     Trace  reversed list of logic events on the INPUT sequences:
            w(Param, Index, Value)   an element of input sequence Param was written
   Values: numbers, true/false, ref(Id), t([...]) (tuple), none
*/
:- use_module(library(assoc)).
:- use_module(library(lists)).
:- use_module(library(apply)).
:- dynamic pnf_fun/3, pnf_lang/1.
:- discontiguous eval/4, binop/5, builtin/5.

% ----- entry ------------------------------------------------------------------------
% run_fun(+Name, +ArgValues(plain Prolog: integers / lists), -Result, -FinalArgs, -Trace)
run_fun(Name, Args, Result, Finals, Trace) :-
    nb_setval(ap13_printed, []),
    empty_assoc(H0), alloc_args(Args, 1, H0, H1, Vals, Refs, N1),
    S0 = s(_, H1, N1, []), nb_setval(ap13_inputs, Refs),
    call_fun(Name, Vals, S0, S, Ret),
    S = s(_, H, _, T0), reverse(T0, Trace),
    plain(Ret, H, Result), maplist(final(H), Vals, Finals).

alloc_args([], N, H, H, [], [], N).
alloc_args([A|As], N, H0, H, [V|Vs], Refs, N2) :-
    (   is_list(A) -> V = ref(N), put_assoc(N, H0, A, H1), Refs = [N|Rs], N1 is N + 1
    ;   V = A, H1 = H0, Refs = Rs, N1 = N
    ),
    alloc_args(As, N1, H1, H, Vs, Rs, N2).

final(H, ref(R), L) :- !, plain(ref(R), H, L).
final(_, V, V).

plain(ref(R), H, L) :- !, get_assoc(R, H, L0), maplist([X, Y]>>plain(X, H, Y), L0, L).
plain(t(L0), H, t(L)) :- !, maplist([X, Y]>>plain(X, H, Y), L0, L).
plain(V, _, V).

% ----- functions ------------------------------------------------------------------------
call_fun(Name, Vals, s(Env0, H0, N0, T0), s(Env0, H, N, T), Ret) :-
    find_fun(Name, Params, Body),
    length(Params, NP), length(Vals, NV),
    ( NP =:= NV -> true ; throw(pnf_error(arity(Name, NP, NV))) ),
    empty_assoc(E0), bind_params(Params, Vals, E0, E1),
    exec(Body, s(E1, H0, N0, T0), s(_, H, N, T), Sig),
    ( Sig = return(Ret) -> true ; Ret = none ).

find_fun(Name, Ps, B) :- pnf_fun(Name, Ps, B), !.
find_fun(Name, Ps, B) :- pnf_fun(Full, Ps, B), short_name(Full, Name), !.
short_name(Full, Short) :- atomic_list_concat(Parts, '.', Full), last(Parts, Short).

bind_params([], [], E, E).
bind_params([P|Ps], [V|Vs], E0, E) :- put_assoc(P, E0, V, E1), bind_params(Ps, Vs, E1, E).

% ----- statements: exec(+Stmt, +S0, -S, -Signal) ------------------------------------------
exec(skip, S, S, normal) :- !.
exec(seq([]), S, S, normal) :- !.
exec(seq([X|Xs]), S0, S, Sig) :- !,
    exec(X, S0, S1, Sig1),
    ( Sig1 == normal -> exec(seq(Xs), S1, S, Sig) ; S = S1, Sig = Sig1 ).
exec(assign(T, E), S0, S, normal) :- !, eval(E, S0, S1, V), store(T, V, S1, S).
exec(par_assign(Ts, Es), S0, S, normal) :- !,
    foldl([E, V, Sa, Sb]>>eval(E, Sa, Sb, V), Es, Vs, S0, S1),
    foldl([T, V, Sa, Sb]>>store(T, V, Sa, Sb), Ts, Vs, S1, S).
exec(if(C, A, B), S0, S, Sig) :- !,
    eval(C, S0, S1, V), ( truthy(V, S1) -> exec(A, S1, S, Sig) ; exec(B, S1, S, Sig) ).
exec(while(C, B), S0, S, Sig) :- !,
    eval(C, S0, S1, V),
    (   truthy(V, S1)
    ->  exec(B, S1, S2, Sig1),
        (   Sig1 == break -> S = S2, Sig = normal
        ;   Sig1 = return(_) -> S = S2, Sig = Sig1
        ;   exec(while(C, B), S2, S, Sig)
        )
    ;   S = S1, Sig = normal
    ).
exec(c_for(I, C, U, B), S0, S, Sig) :- !,
    exec(I, S0, S1, _), for_loop(C, U, B, S1, S, Sig).
exec(for_range(X, Lo, Hi, St, B), S0, S, Sig) :- !,
    eval(Lo, S0, S1, L), eval(Hi, S1, S2, Hv), eval(St, S2, S3, Sv),
    ( Sv > 0 -> ( L < Hv -> numlist_step(L, Hv, Sv, Is) ; Is = [] )
    ; Sv < 0 -> ( L > Hv -> numlist_down(L, Hv, Sv, Is) ; Is = [] )
    ; throw(pnf_error(zero_step)) ),
    each(X, Is, B, S3, S, Sig).
exec(for_each(X, E, B), S0, S, Sig) :- !,
    eval(E, S0, S1, V), S1 = s(_, H, _, _), elements(V, H, Xs), each(X, Xs, B, S1, S, Sig).
exec(return(E), S0, S, return(V)) :- !, eval(E, S0, S, V).
exec(raise, _, _, _) :- !, throw(pnf_error(raised)).
exec(break, S, S, break) :- !.
exec(continue, S, S, continue) :- !.
exec(expr(E), S0, S, normal) :- !, eval(E, S0, S, _).
exec(X, _, _, _) :- throw(pnf_error(unsupported(X))).

for_loop(C, U, B, S0, S, Sig) :-
    eval(C, S0, S1, V),
    (   truthy(V, S1)
    ->  exec(B, S1, S2, Sig1),
        (   Sig1 == break -> S = S2, Sig = normal
        ;   Sig1 = return(_) -> S = S2, Sig = Sig1
        ;   exec(U, S2, S3, _), for_loop(C, U, B, S3, S, Sig)
        )
    ;   S = S1, Sig = normal
    ).

each(_, [], _, S, S, normal).
each(X, [I|Is], B, S0, S, Sig) :-
    ( atom(X) -> store(var(X), I, S0, S1) ; store(X, I, S0, S1) ), exec(B, S1, S2, Sig1),
    (   Sig1 == break -> S = S2, Sig = normal
    ;   Sig1 = return(_) -> S = S2, Sig = Sig1
    ;   each(X, Is, B, S2, S, Sig)
    ).

comp_items([], _, _, _, S, S, []).
comp_items([I|Is], X, C, V, S0, S, Out) :-
    ( atom(X) -> store(var(X), I, S0, S1) ; store(X, I, S0, S1) ), eval(C, S1, S2, CV),
    (   truthy(CV, S2) -> eval(V, S2, S3, VV), Out = [VV|Rest] ; S3 = S2, Out = Rest ),
    comp_items(Is, X, C, V, S3, S, Rest).

slice_list(L, N, A, B, C, Out) :-
    ( C == none -> St = 1 ; St = C ),
    ( St > 0 -> D0 = 0, D1 = N ; D0 is N - 1, D1 = -1 ),
    norm_ix(A, N, D0, I0), norm_ix(B, N, D1, I1),
    ( St > 0 -> ( I0 < I1 -> numlist_step(I0, I1, St, Ix) ; Ix = [] )
    ; ( I0 > I1 -> numlist_down(I0, I1, St, Ix) ; Ix = [] ) ),
    findall(V, ( member(K, Ix), K >= 0, K < N, nth0(K, L, V) ), Out).
norm_ix(none, _, D, D) :- !.
norm_ix(I, N, _, K) :- ( I < 0 -> K0 is N + I ; K0 = I ), K is max(-1, min(N, K0)).

numlist_step(L, H, St, []) :- L >= H, !, St > 0.
numlist_step(L, H, St, [L|Ls]) :- L1 is L + St, numlist_step(L1, H, St, Ls).
numlist_down(L, H, St, []) :- L =< H, !, St < 0.
numlist_down(L, H, St, [L|Ls]) :- L1 is L + St, numlist_down(L1, H, St, Ls).

truthy(V) :- V \== false, V \== 0, V \== none, V \== 0.0.
truthy(ref(R), s(_, H, _, _)) :- !, get_assoc(R, H, L), L \== [].
truthy(t(L), _) :- !, L \== [].
truthy(V, _) :- truthy(V).

% ----- stores --------------------------------------------------------------------------
store(var(X), V, s(E0, H, N, T), s(E, H, N, T)) :- !, put_assoc(X, E0, V, E).
store(elem(Q, I), V, S0, S) :- !,
    eval(Q, S0, S1, ref(R)), eval(I, S1, S2, Ix), S2 = s(E, H0, N, T0),
    get_assoc(R, H0, L0), index_of(Ix, L0, K), set_nth0(K, L0, V, L), put_assoc(R, H0, L, H),
    nb_getval(ap13_inputs, Ins),
    ( nth1(P, Ins, R) -> plain(V, H, PV), T = [w(P, K, PV)|T0] ; T = T0 ),
    S = s(E, H, N, T).
store(slice(Q, A, B, C), V, S0, S) :- !,                        % a[i:j] = ...
    eval(Q, S0, S1, ref(R)), eval(A, S1, S2, AV), eval(B, S2, S3, BV), eval(C, S3, S4, CV),
    S4 = s(E, H0, N, T), get_assoc(R, H0, L0), length(L0, Len), elements(V, H0, New),
    ( CV == none -> true ; CV =:= 1 -> true ; throw(pnf_error(extended_slice_store)) ),
    norm_ix(AV, Len, 0, I0), norm_ix(BV, Len, Len, I1), I0b is max(0, I0), I1b is max(I0b, I1),
    length(Pre, I0b), append(Pre, Rest, L0), Drop is I1b - I0b, length(Mid, Drop), append(Mid, Post, Rest),
    append([Pre, New, Post], L), put_assoc(R, H0, L, H), S = s(E, H, N, T).
store(tuple(Ts), t(Vs), S0, S) :- !, foldl([T, V, Sa, Sb]>>store(T, V, Sa, Sb), Ts, Vs, S0, S).
store(X, _, _, _) :- throw(pnf_error(bad_target(X))).

set_nth0(0, [_|T], V, [V|T]) :- !.
set_nth0(K, [X|T], V, [X|T2]) :- K1 is K - 1, set_nth0(K1, T, V, T2).
index_of(I, L, K) :- integer(I), length(L, N), ( I < 0 -> K is N + I ; K = I ), K >= 0, K < N, !.
index_of(I, _, _) :- throw(pnf_error(index(I))).

elements(ref(R), H, L) :- !, get_assoc(R, H, L).
elements(t(L), _, L) :- !.
elements(V, _, _) :- throw(pnf_error(not_iterable(V))).

new_list(L, s(E, H0, N, T), s(E, H, N1, T), ref(N)) :- put_assoc(N, H0, L, H), N1 is N + 1.

% ----- expressions: eval(+Expr, +S0, -S, -Value) -------------------------------------------
eval(lit(V), S, S, V) :- !.
eval(none, S, S, none) :- !.
eval(fn(N), S, S, fn(N)) :- !.
eval(callv(FE, Args), S0, S, V) :- !,                       % call through a function value (Lisp funcall)
    eval(FE, S0, S1, FV), foldl([E, X, Sa, Sb]>>eval(E, Sa, Sb, X), Args, Vs, S1, S2),
    (   FV = fn(N), lisp_op(N, O) -> Vs = [A, B], S2 = s(_, H, _, _), binop(O, A, B, H, V), S = S2
    ;   FV = fn(N), builtin(N, Vs, S2, S, V) -> true
    ;   FV = fn(N), find_fun(N, _, _) -> call_fun(N, Vs, S2, S, V)
    ;   throw(pnf_error(not_a_function(FV)))
    ).
eval(concat(Ps), S0, S, R) :- !,
    foldl([E, V, Sa, Sb]>>eval(E, Sa, Sb, V), Ps, Vs, S0, S1), S1 = s(_, H, _, _),
    foldl([V, A0, A]>>(elements(V, H, L), append(A0, L, A)), Vs, [], All), new_list(All, S1, S, R).
eval(num(N), S, S, N) :- !.
eval(str(A), S0, S, R) :- !, atom_codes(A, Cs), new_list(Cs, S0, S, R).
eval(comp(X, Seq, C, V), S0, S, R) :- !,
    eval(Seq, S0, S1, SV), S1 = s(E0, H, _, _), elements(SV, H, Xs),
    comp_items(Xs, X, C, V, S1, S2, Out), S2 = s(_, H2, N2, T2), new_list(Out, s(E0, H2, N2, T2), S, R).
eval(slice(Q, A, B, C), S0, S, R) :- !,
    eval(Q, S0, S1, QV), eval(A, S1, S2, AV), eval(B, S2, S3, BV), eval(C, S3, S4, CV),
    S4 = s(_, H, _, _), elements(QV, H, L), length(L, N), slice_list(L, N, AV, BV, CV, Out), new_list(Out, S4, S, R).
eval(int(N), S, S, N) :- !.
eval(bool(B), S, S, B) :- !.
eval(var(X), S, S, V) :- !, S = s(E, _, _, _),
    (   get_assoc(X, E, V) -> true
    ;   memberchk(X, [int, float, str, list, bool, tuple, dict, set, object]) -> V = type(X)
    ;   throw(pnf_error(unbound(X)))
    ).
eval(other(none), S, S, none) :- !.
eval(elem(Q, I), S0, S, V) :- !,                        % reads of INPUT positions are logic events
    eval(Q, S0, S1, QV), eval(I, S1, S2, Ix), S2 = s(E, H, N, T0), elements(QV, H, L),
    index_of(Ix, L, K), nth0(K, L, V),
    nb_getval(ap13_inputs, Ins),
    ( QV = ref(R), nth1(P, Ins, R) -> S = s(E, H, N, [r(P, K)|T0]) ; S = S2 ).
eval(list(Es), S0, S, R) :- !, foldl([E, V, Sa, Sb]>>eval(E, Sa, Sb, V), Es, Vs, S0, S1), new_list(Vs, S1, S, R).
eval(tuple(Es), S0, S, t(Vs)) :- !, foldl([E, V, Sa, Sb]>>eval(E, Sa, Sb, V), Es, Vs, S0, S).
eval(cond(C, A, B), S0, S, V) :- !, eval(C, S0, S1, CV), ( truthy(CV, S1) -> eval(A, S1, S, V) ; eval(B, S1, S, V) ).
eval(op(and, [A, B]), S0, S, V) :- !, eval(A, S0, S1, AV), ( truthy(AV, S1) -> eval(B, S1, S, V) ; S = S1, V = AV ).
eval(op(or, [A, B]), S0, S, V) :- !, eval(A, S0, S1, AV), ( truthy(AV, S1) -> S = S1, V = AV ; eval(B, S1, S, V) ).
eval(op(not, [A]), S0, S, V) :- !, eval(A, S0, S, AV), ( truthy(AV, S) -> V = false ; V = true ).
eval(op(neg, [A]), S0, S, V) :- !, eval(A, S0, S, AV), V is -AV.
eval(op(O, [A, B]), S0, S, V) :- !, eval(A, S0, S1, AV), eval(B, S1, S2, BV), S2 = s(_, H, _, _),
    (   memberchk(O, [add, mul]), ( AV = ref(_) ; BV = ref(_) )
    ->  list_op(O, AV, BV, H, L), new_list(L, S2, S, V)
    ;   S = S2, binop(O, AV, BV, H, V)
    ).
list_op(add, ref(A), ref(B), H, L) :- !, get_assoc(A, H, LA), get_assoc(B, H, LB), append(LA, LB, L).
list_op(mul, ref(A), K, H, L) :- integer(K), !, get_assoc(A, H, LA), repeat_list(LA, K, L).
list_op(mul, K, ref(A), H, L) :- integer(K), !, get_assoc(A, H, LA), repeat_list(LA, K, L).
list_op(O, _, _, _, _) :- throw(pnf_error(list_operator(O))).
repeat_list(_, K, []) :- K =< 0, !.
repeat_list(L, K, R) :- K1 is K - 1, repeat_list(L, K1, R1), append(L, R1, R).
eval(call(F0, Args0), S0, S, V) :- !,
    ( atom(F0), atom_concat('(', F1, F0), atom_concat(F, ')', F1) -> true ; F = F0 ),
    ( Args0 = [var(M)|Rest], module_name(M) -> Args = Rest ; Args = Args0 ),
    foldl([E, X, Sa, Sb]>>eval(E, Sa, Sb, X), Args, Vs, S0, S1),
    (   builtin(F, Vs, S1, S, V) -> true
    ;   find_fun(F, _, _) -> call_fun(F, Vs, S1, S, V)
    ;   throw(pnf_error(unknown_function(F)))
    ).
eval(X, _, _, _) :- throw(pnf_error(unsupported_expr(X))).

binop(add, A, B, H, V) :- number(A), number(B), !, V is A + B, H = H.
binop(mul, A, B, _, V) :- number(A), number(B), !, V is A * B.
binop(sub, A, B, _, V) :- !, V is A - B.
binop(div, A, B, _, V) :- !, ( B =:= 0 -> throw(pnf_error(div0)) ; V is A // B ).   % floor division in PNF
binop(fdiv, A, B, _, V) :- !, ( B =:= 0 -> throw(pnf_error(div0)) ; V is A / B ).
binop(mod, A, B, _, V) :- !, ( B =:= 0 -> throw(pnf_error(div0)) ; V is A mod B ).
binop(pow, A, B, _, V) :- !, V is A ** B.
binop(shr, A, B, _, V) :- !, V is A >> B.
binop(shl, A, B, _, V) :- !, V is A << B.
binop(xor, A, B, _, V) :- !, V is A xor B.
binop(is, A, B, H, V) :- !, binop(eq, A, B, H, V).
binop('is not', A, B, H, V) :- !, binop(ne, A, B, H, V).
binop(in, A, B, H, V) :- !, plain(A, H, PA), elements(B, H, L), ( member(X, L), plain(X, H, PA) -> V = true ; V = false ).
binop('not in', A, B, H, V) :- !, binop(in, A, B, H, V0), ( V0 == true -> V = false ; V = true ).
binop(add, t(A), t(B), _, t(C)) :- !, append(A, B, C).
binop(O, A, B, H, V) :- memberchk(O, [lt, le, gt, ge, eq, ne]), !,
    plain(A, H, PA), plain(B, H, PB), ( compare_op(O, PA, PB) -> V = true ; V = false ).
binop(O, _, _, _, _) :- throw(pnf_error(operator(O))).
compare_op(lt, A, B) :- ( number(A), number(B) -> A < B ; A @< B ).
compare_op(le, A, B) :- ( number(A), number(B) -> A =< B ; A @=< B ).
compare_op(gt, A, B) :- ( number(A), number(B) -> A > B ; A @> B ).
compare_op(ge, A, B) :- ( number(A), number(B) -> A >= B ; A @>= B ).
compare_op(eq, A, B) :- ( number(A), number(B) -> A =:= B ; A == B ).
compare_op(ne, A, B) :- \+ compare_op(eq, A, B).

% ----- library semantics (Python names; SYNONYMS already map other languages) ------------
builtin(len, [Q], S, S, N) :- !, S = s(_, H, _, _), elements(Q, H, L), length(L, N).
builtin(abs, [X], S, S, V) :- !, V is abs(X).
builtin(max, [A, B], S, S, V) :- number(A), !, V is max(A, B).
builtin(min, [A, B], S, S, V) :- number(A), !, V is min(A, B).
builtin(max, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), max_list(L, V).
builtin(min, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), min_list(L, V).
builtin(product, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), foldl([X, A0, A]>>(A is A0 * X), L, 1, V).
builtin(sum, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), sum_list(L, V).
builtin(gcd, [A, B], S, S, V) :- !, V is gcd(A, B).
builtin(sqrt, [X], S, S, V) :- !, V is sqrt(X).
builtin(int, [X], S, S, V) :- !, V is truncate(X).
builtin(floor, [X], S, S, V) :- !, V is floor(X).
builtin(pow, [A, B], S, S, V) :- !, V is A ** B.
builtin(range, Args, S0, S, R) :- !, range_list(Args, L), new_list(L, S0, S, R).
builtin(sorted, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L), msort(L, L2), new_list(L2, S0, S, R).
builtin(list, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L), new_list(L, S0, S, R).
builtin(reverse, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L), reverse(L, L2), new_list(L2, S0, S, R).
builtin(append, [ref(R), X], s(E, H0, N, T), s(E, H, N, T), none) :- !,
    get_assoc(R, H0, L0), append(L0, [X], L), put_assoc(R, H0, L, H).
builtin(pop, [ref(R)], s(E, H0, N, T), s(E, H, N, T), V) :- !,
    get_assoc(R, H0, L0), append(L, [V], L0), put_assoc(R, H0, L, H).
builtin(swap, [Q, I, J], S0, S, none) :- !,
    S0 = s(_, H, _, _), elements(Q, H, L), index_of(I, L, KI), index_of(J, L, KJ),
    nth0(KI, L, A), nth0(KJ, L, B),
    store(elem(lit(Q), int(KI)), B, S0, S1), store(elem(lit(Q), int(KJ)), A, S1, S).
builtin(P, Args, S, S, none) :- memberchk(P, [print, println, printf, puts, format, cat, putStrLn, 'print!', 'println!']), !,
    S = s(_, H, _, _), maplist([X, Y]>>plain(X, H, Y), Args, PA),
    nb_getval(ap13_printed, P0), nb_setval(ap13_printed, [PA|P0]).
builtin(isinstance, _, S, S, true) :- !.
builtin(reversed, [Q], S0, S, R) :- !, builtin(reverse, [Q], S0, S, R).
builtin(isqrt, [X], S, S, V) :- !, V is truncate(sqrt(X)).
builtin(ceil, [X], S, S, V) :- !, V is ceiling(X).
builtin(all, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), ( forall(member(X, L), truthy(X, S)) -> V = true ; V = false ).
builtin(any, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, L), ( member(X, L), truthy(X, S) -> V = true ; V = false ).
builtin(insert, [ref(R), I, X], s(E, H0, N, T), s(E, H, N, T), none) :- !,
    get_assoc(R, H0, L0), length(L0, Len), K is max(0, min(Len, I)), length(P, K), append(P, Suf, L0),
    append(P, [X|Suf], L), put_assoc(R, H0, L, H).
builtin(extend, [ref(R), Q], s(E, H0, N, T), s(E, H, N, T), none) :- !,
    elements(Q, H0, L1), get_assoc(R, H0, L0), append(L0, L1, L), put_assoc(R, H0, L, H).
builtin(randrange, _, S, S, 0) :- !.                     % deterministic stand-in: first position
builtin(randint, [A, _], S, S, A) :- !.
builtin(choice, [Q], S, S, V) :- !, S = s(_, H, _, _), elements(Q, H, [V|_]).
builtin(pop, [ref(R), I], s(E, H0, N, T), s(E, H, N, T), V) :- integer(I), !,
    get_assoc(R, H0, L0), index_of(I, L0, K), nth0(K, L0, V, L), put_assoc(R, H0, L, H).
builtin(index, [Q, X], S, S, K) :- !, S = s(_, H, _, _), elements(Q, H, L), plain(X, H, PX),
    ( nth0(K, L, Y), plain(Y, H, PY), PY == PX -> true ; throw(pnf_error(raised)) ).
builtin(enumerate, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L),
    findall(t([K, X]), nth0(K, L, X), Ps), new_list(Ps, S0, S, R).
builtin(float, [X], S, S, V) :- !, V is float(X).
builtin(round, [X], S, S, V) :- !, V is round(X).
builtin(divmod, [A, B], S, S, t([Q, M])) :- !, Q is A // B, M is A mod B.
builtin(ord, [ref(R)], S, S, C) :- !, S = s(_, H, _, _), get_assoc(R, H, [C]).
builtin(ord, [C], S, S, C) :- integer(C), !.
builtin(chr, [C], S0, S, R) :- !, new_list([C], S0, S, R).

range_list([Hi], L) :- !, range_list([0, Hi, 1], L).
range_list([Lo, Hi], L) :- !, range_list([Lo, Hi, 1], L).
range_list([Lo, Hi, St], L) :- ( St > 0 -> ( Lo < Hi -> numlist_step(Lo, Hi, St, L) ; L = [] )
                              ; ( Lo > Hi -> numlist_down(Lo, Hi, St, L) ; L = [] ) ).

module_name(M) :- memberchk(M, [math, random, np, numpy, statistics, functools, itertools, operator, cmath,
                                 string, sys, collections, heapq, bisect, 'Math']).

lisp_op('<', lt). lisp_op('>', gt). lisp_op('<=', le). lisp_op('>=', ge). lisp_op('=', eq).
lisp_op('+', add). lisp_op('-', sub). lisp_op('*', mul). lisp_op(eql, eq). lisp_op(equal, eq).
