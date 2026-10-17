/* v0.2 branch rules over the AP13 language-neutral relations (value/3, nguard/3, exchange/4,
   under/2, loop/3); polyglot_logic is not changed. AP13 reaches comparison_sort only when an
   element-element comparison guards the write itself, and select_extreme only with m = j. A
   comparison of the sequence's values that decides WHICH POSITION is exchanged (through a holder:
   best = q[k]; idx = k; swap(q[i], q[idx])) had no branch, so the tree fell to the broad
   [sequence_transformation] instead of stopping at its parent comparison_sort.
*/
:- discontiguous family_path_v02/2.

% a value of sequence Q: one of its elements, or a variable that only ever holds its elements
seq_value(_, Q, T) :- T = elem(V, _), V == var(Q), !.
seq_value(F, Q, var(B)) :- atom(B), once(( in_func(S0, F), value(S0, var(B), _) )),
    forall(( in_func(S, F), value(S, var(B2), V) , B2 == B ), ( V = elem(Vq, _), Vq == var(Q) )).
compares_values(F, C, Q) :- sub_term(O, C), compound(O), O = op(Op, [A, B]), memberchk(Op, [gt, ge, lt, le]),
    seq_value(F, Q, A), seq_value(F, Q, B), !.
% the exchanged position var(K) is set under a comparison of Q's values
decided_position(F, Q, S, K, Sk) :-
    in_func(S, F), exchange(S, var(Q), _, J), J = var(K), atom(K),
    in_func(Sk, F), value(Sk, var(K2), _), K2 == K, nguard(Sk, C, _), compares_values(F, C, Q).

family_path_v02(F, [sequence_transformation, comparison_sort]) :- once(decided_position(F, _, _, _, _)).
% the deciding comparison scans in a loop that does not hold the exchange: select, then exchange
family_path_v02(F, [sequence_transformation, comparison_sort, select_extreme]) :-
    once(( decided_position(F, _, S, _, Sk), under(Sk, L), loop(L, F, Kind), Kind \== recursion, \+ under(S, L) )).

% deepest paths of AP13 family_path and these branches together (AP13 prefix_of_other/2 reused)
deepest_families_v02(F, Paths) :-
    findall(P, ( family_path(F, P) ; family_path_v02(F, P) ), Ps0), sort(Ps0, Ps),
    exclude(prefix_of_other(Ps), Ps, Paths).

% x, y := y, t with t := f(x, y) earlier in the same loop body: t's only definition inside the loop
% reaches the parallel assignment (reaching definitions; an initial t = nil outside the loop is
% killed every iteration), so y_{n+1} = f(x_n, y_n): the pair recurrence
loop_value(F, S, T, E) :-
    under(S, L), loop(L, F, Kind), Kind \== recursion, stmt(S, F, _, LS),
    findall(S2-E2, ( in_func(S2, F), value(S2, var(T2), E2), T2 == T, under(S2, L) ), [S2-E]),
    stmt(S2, F, _, L2), L2 < LS.
family_path_v02(F, [numeric, recurrence, pair_recurrence]) :-
    numeric(F),
    once(( in_func(S, F), value(S, var(X), var(Y)), X \== Y, value(S, var(Y), var(T)), loop_value(F, S, T, E),
           E = op(O, _), memberchk(O, [add, mul, sub]), var_in(E, X), var_in(E, Y) )).

% n := n div b (directly, or through t := n div b earlier in the same loop body) with n mod b used as
% data: positional digits in base b; b a constant > 1 or a variable the function never writes (a
% loop invariant, as for induction-variable strides). Learned from sum-digits-1 (base a parameter).
family_path_v02(F, [numeric, decomposition, digits]) :-
    numeric(F),
    once(( in_func(S, F), value(S, var(N), V),
           ( V = op(div, [var(N1), B]) ; V = var(T), loop_value(F, S, T, op(div, [var(N1), B])) ), N1 == N,
           invariant_base(F, B, N),
           in_func(S2, F), value(S2, _, R), sub_term(M, R), compound(M), M = op(mod, [V2, B2]), V2 == var(N), B2 == B )).
invariant_base(_, int(K), _) :- integer(K), K > 1.
invariant_base(F, var(B), N) :- atom(B), B \== N, \+ ( in_func(S, F), value(S, var(B2), _), B2 == B ).

% two self-calls whose results a function of the same file merges (merge evidence in the callee):
% merge sort with its merge helper. Learned from the book's merge-sort / merge-lists.
family_path_v02(F, [sequence_transformation, comparison_sort, merge]) :-
    self_calls(F, K), K >= 2,
    once(( in_func(S, F), ret(S, R), sub_term(C, R), compound(C), C = call(Gn, Args), atom(Gn), Gn \== '$self',
           func(G, N, _), G \== F, base_name(N, Gn), idiom(G, merge, _),
           member(A, Args), sub_term(Sf, A), compound(Sf), Sf = call('$self', _) )).

% bounded interval halving (AP12's bounded_indexed_interval_lookup with any comparison of the two
% bounds as the loop test, beg /= end included): mid = midpoint(lo, hi); lo = mid + 1 and hi = mid
% (or mid - 1) under comparisons of a[mid] with the target. Learned from the book's bin-search.
family_path_v02(F, [sequence_query, target_search, interval_halving]) :-
    once(( loop(Lp, F, _), lcond(Lp, op(O, [var(X), var(Y)])), memberchk(O, [gt, ge, ne]),
           ( Lo = Y, Hi = X ; Lo = X, Hi = Y ),
           midpoint_in(Lp, M, Lo, Hi, _),
           ( assign(Sg, var(Lo), op(add, [var(M), int(1)])) ; value(Sg, var(Lo), op(add, [var(M), int(1)])) ),
           under(Sg, Lp), param(F, _, A), param(F, _, T), A \== T,          % bound before mentions/2 (it tests ==)
           nguard(Sg, C1, _), mentions(C1, elem(var(A), var(M))), mentions(C1, var(T)),
           ( assign(Ss, var(Hi), var(M)) ; assign(Ss, var(Hi), op(sub, [var(M), int(1)])) ),   % raw: mid is
           under(Ss, Lp), nguard(Ss, C2, _), mentions(C2, elem(var(A), var(M))) )).        % copy-propagated
% recursive halving of the sequence itself: the self-calls take slice(q, m) and slice(q, 0, m) with
% m = len(q) / 2, under a comparison of q's middle element with the target. Learned from the book's
% bin-search-v0.
family_path_v02(F, [sequence_query, target_search, interval_halving]) :-
    once(( param(F, _, Q), param(F, _, T), Q \== T,
           in_func(S1, F), call_at(S1, '$self', A1), member(H1, A1), H1 = call(slice, [var(Q1), var(M)]), Q1 == Q,
           in_func(S2, F), S2 \== S1, call_at(S2, '$self', A2), member(H2, A2),
           H2 = call(slice, [var(Q2), int(0), var(M2)]), Q2 == Q, M2 == M,
           in_func(Sm, F), value(Sm, var(M3), op(div, [call(len, [var(Q3)]), int(2)])), M3 == M, Q3 == Q,
           nguard(S1, C, _), mentions(C, var(T)), compared_element(F, C, Q) )).
compared_element(_, C, Q) :- sub_term(E, C), compound(E), E = elem(V, _), V == var(Q), !.
compared_element(F, C, Q) :- sub_term(W, C), compound(W), W = var(V), atom(V),
    in_func(S, F), value(S, var(V2), elem(var(Q2), _)), V2 == V, Q2 == Q, !.

% acc = acc op counter (product / sum over a range) where the update's only guards are its loop's own
% continuation condition (an accumulator recursion: f(n - 1, m * n) under n /= 0): every counter value is
% still taken. Learned from Rosetta factorial-3.
family_path_v02(F, [numeric, recurrence, range_accumulation]) :-
    numeric(F),
    once(( role(F, gatherer(O), X), memberchk(O, [mul, add]),
           in_func(S, F), value(S, var(X2), op(O, Args)), X2 == X, member(var(I), Args), I \== X,
           role(F, stepper, I), guard(S, _, _),
           forall(guard(S, C, P), continuation_guard(F, S, C, P)) )).
continuation_guard(F, S, C, P) :- under(S, L), loop(L, F, _), loop_cond(L, LC),
    ( P == true, LC == C ; P == false, LC == op(not, [C]) ), !.

% two recursive calls where the compiler made the second (a tail call) a jump to the function's start
% (ECL: tail_loop, ecl_norm.pl): a self-call inside that loop is the first call, the jump the second.
% The same logic as AP13's rec_class(double_recursion) (hanoi: f(n-1); move; f(n-1)), a second clause.
family_path_v02(F, [numeric, recurrence, double_recursion]) :-
    tail_loop(L), loop(L, F, _), once(( in_func(S, F), call_at(S, '$self', _), in_loop(S, L) )).

% ===== built branches (doc 04 section 15): where the Python examples cannot teach an algorithm in another
% language, its logic is stated here as relations over the facts, the same in every language. Each names
% the case it was built from and has a logic test on own programs (tests/test_uniform.py). =================

% Ackermann: nested recursion that counts the first argument down: f(m - 1, f(m, n - 1)). In Lisp ECL makes
% the outer call a jump to the start (tail_loop) whose update of a parameter is the inner call and another
% parameter's update is p - 1. Built from ackermann-function-4.c's task (the Rosetta Lisp/Python forms).
family_path_v02(F, [numeric, recurrence, nested_recursion]) :-
    once(( param(F, _, M),
           (   in_func(S, F), ( value(S, _, V) ; ret(S, V) ; call_at(S, '$self', As), V = call('$self', As) ),
               sub_term(O, V), compound(O), O = call('$self', Os), member(op(sub, [P, int(1)]), Os), P == var(M),
               member(A, Os), sub_term(I, A), compound(I), I = call('$self', _)
           ;   tail_loop(L), loop(L, F, _),
               in_func(S1, F), in_loop(S1, L), assign(S1, var(N), V1), param(F, _, N), N \== M,
               sub_term(I, V1), compound(I), I = call('$self', _),
               in_func(S2, F), in_loop(S2, L), assign(S2, var(M2), op(sub, [P2, int(1)])), M2 == M, P2 == var(M)
           ) )).

% 0-1 knapsack: a table cell T[i][j] taken from the previous row at a capacity reduced by a non-constant
% amount, T[i-1][j - w] (the item's weight); LCS and edit distance read T[i-1][j-1]. Built from
% knapsack-problem-0-1.c.
family_path_v02(F, [marking, table_fill, capacity_reduction]) :-
    once(( idiom(F, table_fill, T), in_func(S, F), value(S, elem(elem(var(T2), I), J), V), T2 == T,
           sub_term(R, V), compound(R), R = elem(elem(var(T3), op(sub, [I3, int(1)])), op(sub, [J3, W])),
           T3 == T, I3 == I, J3 == J, W \= int(_) )).

% Caesar shift: a character made from one input character's code taken modulo 26 around a base,
% chr((code(c) - b + k) mod 26 + b); a Vigenere shift is itself a character code (two in the mod). Built
% from caesar-cipher-2.lisp.
family_path_v02(F, [sequence_transformation, elementwise_map, alphabet_rotation]) :-
    once(( in_func(S, F), ( value(S, _, V) ; ret(S, V) ; call_at(S, _, V) ), sub_term(C, V), compound(C), C = call(chr, [E]),
           sub_term(Md, E), compound(Md), Md = op(mod, [X, int(26)]),
           findall(Q, ( sub_term(Q, X), char_code_of(F, Q) ), [_]) )).
char_code_of(_, call(ord, [A])) :- A \= other(string), A \= int(_), !.
char_code_of(F, var(V)) :- atom(V), in_func(S, F), value(S, var(V2), call(ord, [A])), V2 == V, A \= other(string), !.

% matrix product: the accumulated sum of a[r][k] * b[k][c] over k (b's column c: b[k][c], or a helper of
% the file that gives b's column, col(b, c)[k]), a and b parameters. Built from matrix-multiplication-1.lisp.
family_path_v02(F, [sequence_transformation, construction, matrix_product]) :-
    once(( in_func(S, F), value(S, T, op(add, [T2, op(mul, Fs)])), T2 == T,
           permutation(Fs, [X, Y]), X = elem(elem(var(A), var(R)), var(K)),
           (   Y = elem(elem(var(B), var(K2)), var(Cc))
           ;   Y = elem(call(G, [var(B), var(Cc)]), var(K2)), atom(G), func(_, G, _)
           ), K2 == K, param(F, _, A), param(F, _, B), R \== K, Cc \== K )).

% runs of equal elements: a group is extended by the next element while it equals the group's first,
% otherwise the group is emitted and a new group starts with the element (the run-length idiom of AP13's
% node, written by grouping). Built from run-length-encoding.lisp.
family_path_v02(F, [sequence_transformation, construction, run_length]) :-
    once(( in_func(S1, F), value(S1, var(G), cons(_, var(G2))), G2 == G,
           same_as_first(S1, G, true),
           in_func(S2, F), call_at(S2, append, [_, var(G3)]), G3 == G, same_as_first(S2, G, false),
           in_func(S3, F), value(S3, var(G4), list([_])), G4 == G, same_as_first(S3, G, false) )).
% statement S runs when (Pol = true) / unless (false) the element equals the first of group G
same_as_first(S, G, Pol) :-
    guard(S, C, P), ( C = op(not, [E]) -> flip(P, P1) ; E = C, P1 = P ),    % flip/2: AP13 canon.pl
    E = op(eq, Xs), member(elem(var(G2), int(0)), Xs), G2 == G, P1 == Pol, !.

% N-queens by generate and test: among the permutations of 0..n-1 (queen i in column x_i), keep those whose
% diagonals are distinct: the number of distinct values of x_i + i and x_i - i is n. Python counts them as
% len(set(x[i] + i ...)), Haskell as length . nub . zipWith f [0..] (a helper of the file). Built from
% n-queens-problem-3.hs.
family_path_v02(F, [search, permutation_filter]) :-
    once(( in_func(S, F), call_at(S, permutations, _), distinct_diagonals )).
distinct_diagonals :- in_func(S, _), ( value(S, _, V) ; ret(S, V) ; guard(S, V, _) ; cret(S, V) ),
    sub_term(D, V), compound(D), index_distinct(D), !.
index_distinct(call(len, [call(set, [op(O, [elem(var(Q), var(I)), var(I2)])|_])])) :- memberchk(O, [add, sub]), I == I2, atom(Q).
index_distinct(op('.', [var(length), op('.', [var(nub), call(zipWith, [_, call(range, [int(0), _])])])])).
