/* AP13 v3: roles of variables (Sajaniemi) and recurrence classes (chains of
   recurrences, LLVM ScalarEvolution) over the EXISTING canonical relations of
   canon.pl / slice.pl. Language-neutral: only value/3, cret/2, exchange/4,
   nguard/3, lcond/2, lvar/2, under/2 and the raw base facts are read.
   Nothing here redefines an existing predicate (doc 08).
*/
:- discontiguous role/3, rec_class/3, idiom/3, stride_loop/2.

% ----- helpers -------------------------------------------------------------------
in_func(S, F) :- stmt(S, F, _, _).
loop_of(F, L) :- loop(L, F, _).
in_some_loop(S) :- under(S, L), loop(L, _, _), !.
seq_param(F, Q) :- param(F, _, Q), seq_param_direct(F, Q), !.
seq_param(F, Q) :- param(F, _, Q),                 % passed on to a local function that uses it so (SDG)
    stmt(S, F, _, _), call_at(S, Gn, Args), nth0(K, Args, V), V == var(Q),
    func(G, N, _), G \== F, base_name(N, Gn), param(G, K, P), seq_param_direct(G, P), !.
seq_param_direct(F, Q) :-
    once(( stmt(S, F, _, _), rel_of(S, R), sub_term(E, R), compound(E), seq_use(E, V), V == var(Q)
         ; loop(L, F, _), loop_iter(L, V), V == var(Q) )).
% elem(q, i), tail(q, k) (x:xs, xs[1:]), filter/map over q, len(q)
seq_use(elem(V, _), V).
seq_use(tail(V, _), V).
seq_use(filter(V, _), V).
seq_use(map(V, _, _), V).
seq_use(call(len, [V]), V).
rel_of(S, R) :- ( value(S, T, V), R = T-V ; cret(S, R) ; nguard(S, R, _) ; capp(S, _, R)
                ; exchange(S, Q, I, J), R = elem(Q, I)-elem(Q, J) ; under(S, L), lcond(L, R) ).
mentions_term(T, X) :- sub_term(Y, T), Y == X, !.
var_in(T, X) :- sub_term(V, T), compound(V), V = var(X), atom(X).
self_count(T, N) :- findall(x, ( sub_term(C, T), compound(C), C = call('$self', _) ), L), length(L, N).

% ----- roles of variables ------------------------------------------------------------
% organizer: a sequence whose elements are rearranged or rewritten
role(F, organizer, Q) :- in_func(S, F), exchange(S, var(Q), _, _).
role(F, organizer, Q) :- in_func(S, F), value(S, elem(var(Q), _), _), param(F, _, Q).

% stepper: a loop variable, or x = x +/- constant inside a loop
role(F, stepper, X) :- loop_of(F, L), lvar(L, var(X)).
role(F, stepper, X) :- in_func(S, F), in_some_loop(S), value(S, var(X), E), counter(X, E).

% gatherer: x = x (op) e, e not constant, inside a loop or recursion (sum, product, digits)
role(F, gatherer(O), X) :-
    in_func(S, F), in_some_loop(S), value(S, var(X), op(O, [A, B])), memberchk(O, [add, mul, sub, or, xor]),
    ( A == var(X), B \= int(_) ; B == var(X), A \= int(_) ).

% most-wanted holder: x = e only when e beats x (max/min, or the index of the best element)
role(F, most_wanted, X) :-
    in_func(S, F), in_some_loop(S), value(S, var(X), E), E \= int(_),
    nguard(S, op(O, [P, Q]), true), memberchk(O, [gt, ge]),
    beats(P, Q, E, X).
beats(P, Q, E, X) :- ( P == E ; P = elem(_, I), I == E ), ( Q == var(X) ; Q = elem(_, J), J == var(X) ).
beats(P, Q, E, X) :- ( Q == E ; Q = elem(_, I), I == E ), ( P == var(X) ; P = elem(_, J), J == var(X) ).

% follower: x takes the previous value of y, which is itself updated in the same loop
role(F, follower(Y), X) :-
    in_func(S, F), value(S, var(X), var(Y)), X \== Y, under(S, L), loop(L, F, _),
    in_func(S2, F), S2 \== S, value(S2, var(Y), _), under(S2, L).

% ----- recurrence classes (chains of recurrences) ------------------------------------
% the value of Y after following one temporary (t = a + b; b = t)
value_through(F, Y, E) :- in_func(S, F), value(S, var(Y), E0),
    ( E0 = var(T), in_func(S2, F), value(S2, var(T), E1), E1 \= var(_) -> E = E1 ; E = E0 ).

% x_{n+1} = y_n, y_{n+1} = f(x_n, y_n): Fibonacci-like pair recurrence
rec_class(F, pair, X-Y) :-
    role(F, follower(Y), X), value_through(F, Y, E), var_in(E, X), var_in(E, Y2), Y2 == Y,
    E = op(O, _), memberchk(O, [add, mul, sub]).
rec_class(F, pair, X-Y) :-                       % Haskell/Prolog style: f(b, a + b)
    in_func(S, F), value(S, var(X), var(Y)), X \== Y, value(S, var(Y), E),
    var_in(E, X), E = op(O, _), memberchk(O, [add, mul, sub]).
% x_{n+1} = y_n, y_{n+1} = x_n mod y_n: Euclid
rec_class(F, modulo, X-Y) :-
    ( role(F, follower(Y), X) ; in_func(S, F), value(S, var(X), var(Y)), X \== Y ),
    value_through(F, Y, E), sub_term(M, E), compound(M), M = op(mod, [A, B]),
    ( var_in(A, X) ; var_in(B, X) ).
% acc = acc (op) counter: product / sum over a range (factorial-like)
rec_class(F, range_accumulation, X) :-               % unconditional: every counter value is taken
    role(F, gatherer(O), X), memberchk(O, [mul, add]),
    in_func(S, F), value(S, var(X), op(O, Args)), member(var(I), Args), I \== X,
    role(F, stepper, I), \+ nguard(S, _, _).
rec_class(F, range_accumulation, N) :-           % n * f(n - 1), n + f(n - 1)
    in_func(S, F), cret(S, op(O, Args)), memberchk(O, [mul, add]), self_count(Args, 1),
    member(var(N), Args), param(F, _, N), value(S, var(N), E), counter(N, E).
% n = n div b with n mod b used: positional digits
rec_class(F, digits, N) :-
    in_func(S, F), value(S, var(N), op(div, [var(N1), int(B)])), N1 == N, B > 1,
    in_func(S2, F), value(S2, _, R), sub_term(M, R), compound(M),     % the remainder is DATA,
    M = op(mod, [V, int(B2)]), V == var(N), B2 == B.                   % not only a test (Collatz)
% n = f(n) under one test, n = g(n) under the opposite test (Collatz)
rec_class(F, conditional, N) :-                     % one branch multiplicative (n/2, 3n+1)
    in_func(S1, F), value(S1, var(N), E1), var_in(E1, N), \+ counter(N, E1),
    E1 = op(O1, _), memberchk(O1, [div, mul, add]), sub_term(Mx, E1), compound(Mx), Mx = op(Om, _),
    memberchk(Om, [div, mul]),
    in_func(S2, F), S2 \== S1, value(S2, var(N), E2), var_in(E2, N), \+ counter(N, E2), E1 \== E2,
    exclusive(S1, S2), in_some_loop(S1).
% n mod d == 0 tested while d steps: trial division
rec_class(F, divisor_test, N-D) :-
    in_func(S, F), rel_of(S, R), sub_term(M, R), compound(M), M = op(mod, [A, B]),
    A = var(N), B = var(D), role(F, stepper, D), N \== D.
rec_class(F, divisor_test, N-D) :-                % n % d for d in range(...)
    in_func(S, F), rel_of(S, R), sub_term(M, R), compound(M), M = op(mod, [A, B]),
    A = var(N), param(F, _, N), B = elem(call(Rg, _), var(D)), memberchk(Rg, [range, xrange, seq, seq_len]).
% two recursive calls in one result
rec_class(F, double_recursion, S) :- in_func(S, F), cret(S, V), self_count(V, K), K >= 2.
rec_class(F, double_recursion, F) :-               % hanoi: two recursive calls in ONE statement sequence
    in_func(S1, F), call_at(S1, '$self', _), in_func(S2, F), S2 \== S1, call_at(S2, '$self', _),
    follows(S1, S2), \+ exclusive(S1, S2), \+ exclusive(S2, S1), !.
follows(A, B) :- follows(A, B, [A]).
follows(A, B, _) :- next_stmt(A, B), !.
follows(A, B, Seen) :- next_stmt(A, C), \+ memberchk(C, Seen), follows(C, B, [C|Seen]), !.

% ----- sequence idioms (LoopIdiomRecognize; Ginsbach and O'Boyle reductions/histograms) --
% histogram: count[a[i]] += 1
idiom(F, histogram, C) :-
    in_func(S, F), value(S, elem(var(C), _), op(add, [elem(var(C2), K), int(_)])), C2 == C,
    sub_term(E, K), compound(E), E = elem(var(Q), _), param(F, _, Q).
% strided marking: m[j] = const while j steps by a variable stride
idiom(F, stride_marking, M) :-
    in_func(S, F), value(S, elem(var(M), var(J)), V), V \= op(_, _), \+ param(F, _, M),
    under(S, L), lvar(L, var(J)), stride_loop(L, J).
stride_loop(L, _) :- call_at(L, R, [_, _, var(_)]), memberchk(R, [range, xrange, seq]).
% a collection receives range(i*i, n + 1, i) for the loop variable i (marking a set)
idiom(F, stride_marking, C) :-
    in_func(S, F), call_at(S, _, [var(C)|Args]), \+ param(F, _, C),
    member(call(R, [_, _, var(P)]), Args), memberchk(R, [range, xrange, seq]),
    under(S, L), lvar(L, var(P2)), P2 == P.
stride_loop(L, J) :- in_func(S, _), under(S, L), value(S, var(J), op(add, [var(J1), var(P)])), J1 == J, atom(P).
% 2-D table filled from neighbouring cells (dynamic programming)
idiom(F, table_fill, T) :-
    in_func(S, F), value(S, elem(elem(var(T), _), _), E),
    sub_term(R, E), compound(R), R = elem(elem(var(T2), _), _), T2 == T.
% search: return the index whose element equals the target
idiom(F, index_return, I) :-
    in_func(S, F), cret(S, var(I)), in_some_loop(S),
    nguard(S, op(eq, [A, B]), true), ( A = elem(var(Q), V) ; B = elem(var(Q), V) ),
    V == var(I), param(F, _, Q).
% merge: comparing elements of two different sequences decides which one is taken next
idiom(F, merge, A-B) :-
    in_func(S, F), ( capp(S, _, X) ; cret(S, cons(X, _)) ; value(S, elem(_, _), X) ),
    compound(X), X = elem(var(A), _),
    ( nguard(S, C, _) ; under(S, L), lcond(L, C) ),
    sub_term(O, C), compound(O), O = op(Op, [P, Q]), memberchk(Op, [gt, ge, lt, le]),
    P = elem(var(A1), _), Q = elem(var(B1), _), A1 \== B1, ( A == A1 ; A == B1 ),
    ( A == A1 -> B = B1 ; B = A1 ), !.
% midpoint of two bounds inside the loop/recursion
idiom(F, midpoint, M) :- in_func(S, F), value(S, var(M), Mid), midpoint(Mid, _, _).
idiom(F, midpoint, M) :- in_func(S, F), cret(S, Mid), midpoint(Mid, _, _), M = '$ret'.
% a comparison of two elements of the same sequence controls a write of that sequence
idiom(F, compared_rewrite, Q) :-
    in_func(S, F), ( exchange(S, var(Q), _, _) ; value(S, elem(var(Q), _), _) ),
    ( nguard(S, C, _) ; under(S, L), lcond(L, C) ), compares_elements(C, Q).
compares_elements(C, Q) :- sub_term(O, C), compound(O), O = op(Op, [A, _]), memberchk(Op, [gt, ge, lt, le]),
    sub_term(E, O), compound(E), E = elem(V, _), V == var(Q), A \== none, !.
% shifting: q[i + 1] = q[i] (or q[i] = q[i - 1]) inside a condition loop
idiom(F, shift, Q) :-
    in_func(S, F), value(S, elem(var(Q), I), elem(var(Q2), J)), Q2 == Q,
    ( I = op(add, [J1, int(1)]), J1 == J ; J = op(sub, [I1, int(1)]), I1 == I ),
    under(S, L), loop(L, F, cond).
% recursive partition: result = f(part) ++ [pivot] ++ f(part)
idiom(F, partition, S) :-
    in_func(S, F), cret(S, concat(Ps)), self_count(Ps, K), K >= 2.
idiom(F, partition, S) :-                         % in place: a compared exchange in a loop + 2 recursive calls
    self_calls(F, K), K >= 2, partition_loop(F), S = F.
partition_loop(F) :- in_func(S3, F), exchange(S3, Q, _, _), idiom(F, compared_rewrite, Q0), var(Q0) == Q,
    under(S3, L), loop(L, F, K), K \== recursion, !.
partition_loop(F) :-                              % the loop lives in a local partition function
    in_func(C, F), call_at(C, Gn, _), Gn \== '$self', func(G, N, _), G \== F, base_name(N, Gn),
    in_func(S3, G), exchange(S3, _, _, _), under(S3, L), loop(L, G, K), K \== recursion, !.
self_calls(F, K) :- findall(S, ( in_func(S, F), call_at(S, '$self', _) ), Ss), length(Ss, K).
idiom(F, stooge, F) :- self_calls(F, K), K >= 3, in_func(S, F), exchange(S, _, _, _),
    \+ ( loop(L, F, Kd), Kd \== recursion, in_func(S2, F), under(S2, L) ).
% exchange shapes: i / i+1 (adjacent), i / i+g with a variable g (gap), i / 2i+1 (heap)
idiom(F, adjacent, Q) :- in_func(S, F), exchange(S, Q, I, J), J = op(add, [I1, int(1)]), I1 == I.
idiom(F, gap, Q) :- in_func(S, F), ( exchange(S, Q, I, J) ; value(S, elem(Q, J), elem(Q, I)) ),
    ( J = op(add, [I1, var(G)]) ; J = op(sub, [I1, var(G)]) ; I = op(sub, [I1, var(G)]), J1 = J, I1 = J1 ), I1 == I,
    atom(G), \+ ( loop(L, F, _), lvar(L, var(G2)), G2 == G ).
idiom(F, gap, Q) :- in_func(S, F), ( exchange(S, Q, I, J) ; value(S, elem(Q, I), elem(Q, J)) ),
    J = op(sub, [I1, var(G)]), I1 == I, atom(G), \+ ( loop(L, F, _), lvar(L, var(G2)), G2 == G ).
idiom(F, heap, Q) :- in_func(S, F), rel_of(S, R), sub_term(E, R), compound(E), E = elem(Q, I),
    heap_child(I).
heap_child(op(add, [op(mul, [int(2), _]), int(K)])) :- memberchk(K, [1, 2]).
heap_child(op(add, [op(mul, [_, int(2)]), int(K)])) :- memberchk(K, [1, 2]).
heap_child(op(add, [op(add, [V, V2]), int(K)])) :- V == V2, memberchk(K, [1, 2]).
