/* Tracing a returned value through the variable that holds a recursive call's result (doc 04 section 19).
   AP13's copy propagation (canon.pl resolve/4, inline/4) replaces only a variable with ONE definition, so a return of
   a variable defined twice was not traced to the recursive call it holds, and the tree read
       lesser = f(lesser); greater = f(greater); return lesser + equal + greater
       z = 1; if n > 1: z = n * f(n - 1); return z
   as a return of plain variables. The same code written directly (return f(l) + e + f(g); return 1 if ... else
   n * f(n - 1)) is read correctly. Two value-flow shapes are traced here, by line order and guards, the same in every
   language; nothing names an algorithm:
     A  the last definition D of v before the return S holds on every path to S (its guards are among S's) and v is
        not written in between (no append or element write): v in S's value is D's value;
   in both, v is read nowhere after its traced definition but in the return (otherwise its value is used for more
   than the result);
     B  v has two definitions, a default D0 that holds on every path to S, then D1 under one more guard C (polarity P):
        S becomes two returns, D1's value under C = P and D0's under the other polarity (as a conditional return is).
   Only values holding a recursive call ('$self') are traced, the fault found; a loop of kind recursion contains the
   whole function and is no barrier. The call's own facts (the call and its parameter updates) move with its value.
     trace_returns   rewrites the loaded facts (called by tree_main.pl tree_load/2 after its other normalisations)
*/
trace_returns :- trace_returns(8).
trace_returns(0) :- !.
trace_returns(N) :-                              % one variable per return per round, until nothing is left to trace
    (   once(( ret(S, R), stmt(S, F, _, _), tr_traced_var(F, S, R, V, Shape) ))
    ->  tr_rewrite(Shape, F, S, V), N1 is N - 1, trace_returns(N1)
    ;   true
    ).

% a variable of the returned value whose definitions have shape A or B
tr_traced_var(F, S, R, V, Shape) :-
    once(( tr_free_var(R, V), \+ param(F, _, V), \+ loop_var(_, V),
           tr_defs_before(F, S, V, Ds), Ds \== [],
           (   last(Ds, D), tr_guards_within(D, S), \+ tr_written_between(F, V, D, S), tr_value_of(D, E), tr_recursive(E),
               \+ tr_used_elsewhere(F, V, [D], S)
           ->  Shape = a(D, E)
           ;   Ds = [D0, D1], tr_guards_within(D0, S), tr_extra_guard(D1, S, C, P), \+ tr_written_between(F, V, D1, S),
               \+ tr_written_between(F, V, D0, D1), tr_value_of(D0, E0), tr_value_of(D1, E1), tr_recursive(E1),
               \+ tr_used_elsewhere(F, V, [D0, D1], S)
           ->  Shape = b(D0, E0, D1, E1, C, P)
           ) )).

% a variable of the returned value outside the arguments of a recursive call: in return f(lesser) + equal, the
% lesser passed to f is the value before the call, never the traced result
tr_free_var(var(V), V) :- atom(V).
tr_free_var(T, V) :- compound(T), T \= var(_), T \= call('$self', _), T =.. [_|As], member(A, As), tr_free_var(A, V).

% the assignments of var(V) in F before S, by line; none when V is also assigned in a tuple
tr_defs_before(F, S, V, Ds) :-
    stmt(S, F, _, LS), \+ ( par_assign(_, Ts, _), member(T, Ts), T == var(V) ),
    findall(L-D, ( assign(D, T, _), T == var(V), stmt(D, F, _, L), L < LS ), LDs), msort(LDs, Sorted),
    pairs_values(Sorted, Ds).
tr_value_of(D, E) :- assign(D, T, E), T = var(_), !.
% the traced value of v (from its first traced definition Ds on) is read by a statement other than the return S and
% those definitions (a test, another value, a call, another return): its value is then not only the returned one, and
% the call stays where it is (red_black_tree's black_height tests left != right after left = f(...)). A read before
% that definition (the appends that build lesser, f(lesser) itself) reads the earlier value, not the returned one.
tr_used_elsewhere(F, V, [D|Ds], S) :- stmt(D, F, _, LD), stmt(W, F, _, LW), LW > LD, W \== S, \+ memberchk(W, [D|Ds]),
    tr_reads(W, V), !.
tr_reads(W, V) :- ( guard(W, X, _) ; assign(W, _, X) ; call_at(W, _, X) ; ret(W, X) ; loop_cond(W, X) ; loop_iter(W, X) ),
    sub_term(T, X), T == var(V), !.
tr_recursive(E) :- sub_term(C, E), compound(C), C = call('$self', _), !.
% D's guards are among S's (D holds on every path that reaches S), and D is in no ordinary loop S is outside of
tr_guards_within(D, S) :- forall(guard(D, C, P), guard(S, C, P)), \+ tr_outside_loop(D, S).
tr_outside_loop(D, S) :- in_loop(D, L), loop(L, _, K), K \== recursion, \+ in_loop(S, L).
% D1 has S's guards and exactly one more
tr_extra_guard(D1, S, C, P) :- forall(guard(S, C0, P0), guard(D1, C0, P0)), \+ tr_outside_loop(D1, S),
    findall(C1-P1, ( guard(D1, C1, P1), \+ guard(S, C1, P1) ), [C-P]).
% V is appended to, or an element of it written, on a line from D (exclusive) to S (exclusive)
tr_written_between(F, V, D, S) :- stmt(D, F, _, LD), stmt(S, F, _, LS),
    ( call_at(W, append, [T|_]) ; assign(W, elem(T, _), _) ), T == var(V), stmt(W, F, _, LW), LW > LD, LW < LS, !.

tr_rewrite(a(D, E), F, S, V) :- retract(ret(S, R)), tr_replace(var(V), E, R, R1), assertz(ret(S, R1)),
    tr_move_call(F, D, S).
tr_rewrite(b(_, E0, D1, E1, C, P), F, S, V) :-
    retract(ret(S, R)), tr_replace(var(V), E1, R, R1), tr_replace(var(V), E0, R, R0), tr_move_call(F, D1, S),
    atom_concat(S, '_else', S2), stmt(S, F, Kind, L), assertz(stmt(S2, F, Kind, L)),
    forall(in_loop(S, Lp), assertz(in_loop(S2, Lp))), forall(guard(S, C0, P0), assertz(guard(S2, C0, P0))),
    forall(next_stmt(X, S), assertz(next_stmt(X, S2))),
    flip(P, Q), assertz(guard(S, C, P)), assertz(ret(S, R1)), assertz(guard(S2, C, Q)), assertz(ret(S2, R0)).

% AP13 represents a recursive call by facts on the statement that makes it: call_at(D, '$self', Args) and the
% parameter updates assign(D, var(P), Arg). The call now lives in the return S, so they move with it.
tr_move_call(F, D, S) :-
    forall(retract(call_at(D, '$self', A)), assertz(call_at(S, '$self', A))),
    forall(( param(F, _, P), retract(assign(D, var(P), X)) ), assertz(assign(S, var(P), X))).

tr_replace(Old, New, T0, T) :- T0 == Old, !, T = New.
tr_replace(_, _, T, T) :- \+ compound(T), !.
tr_replace(Old, New, T0, T) :- T0 =.. [Fn|As], maplist(tr_replace(Old, New), As, Bs), T =.. [Fn|Bs].
