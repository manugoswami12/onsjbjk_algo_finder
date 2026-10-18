/* v0.2 hand rules for TheAlgorithms/Python (doc 04 section 17): written where learning could not tell the algorithms
   at one tree node apart (the same behaviour, no shared write trace). Each is a relation over the language-neutral
   facts (AP13 exchange/4, loops, under/2, the v0.2 loop_step/2), the same in every language.
     hand_branch(Node, F, Label)   F at tree node Node is the algorithm Label
   All solutions are collected (findall in learn_apply.pl): no cut, no clause order. The family tree and its branches
   (families_v02.pl, family_to_v02.pl) are unchanged, so the earlier keys keep their answers.
*/
:- dynamic loop_step/2.
:- discontiguous hand_branch/3.

% the hand rules holding for a function at a node of it; a file's answer is the hand labels of its functions that no
% function with a hand label of its own calls (a partition helper belongs to its quicksort; a helper called by a
% function the rules do not name answers for it)
hand_at(F, C, H) :- func(F, _, _), deepest_families_v02(F, Ps), member(C, Ps), hand_branch(C, F, H).
hand_answer(C, H) :- hand_at(F, C, H), func(F, Name, _), base_name(Name, B),
    \+ ( func(G, _, _), G \== F, in_func(S, G), call_at(S, B, _), part_of(G, C) ).
% the caller has a hand label of its own, sits in the same category of the tree (a sort calling a sort pass), or
% combines two functions of that category (an introsort: its heap sort, partition and insertion pass)
part_of(G, _) :- hand_at(G, _, _), !.
part_of(G, [Cat|_]) :- deepest_families_v02(G, Ps), member([Cat|_], Ps), !.
part_of(G, [Cat|_]) :- calls_in(G, Cat, H1), calls_in(G, Cat, H2), H1 \== H2, !.
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
% heap: AP13's heap leaf (a sift over the children 2i + 1, 2i + 2)
hand_branch([sequence_transformation, comparison_sort, heap], _, heap_sort).
