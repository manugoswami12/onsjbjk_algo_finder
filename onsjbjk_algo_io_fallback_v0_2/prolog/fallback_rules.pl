/* v0.2 fallback rules (doc 03 section 9): DCGs over the token stream of fallback_main.pl.
   One fallback_pattern(Branch, Rule)//0 clause per learned pattern; each states the case it was
   learned from. Add a learning: one clause here plus a logic test (tests/test_ecl_logic.py).
*/
:- discontiguous fallback_pattern//2.
... --> [] | [_], ... .

% (reduce #'+ (map 'vector #'* a b)): a fold of an arithmetic operator over an element-wise
% arithmetic map of two or more parameter sequences (fold/map fusion law): an aggregate over the
% elements. Learned from Rosetta dot-product-2.
fallback_pattern(element_accumulation, fold_map) -->
    [fold, op(F)], { memberchk(F, [add, mul]) }, [map, op(G)], { memberchk(G, [add, sub, mul]) },
    params(N), { N >= 2 }.
params(N) --> [param], params(N0), { N is N0 + 1 }.
params(0) --> [].

% (reduce #'insert list :initial-value nil) where insert returns left ++ (list x) ++ right and left is
% cut from the accumulator by an order comparison with x: a fold of an ordered insertion over the
% input = insertion sort. Learned from Rosetta insertion-sort-1.
fallback_pattern(shift_insertion, fold_ordered_insert) -->
    [fold, link(G), enter(G)], ordered_insert, [leave(G), param, init, empty].
ordered_insert --> ..., [append(3)], cut_by_comparison, [single], ... .
cut_by_comparison --> ..., [cmp(_)], ... .

% the position of the extreme of a prefix, then a linked function that reverses a prefix in place:
% select the extreme and flip it to its end (pancake sort, prefix reversal). Learned from Rosetta
% pancake-sort-1: (position (apply #'max (subseq lst 0 i)) lst), (flip lst k) = reverse (subseq lst 0 k).
fallback_pattern(comparison_driven_reordering, prefix_reversal) -->
    ..., [position, fold, op(E)], { memberchk(E, [max, min]) }, [subseq], ...,
    [link(G), enter(G)], ..., [reverse, subseq], ..., [leave(G)], ... .

% f(xs) = insert(first(xs), f(rest(xs))) where the linked insert compares, conses and recurses: the
% recursive insertion sort of a list. Learned from Rosetta insertion-sort-2.
fallback_pattern(shift_insertion, recursive_ordered_insert) -->
    ..., [link(G), enter(G)], ..., [cmp(_)], ..., [cons], ..., [call('$self')], ..., [leave(G)],
    ..., [call('$self')], ... .
