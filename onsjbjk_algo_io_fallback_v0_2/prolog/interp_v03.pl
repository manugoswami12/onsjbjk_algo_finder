/* v0.3 interpreter of the Prolog normal form (doc 04 section 18.4), kept separate from the pipeline: AP13's
   interp.pl, extended without editing it. The clauses below are loaded before interp.pl's (eval/4 and builtin/5 are
   declared multifile), so they are tried first; each one applies only where interp.pl would throw.
     lambda(Ps, Body)          a closure: closure(Ps, Body, Env), the environment it was made in
     a call of a variable      bound to a closure, or to an own function's name (fun(Name)): the value is applied
     var(X) unbound            a module-level constant (pnf_const/2, from pnf_v03.py), or an own function as a value
     map / filter / reduce     over closures and function values
     str / set / chain / zip / bisect_left / bisect_right / int(string)   their list relations
   The source never runs; only its normal form does (pnf_v03.py).
*/
:- multifile eval/4, builtin/5.
:- dynamic pnf_const/2.

eval(lambda(Ps, B), S, S, closure(Ps, B, E)) :- !, S = s(E, _, _, _).
eval(var(X), S0, S, V) :- S0 = s(E, _, _, _), \+ get_assoc(X, E, _), global_value(X, S0, S, V), !.
eval(call(F, Args), S0, S, V) :- atom(F), S0 = s(E, _, _, _), get_assoc(F, E, C), applicable(C), !,
    foldl([A, X, Sa, Sb]>>eval(A, Sa, Sb, X), Args, Vs, S0, S1), apply_value(C, Vs, S1, S, V).

global_value(X, S0, S, V) :- pnf_const(X, Expr), !, eval(Expr, S0, S, V).
global_value(X, S, S, fun(X)) :- find_fun(X, _, _), !.
global_value(X, S, S, op_fun(O)) :- operator_function(X, O), !.   % operator.mul passed as a value
operator_function(mul, mul). operator_function(add, add). operator_function(sub, sub).
operator_function(truediv, fdiv). operator_function(floordiv, div). operator_function(mod, mod).

applicable(closure(_, _, _)).
applicable(fun(_)).
applicable(op_fun(_)).
% apply_value(+Value, +Args, S0, S, -Result): the caller's environment is kept
apply_value(closure(Ps, B, CE), Vs, s(E0, H0, N0, T0), s(E0, H, N, T), V) :- !,
    length(Ps, NP), length(Vs, NV), ( NP =:= NV -> true ; throw(pnf_error(arity(lambda, NP, NV))) ),
    bind_params(Ps, Vs, CE, E1), eval(B, s(E1, H0, N0, T0), s(_, H, N, T), V).
apply_value(fun(F), Vs, S0, S, V) :- !, call_fun(F, Vs, S0, S, V).
apply_value(op_fun(O), [A, B], S0, S, V) :- !, eval(op(O, [lit(A), lit(B)]), S0, S, V).

builtin(map, [C, Q], S0, S, R) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, L),
    foldl([X, Y, Sa, Sb]>>apply_value(C, [X], Sa, Sb, Y), L, Ys, S0, S1), new_list(Ys, S1, S, R).
builtin(filter, [C, Q], S0, S, R) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, L),
    foldl([X, K, Sa, Sb]>>(apply_value(C, [X], Sa, Sb, T), ( truthy(T, Sb) -> K = [X] ; K = [] )), L, Ks, S0, S1),
    append(Ks, Ys), new_list(Ys, S1, S, R).
builtin(reduce, [C, Q], S0, S, V) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, [X|L]),
    foldl([Y, A0, A, Sa, Sb]>>apply_value(C, [A0, Y], Sa, Sb, A), L, X, V, S0, S).
builtin(reduce, [C, Q, I], S0, S, V) :- applicable(C), !, S0 = s(_, H, _, _), elements(Q, H, L),
    foldl([Y, A0, A, Sa, Sb]>>apply_value(C, [A0, Y], Sa, Sb, A), L, I, V, S0, S).
builtin(str, [X], S0, S, R) :- number(X), !, ( integer(X) -> number_codes(X, Cs) ; format(codes(Cs), '~w', [X]) ),
    new_list(Cs, S0, S, R).
builtin(str, [ref(Q)], S0, S, R) :- !, S0 = s(_, H, _, _), get_assoc(Q, H, L), new_list(L, S0, S, R).
builtin(int, [ref(Q)], S, S, V) :- !, S = s(_, H, _, _), get_assoc(Q, H, Cs),
    ( catch(number_codes(V0, Cs), _, fail), integer(V0) -> V = V0 ; throw(pnf_error(raised)) ).
builtin(set, [Q], S0, S, R) :- !, S0 = s(_, H, _, _), elements(Q, H, L), list_to_set(L, L2), new_list(L2, S0, S, R).
builtin(set, [], S0, S, R) :- !, new_list([], S0, S, R).
builtin(chain, Qs, S0, S, R) :- !, S0 = s(_, H, _, _), foldl([Q, A0, A]>>(elements(Q, H, L), append(A0, L, A)), Qs, [], All),
    new_list(All, S0, S, R).
builtin(zip, [A, B], S0, S, R) :- !, S0 = s(_, H, _, _), elements(A, H, LA), elements(B, H, LB),
    zip_pairs(LA, LB, Ps), new_list(Ps, S0, S, R).
builtin(bisect_left, [Q, X], S, S, K) :- !, S = s(_, H, _, _), elements(Q, H, L), plain(X, H, PX),
    include([Y]>>(plain(Y, H, PY), compare_op(lt, PY, PX)), L, Lt), length(Lt, K).
builtin(bisect_right, [Q, X], S, S, K) :- !, S = s(_, H, _, _), elements(Q, H, L), plain(X, H, PX),
    include([Y]>>(plain(Y, H, PY), compare_op(le, PY, PX)), L, Le), length(Le, K).
builtin(bisect, Args, S0, S, K) :- !, builtin(bisect_right, Args, S0, S, K).
builtin(B, [Q, X, Lo, Hi], S, S, K) :- memberchk(B, [bisect_left, bisect_right]), !,   % within a[lo:hi]
    S = s(_, H, _, _), elements(Q, H, L), length(L, N), ( Hi == none -> Hi1 = N ; Hi1 = Hi ),
    findall(Y, ( between(Lo, Hi1, I), I < Hi1, nth0(I, L, Y) ), Part), new_list(Part, S, S1, R),
    builtin(B, [R, X], S1, _, K0), K is Lo + K0.
builtin(B, [Q, X, Lo], S0, S, K) :- memberchk(B, [bisect_left, bisect_right]), !, builtin(B, [Q, X, Lo, none], S0, S, K).

zip_pairs([X|Xs], [Y|Ys], [t([X, Y])|Ps]) :- !, zip_pairs(Xs, Ys, Ps).
zip_pairs(_, _, []).

:- prolog_load_context(directory, Dir), directory_file_path(Dir, '../../polyglot_logic/prolog/interp.pl', P),
   load_files(P, [if(not_loaded)]).
