/* v0.2 hand rules for TheAlgorithms/Python (doc 04 section 17): written where learning could not tell the algorithms
   at one tree node apart (the same behaviour, no shared write trace). Each is a relation over the language-neutral
   facts (AP13 exchange/4, loops, under/2, the v0.2 loop_step/2), the same in every language.
     hand_branch(Node, F, Label)   F at tree node Node is the algorithm Label
   All solutions are collected (findall in learn_apply.pl): no cut, no clause order. The family tree and its branches
   (families_v02.pl, family_to_v02.pl) are unchanged, so the earlier keys keep their answers.
*/
:- dynamic loop_step/2.
:- discontiguous hand_branch/3.

% the hand rules holding for a function at a node of it (the root [] for a function on no path); a file's answer is the hand labels of its functions that no
% function with a hand label of its own calls (a partition helper belongs to its quicksort; a helper called by a
% function the rules do not name answers for it)
hand_at(F, C, H) :- func(F, _, _), deepest_families_v02(F, Ps), ( Ps == [] -> C = [] ; member(C, Ps) ),
    hand_branch(C, F, H).
hand_answer(C, H) :- hand_at(F, C, H), func(F, Name, _), base_name(Name, B),
    \+ ( func(G, _, _), G \== F, in_func(S, G), call_at(S, B, _), part_of(G, C) ).
% the caller has a hand label of its own, or combines two functions of the same category of the tree that are not the
% same algorithm (an introsort: its heap sort, partition and insertion pass); a wrapper calling one sort, or a main
% calling two versions of one algorithm, is not
part_of(G, _) :- hand_at(G, _, _), !.
part_of(G, [Cat|_]) :- calls_in(G, Cat, H1), calls_in(G, Cat, H2), H1 \== H2,
    \+ ( hand_at(H1, _, L), hand_at(H2, _, L) ), !.
calls_in(G, Cat, H) :- in_func(S, G), call_at(S, B, _), func(H, N, _), H \== G, base_name(N, B),
    deepest_families_v02(H, Ps), member([Cat|_], Ps).

% ----- sequence_transformation > comparison_sort (> adjacent_exchange) -------------------------------------------
% the comparison sorts' node or a leaf below it: the relations below name the exchange themselves
sort_node(N) :- append([sequence_transformation, comparison_sort], _, N).
% an exchange of positions i and i + 1 of sequence Q (AP13 exchange/4 makes swap(i - 1, i) the same)
adjacent_exchange(F, S, Q) :- in_func(S, F), exchange(S, Q, I, J), J = op(add, [I1, int(1)]), I1 == I.
% the loops (and the recursion) around a statement; the innermost one
around(S, L) :- under(S, L), loop(L, _, _).
innermost(S, L) :- around(S, L), \+ ( around(S, L2), L2 \== L, under(L2, L) ).
stepping_two(L) :- loop_step(L, K), memberchk(K, [2, -2]).

% gnome: the exchange sits in one condition loop and nothing else: no outer pass, no recursion (the index walks back
% after a swap instead)
hand_branch(N, F, gnome_sort) :-
    sort_node(N), adjacent_exchange(F, S, _), findall(L, around(S, L), [L]), loop(L, F, cond), \+ called_elsewhere(F).
% another function of the file calls F inside a loop (in its body or its condition): F is a pass, not the whole sort
called_elsewhere(F) :- func(F, Name, _), base_name(Name, B), func(G, _, _), G \== F,
    ( in_func(C, G), call_at(C, B, _), around(C, _)
    ; loop(L, G, _), lcond(L, Cond), sub_term(T, Cond), compound(T), T = call(B, _) ), !.
% odd-even transposition: the exchanges' pass steps by two (the odd and the even positions in turn)
hand_branch(N, F, odd_even_sort) :-
    sort_node(N), adjacent_exchange(F, S, _), innermost(S, L), stepping_two(L).
% cocktail shaker: two different passes, each exchanging neighbours of the same sequence, inside one outer loop
hand_branch(N, F, cocktail_shaker_sort) :-
    sort_node(N), two_passes(F, L1, L2), \+ stepping_two(L1), \+ stepping_two(L2).
% ... or one pass whose positions come from the outer loop, which alternates the two directions
hand_branch(N, F, cocktail_shaker_sort) :-
    sort_node(N), adjacent_exchange(F, S, _), innermost(S, L), passes_vary(L).
two_passes(F, L1, L2) :-
    adjacent_exchange(F, S1, Q1), innermost(S1, L1), adjacent_exchange(F, S2, Q2), innermost(S2, L2),
    Q1 == Q2, L1 @< L2, \+ under(L1, L2), \+ under(L2, L1), around(L1, L0), around(L2, L0b), L0 == L0b.
% double sort: one pass exchanging two different neighbour pairs (from the front and from the back)
hand_branch(N, F, double_sort) :-
    sort_node(N), both_ends(F).
both_ends(F) :- adjacent_exchange(F, S1, Q1), in_func(S2, F), S2 \== S1, exchange(S2, Q2, _, _), Q1 == Q2,
    innermost(S1, L), innermost(S2, L2), L == L2.
% insertion by exchanges: the pass stops as soon as the neighbours are in order (the element comparison is the pass's
% own condition); a bubble pass only guards the exchange with it
hand_branch(N, F, insertion_sort) :-
    sort_node(N), adjacent_exchange(F, S, Q), innermost(S, L), stops_in_order(L, Q).
stops_in_order(L, var(Q)) :- lcond(L, C), compares_elements(C, Q).
% bubble: repeated passes of one neighbour exchange: its pass (stepping by one, running to its end, over the same
% positions each time) inside an outer loop or a recursion
hand_branch(N, F, bubble_sort) :-
    sort_node(N), adjacent_exchange(F, S, Q), innermost(S, L), around(L, _), \+ stepping_two(L),
    \+ stops_in_order(L, Q), \+ passes_vary(L), \+ two_passes(F, _, _), \+ both_ends(F).
% the pass iterates a value of an enclosing loop (the passes alternate their direction: a cocktail shaker)
passes_vary(L) :- loop_iter(L, var(V)), around(L, L0), lvar(L0, var(V2)), V == V2.

% ----- other comparison sorts (AP13's leaves below comparison_sort hold several algorithms each) -------------------
% selection: AP13's select_extreme (the scanned minimum exchanged into place), not a recursion
hand_branch([sequence_transformation, comparison_sort, select_extreme], F, selection_sort) :-
    self_calls(F, 0).                              % AP13 roles.pl: the number of self-calls
% insertion by shifting: AP13's shift idiom, and the function's only loops are the shift loop and the pass around it
hand_branch(N, F, insertion_sort) :-
    sort_node(N), idiom(F, shift, Q), \+ adjacent_exchange(F, _, _), in_func(S, F), value(S, elem(var(Q2), _), elem(var(Q3), _)), Q2 == Q, Q3 == Q,
    innermost(S, L), \+ ( loop(L2, F, K), K \== recursion, L2 \== L, \+ under(L, L2) ).
% shell: an element moved by a gap that is not one: q[j] = q[j - g] (insertion over gapped positions)
hand_branch(N, F, shell_sort) :-
    sort_node(N), in_func(S, F), value(S, elem(Q, J), elem(Q2, op(sub, [J2, G]))), Q2 == Q, J2 == J, G \= int(_),
    around(S, _).
% comb: an exchange of i and i + g while the gap g shrinks by a division (g = g / 1.3)
hand_branch(N, F, comb_sort) :-
    sort_node(N), in_func(S, F), exchange(S, _, I, J), gap_apart(F, I, J, G), shrinks(F, G).
% j = i + g, directly or through a local j assigned i + g
gap_apart(_, I, op(add, [I2, var(G)]), G) :- I2 == I.
gap_apart(F, I, var(Jv), G) :- in_func(S, F), assign(S, var(Jv2), op(add, [I2, var(G)])), Jv2 == Jv, I2 == I.
% ... or kept g apart by starting at i = 0, j = g and stepping both (C for (i = 0, j = gap; ...; i++, j++), Lisp)
gap_apart(F, var(Iv), var(Jv), G) :- in_func(S1, F), assign(S1, var(Iv2), int(0)), Iv2 == Iv,
    in_func(S2, F), assign(S2, var(Jv2), var(G)), Jv2 == Jv, G \== Iv.
% g is divided while it is updated: g / 1.3, g * 10 / 13, g / shrink
shrinks(F, G) :- in_func(S, F), ( assign(S, var(G2), E) ; value(S, var(G2), E) ), G2 == G,
    sub_term(D, E), compound(D), D = op(Div, [Num, _]), memberchk(Div, [div, fdiv]),
    sub_term(V, Num), V == var(G), !.
% stooge: three or more self-calls, two of them on the same arguments (the first two thirds sorted twice)
hand_branch(N, F, stooge_sort) :-
    sort_node(N), self_calls(F, K), K >= 3, repeated_call(F).
repeated_call(F) :- in_func(S1, F), call_at(S1, '$self', A1), in_func(S2, F), S2 @> S1, call_at(S2, '$self', A2),
    A1 =@= A2.
% slowsort: halves sorted recursively at a midpoint, then the range one shorter (the maximum moved to the end)
hand_branch(N, F, slowsort) :-
    sort_node(N), self_calls(F, K), K >= 3, in_func(S, F), call_at(S, '$self', As),
    member(op(sub, [var(E), int(1)]), As), param(F, _, E), \+ repeated_call(F).
% circle: an exchange of positions walking towards each other (one up, one down in the same loop), in halves
hand_branch(N, F, circle_sort) :-
    sort_node(N), mirrored_walk(F).
mirrored_walk(F) :- in_func(S, F), exchange(S, _, var(A), var(B)), A \== B, innermost(S, L),
    stepped_in(L, A, add), stepped_in(L, B, sub), self_calls(F, K), K >= 2, split_at_midpoint(F).
% the halves of a self-recursion meet at a midpoint m = (lo + hi) / 2: f(lo, m) and f(m + 1, hi)
split_at_midpoint(F) :- in_func(S, F), ( assign(S, var(M), E) ; value(S, var(M), E) ), halved(E),
    in_func(C, F), call_at(C, '$self', As), member(var(M2), As), M2 == M, !.
halved(E) :- sub_term(D, E), compound(D), D = op(Div, [_, int(2)]), memberchk(Div, [div, fdiv]), !.
halved(E) :- sub_term(D, E), compound(D), D = op(shr, [_, int(1)]), !.
stepped_in(L, X, O) :- in_func(S, _), under(S, L), ( assign(S, var(X2), op(O, [var(X3), int(1)])) ), X2 == X, X3 == X.
% quick: AP13's partition recursion (a split by a pivot, both parts sorted recursively), not the circle walk
hand_branch([sequence_transformation, comparison_sort, partition_recursive], F, quick_sort) :-
    \+ mirrored_walk(F), \+ repeated_call(F).
% ... or, however the parts are joined, two self-calls on the sequence filtered against one pivot, on the two sides
% of it (quicksort by filters: [x | x < p] and [x | x >= p])
hand_branch([sequence_transformation|_], F, quick_sort) :-
    in_func(S1, F), call_at(S1, '$self', [filter(Q1, C1)]), in_func(S2, F), call_at(S2, '$self', [filter(Q2, C2)]),
    Q1 == Q2, C1 = op(O1, [_, P1]), C2 = op(O2, [_, P2]), P1 == P2, sides(O1, O2).
sides(lt, ge). sides(lt, gt). sides(le, gt). sides(gt, le). sides(ge, lt). sides(gt, lt).
% heap: AP13's heap leaf (a sift over the children 2i + 1, 2i + 2)
hand_branch([sequence_transformation, comparison_sort, heap], _, heap_sort).

% ----- sequence_transformation > distribution_sort > histogram ----------------------------------------------------
% counting: the keys counted (AP13's histogram), then put back in key order, either the key itself written into the
% output by a loop over the keys that reads the count table at it (out[i] = k; out.append(k); out += [k] * count[k]),
% or each element placed at the position its key's prefix count gives (out[count[key(a[i])] - 1] = a[i])
hand_branch([sequence_transformation, distribution_sort, histogram], F, counting_sort) :-
    count_table(F, Tab), loop(L, F, _), lvar(L, var(K)), in_func(S, F), under(S, L), written_back(S, R, K),
    R \== Tab, reads_at(F, L, S, Tab, K).
hand_branch([sequence_transformation, distribution_sort, histogram], F, counting_sort) :-
    count_table(F, Tab), in_func(S, F), value(S, elem(R, Idx), elem(Q, _)), R \== Tab, Q \== Tab, R \== Q,
    sub_term(T, Idx), compound(T), T = elem(Tab2, _), Tab2 == Tab.
count_table(F, Tab) :- in_func(S, F), value(S, elem(Tab, _), op(add, [elem(Tab3, _), int(1)])), Tab3 == Tab.
% the key k as a value put into the output R
written_back(S, R, K) :- value(S, elem(R, _), E), key_value(E, K).
written_back(S, R, K) :- capp(S, R, E), key_value(E, K).
written_back(S, var(R), K) :- value(S, var(R2), op(add, [var(R3), X])), R2 == R3, R = R2,
    sub_term(list(Xs), X), member(E, Xs), key_value(E, K).
key_value(V, K) :- V == var(K).
key_value(op(add, [V, _]), K) :- V == var(K).
% the count table read at k in the write-back statement or its loop (count[k] > 0, range(count[k]))
reads_at(F, L, S, Tab, K) :- in_func(S2, F), ( S2 == S ; under(S2, L) ; S2 == L ), rel_of(S2, R0),
    sub_term(T, R0), compound(T), T = elem(Tab2, I), Tab2 == Tab, sub_term(V, I), V == var(K), !.
reads_at(_, L, _, Tab, K) :- ( lcond(L2, C) ; call_at(L2, _, C) ), ( L2 == L ; under(L2, L) ),
    sub_term(T, C), compound(T), T = elem(Tab2, I), Tab2 == Tab, sub_term(V, I), V == var(K), !.

% ----- numeric > recurrence ----------------------------------------------------------------------------------------
% factorial: the product of the counter itself, 1..n by ones (acc = acc * i), or n * f(n - 1); a double factorial
% steps by two
hand_branch([numeric, recurrence, range_accumulation], F, factorial) :-
    in_func(S, F), value(S, var(A), op(mul, [X, Y])), ( X == var(A), Y = var(I) ; Y == var(A), X = var(I) ),
    under(S, L), lvar(L, var(I2)), I2 == I, counts_numbers(L), \+ stepping_two(L).
% a counting loop: over range(...), over a range of numbers (Haskell [1..n], a fold over it), or a loop whose condition
% bounds its own variable (C for, Lisp loop for i from 2 to n)
counts_numbers(L) :- call_at(L, range, _), \+ loop_iter(L, _).
counts_numbers(L) :- loop_iter(L, call(range, _)).
counts_numbers(L) :- lvar(L, var(I)), lcond(L, C), sub_term(V, C), V == var(I), \+ loop_iter(L, _), !.
hand_branch([numeric, recurrence, range_accumulation], F, factorial) :-
    param(F, _, N), in_func(S, F), ( cret(S, op(mul, [X, Y])) ; ret(S, op(mul, [X, Y])) ),
    ( X == var(N), Y = call('$self', [op(sub, [V, int(1)])]) ; Y == var(N), X = call('$self', [op(sub, [V, int(1)])]) ),
    V == var(N).
% fibonacci: the pair (a, b) stepped to (b, a + b) from a start among 0 and 1 (Lucas starts at 2, 1; Pell and
% Jacobsthal double one term), or f(n - 1) + f(n - 2) with base values among 0, 1 and n
hand_branch([numeric, recurrence, pair_recurrence], F, fibonacci) :-
    in_func(S1, F), value(S1, var(A), var(B)), under(S1, L), in_func(S2, F), value(S2, var(B2), op(add, [X, Y])),
    B2 == B, under(S2, L2), L2 == L, msort([X, Y], XY), msort([var(A), var(B)], AB), XY == AB,
    \+ ( in_func(S0, F), \+ under(S0, _), value(S0, var(V0), int(K)), memberchk(V0, [A, B]), \+ memberchk(K, [0, 1]) ).
hand_branch([numeric, recurrence, double_recursion], F, fibonacci) :-
    self_minus_one_minus_two(F), \+ ( self_calls(F, K), K > 2 ), param(F, _, N),
    in_func(S, F), ( cret(S, op(add, [X, Y])) ; ret(S, op(add, [X, Y])) ), msort([X, Y], XY),
    msort([call('$self', [op(sub, [var(N), int(1)])]), call('$self', [op(sub, [var(N), int(2)])])], Want), XY == Want,
    \+ ( in_func(S2, F), ret(S2, int(K2)), \+ memberchk(K2, [0, 1]) ).
% gcd: Euclid's pair step {p := q, q := p mod q} (or the recursive gcd(q, p mod q)), no Bezout coefficients tracked
% (the extended algorithm also updates c := c' - quotient * c)
hand_branch([numeric|_], F, greatest_common_divisor) :-
    euclid_step(F), \+ coefficients(F).
euclid_step(F) :- in_func(S1, F), copied(F, S1, P, Q), P \== Q, in_func(S2, F), value(S2, var(V), op(mod, [A, B])),
    ( V == Q, A == var(P), B == var(Q) ; V == P, A == var(Q), B == var(P) ), !.
% p := q, directly or through one temporary (t = b; b = a % b; a = t)
copied(_, S, P, Q) :- value(S, var(P), var(Q)).
copied(F, S, P, Q) :- value(S, var(P), var(T)), in_func(S0, F), value(S0, var(T2), var(Q)), T2 == T, S0 \== S, Q \== P.
coefficients(F) :- in_func(S, F), value(S, _, op(sub, [_, op(mul, [var(_), var(_)])])), !.
% lcm: a * b over their gcd (a function of the file with the gcd rule, or the library gcd), or a multiple of the larger
% stepped by itself until the other divides it
hand_branch(_, F, least_common_multiple) :-
    param(F, _, A), param(F, _, B), A @< B, in_func(S, F), cret(S, E), sub_term(D, E), compound(D),
    D = op(div, _), sub_term(G, E), compound(G), G = call(Gn, [_, _]), gcd_name(Gn),
    sub_term(VA, E), VA == var(A), sub_term(VB, E), VB == var(B).
hand_branch(_, F, least_common_multiple) :-
    in_func(S, F), value(S, var(M), op(add, [var(M2), var(K)])), M2 == M, K \== M, under(S, L), lcond(L, C),
    sub_term(T, C), compound(T), T = op(mod, [V, _]), V == var(M).
gcd_name(gcd).
gcd_name(G) :- func(H, N, _), base_name(N, G), euclid_step(H), \+ coefficients(H).

% ----- primes --------------------------------------------------------------------------------------------------
% sieve of Eratosthenes: a constant mark written at m[j] while j steps by a stride (AP13's stride marking, also with
% the v0.2 loop_step of a C for) that is the variable (or AP13 stepper) of an enclosing loop reading the mark at it (if mark[p]: for j in range(p * p, n, p): mark[j] = False)
hand_branch(_, F, sieve_of_eratosthenes) :-
    in_func(S, F), value(S, elem(var(M), var(J)), V), V \= op(_, _), innermost(S, L),
    lvar(L, var(J2)), J2 == J, stride_of(L, P), around(L, L0), ( lvar(L0, var(P2)) ; role(F, stepper, P2) ), P2 == P,
    reads_mark(F, L0, M, P).
stride_of(L, P) :- call_at(L, R, [_, _, var(P)]), memberchk(R, [range, xrange, seq]).
stride_of(L, P) :- loop_step(L, var(P)).
stride_of(L, P) :- lvar(L, var(J)), in_func(S, _), under(S, L), value(S, var(J1), op(add, [var(J2), var(P)])),
    J1 == J, J2 == J, atom(P).
reads_mark(F, L0, M, P) :- in_func(S, F), ( under(S, L0) ; S == L0 ), ( nguard(S, C, _) ; lcond(S, C) ),
    sub_term(T, C), compound(T), T = elem(var(M2), var(P2)), M2 == M, P2 == P, !.
% trial division: n mod d == 0 for a stepping d guards a return of false; nothing divided out, nothing summed
hand_branch([numeric|_], F, prime_check) :-
    param(F, _, N), in_func(S, F), ret(S, R), falsy(R), nguard(S, C, _), sub_term(T, C), compound(T),
    T = op(mod, [var(N2), var(D)]), N2 == N, D \== N, role(F, stepper, D2), D2 == D,
    \+ ( in_func(S2, F), value(S2, var(N3), op(div, [var(N4), _])), N3 == N, N4 == N ),
    \+ ( in_func(S3, F), value(S3, var(A), op(add, [var(A2), var(D3)])), A == A2, D3 == D ).
falsy(bool(false)).
falsy(int(0)).
% perfect number: the divisors d of n (n mod d == 0) summed, the sum compared with n
hand_branch(_, F, perfect_number) :-
    param(F, _, N), in_func(S, F), value(S, var(A), op(add, [var(A2), X])), A == A2, nguard(S, C, _),
    sub_term(T, C), compound(T), T = op(mod, [var(N2), var(D)]), N2 == N, sub_term(VD, X), VD == var(D),
    in_func(S2, F), ( cret(S2, E) ; nguard(S2, E, _) ), sub_term(Q, E), compound(Q), Q = op(eq, Args),
    msort(Args, Sorted), msort([var(A), var(N)], Want), Sorted == Want.

% ----- digits --------------------------------------------------------------------------------------------------
% digit sum: acc += n mod b while n //= b (or the recursion n mod b + f(n // b))
hand_branch(_, F, sum_of_digits) :-
    in_func(S1, F), value(S1, var(A), op(add, [var(A2), op(mod, [var(N), B])])), A == A2,
    in_func(S2, F), value(S2, var(N2), op(div, [var(N3), B2])), N2 == N, N3 == N, B2 == B, A \== N.
hand_branch(_, F, sum_of_digits) :-
    in_func(S, F), cret(S, op(add, [X, Y])), ( X = op(mod, [var(N), B]), Y = call('$self', _)
                                             ; Y = op(mod, [var(N), B]), X = call('$self', _) ),
    in_func(S2, F), value(S2, var(N2), op(div, [var(N3), B2])), N2 == N, N3 == N, B2 == B.
% hailstone (Collatz): n halved when even, 3n + 1 when odd
hand_branch(_, F, collatz_sequence) :-
    in_func(S1, F), value(S1, var(N), E1), three_n_plus_one(E1, N),
    in_func(S2, F), value(S2, var(N2), op(div, [var(N3), int(2)])), N2 == N, N3 == N.
three_n_plus_one(op(add, [op(mul, [int(3), V]), int(1)]), N) :- V == var(N).
three_n_plus_one(op(add, [op(mul, [V, int(3)]), int(1)]), N) :- V == var(N).
% Luhn: every second digit doubled (and 9 taken off a two-digit double), the total divisible by 10
hand_branch(_, F, luhn) :-
    in_func(S1, F), value(S1, var(D2), op(mul, [_, int(2)])), in_func(S2, F), value(S2, var(D3), op(sub, [var(D4), int(9)])),
    D3 == D2, D4 == D2, in_func(S3, F), ( cret(S3, E) ; nguard(S3, E, _) ), sub_term(T, E), compound(T),
    T = op(eq, [op(mod, [_, int(10)]), int(0)]).

% ----- searching -----------------------------------------------------------------------------------------------
% binary search: the midpoint of lo and hi, the element there compared, lo moved past it or hi moved before it
hand_branch(_, F, binary_search) :-
    in_func(S, F), value(S, var(M), E), midpoint_of(E, Lo, Hi), Lo \== Hi,
    in_func(S1, F), value(S1, var(Lo2), op(add, [var(M2), int(1)])), Lo2 == Lo, M2 == M,
    in_func(S2, F), value(S2, var(Hi2), H), Hi2 == Hi, ( H = op(sub, [var(M3), int(1)]) ; H = var(M3) ), M3 == M,
    in_func(S3, F), ( nguard(S3, C, _) ; lcond(S3, C) ), at_mid(F, C, M),
    \+ ( in_func(Sw, F), value(Sw, elem(_, _), _) ).    % a search writes no element (binary insertion sort does)
% the element at the midpoint, directly or through a local (item = seq[mid])
at_mid(_, C, M) :- sub_term(T, C), compound(T), T = elem(_, var(M2)), M2 == M, !.
at_mid(F, C, M) :- in_func(S, F), value(S, var(X), elem(_, var(M2))), M2 == M, sub_term(V, C), V == var(X), !.
midpoint_of(E, Lo, Hi) :- halved(E), sub_term(A, E), A = var(Lo), sub_term(B, E), B = var(Hi), Lo @< Hi.
midpoint_of(E, Lo, Hi) :- halved(E), sub_term(A, E), A = var(Hi), sub_term(B, E), B = var(Lo), Hi @< Lo.

% ----- sequence predicates and merge sort ------------------------------------------------------------------------
% palindrome: the sequence compared with its mirror (AP13 mirror_compare: s[i] with s[n - 1 - i]) or with its reverse
% (s == s[::-1], s == reversed(s))
hand_branch(_, F, palindrome) :- idiom(F, mirror_compare, _).
hand_branch(_, F, palindrome) :-
    in_func(S, F), ( cret(S, E) ; nguard(S, E, _) ), sub_term(T, E), compound(T), T = op(Eq, [A, B]),
    memberchk(Eq, [eq, ne]), ( reversed_of(B, X), X == A ; reversed_of(A, X), X == B ).
reversed_of(call(slice, [X, other(none), other(none), int(-1)]), X).
reversed_of(call(R, [X]), X) :- memberchk(R, [reverse, reversed]).
reversed_of(call(join, [_, call(reversed, [X])]), X).
% merge sort: the two halves sorted by self-calls (split at a midpoint, by indexes or slices) and merged (AP13's merge:
% the smaller of two heads taken), in the function or in a merge function it calls
hand_branch(_, F, merge_sort) :-
    self_calls(F, 2), ( split_at_midpoint(F) ; sliced_halves(F) ), merges(F).
sliced_halves(F) :- in_func(S1, F), call_at(S1, '$self', A1), member(call(slice, [Q, other(none), var(M)]), A1),
    in_func(S2, F), call_at(S2, '$self', A2), member(call(slice, [Q2, var(M2), other(none)]), A2), Q2 == Q, M2 == M, !.
merges(F) :- idiom(F, merge, _), !.
merges(F) :- head_merge(F), !.
merges(F) :- in_func(S, F), call_at(S, B, _), func(G, N, _), G \== F, base_name(N, B), idiom(G, merge, _), !.
merges(F) :- in_func(S, F), call_at(S, merge, _), !.
merges(F) :- in_func(S, F), call_at(S, B, _), func(G, N, _), G \== F, base_name(N, B), head_merge(G), !.
% the head of one of two sequences moved to the result under a comparison of their heads (out.append(a.pop(0)))
head_merge(G) :- in_func(S, G), call_at(S, append, [_, call(pop, [var(A), _])]), nguard(S, C, _),
    sub_term(O, C), compound(O), O = op(Op, [P, Q]), memberchk(Op, [gt, ge, lt, le]),
    P = elem(var(A1), _), Q = elem(var(B1), _), A1 \== B1, ( A == A1 ; A == B1 ), !.
