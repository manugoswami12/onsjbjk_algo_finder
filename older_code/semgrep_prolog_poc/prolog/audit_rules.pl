/* AP8 conservative audit, additive to AP7 recognizers.
   A successful audit proves only the listed AST relationships, NOT Python
   behavioral equivalence or any mathematical sorting/hash property.
*/

/* A parallel swap must be a direct statement of the comparison's Then block.
   Keep the same array and index variables on both sides. */
direct_reverse_swap(Then, Sequence, IndexVar) :-
    direct_assignment(Then, Assign), assignment(Assign, Lhs, Rhs),
    ordered_two_accesses(Lhs, L0, L1),
    ordered_two_accesses(Rhs, R0, R1),
    array_index_expression(L0, Sequence, IX0), index_base(IX0, IndexVar),
    array_index_expression(L1, Sequence, IX1), index_plus_one(IX1, IndexVar),
    array_index_expression(R0, Sequence, IR0), index_plus_one(IR0, IndexVar),
    array_index_expression(R1, Sequence, IR1), index_base(IR1, IndexVar).

/* Bubble sort: require canonical Python-range bounds, direct comparison,
   direct swap and no abrupt exits anywhere inside the outer loop. */
audited_bubble(D, Outer, evidence(inner(Inner), array(A), index(J))) :-
    bubble_instance(D, Outer, evidence(inner(Inner), array(A), index(J))),
    function_definition(D, _, FunctionBody),
    direct_statement(FunctionBody, Outer),
    no_top_level_return_before(FunctionBody, Outer),
    canonical_bubble_bounds(Outer, Inner, A, J),
    for_block(Inner, Body),
    direct_if_parts(Body, _, Cond, Then),
    adjacent_greater(Cond, A, J),
    direct_reverse_swap(Then, A, J),
    no_abrupt_exit(Outer).

/* Hash update: require seed/return in top-level statements and the update
   directly in the inner for-block. A nested If False cannot be borrowed as an
   update. An unsupported guarded update remains UNVERIFIED, not ABSENT. */
audited_hash(D, Outer, Inner, Update, Evidence) :-
    rolling_hash_thread(D, Outer, Inner, Update, Evidence),
    Evidence = evidence(state(Accumulator), input(_, _), base(_), modulus(_),
                        seed(Seed), inner(Inner), return(Return)),
    function_definition(D, _, Body),
    direct_assignment(Body, Seed),
    direct_return(Body, Return),
    direct_statement(Body, Outer),
    no_top_level_return_before(Body, Outer),
    for_block(Inner, InnerBody),
    direct_assignment(InnerBody, Update),
    no_abrupt_exit(Outer),
    % The same state has already been checked across seed/update/return in AP7.
    nonvar(Accumulator).

/* Multi-thread audit: same definition, outer loop, inner loop, array, index.
   Both strands must independently pass their conservative checks. */
audited_interleaving(D, Bubble, Update,
                     evidence(shared_inner(Inner), array(A), index(J), accumulator(V))) :-
    audited_bubble(D, Bubble, evidence(inner(Inner), array(A), index(J))),
    audited_hash(D, Bubble, Inner, Update,
                 evidence(state(V), input(A, J), base(_), modulus(_),
                          seed(_), inner(Inner), return(_))).

/* A failed audit is NOT evidence that the algorithm is absent. */
audit_status(D, Name, bubble_sort, Region, audited_structural, Evidence) :-
    algorithm_instance_in(D, Name, bubble_sort, Region, Evidence),
    audited_bubble(D, Region, Evidence).
audit_status(D, Name, bubble_sort, Region, unverified, Evidence) :-
    algorithm_instance_in(D, Name, bubble_sort, Region, Evidence),
    \+ audited_bubble(D, Region, Evidence).
audit_status(D, Name, rolling_hash_update, Region, audited_structural, Evidence) :-
    thread_instance_in(D, Name, rolling_hash_update, Region, Evidence),
    audited_hash(D, _, _, Region, Evidence).
audit_status(D, Name, rolling_hash_update, Region, unverified, Evidence) :-
    thread_instance_in(D, Name, rolling_hash_update, Region, Evidence),
    \+ audited_hash(D, _, _, Region, Evidence).
audit_status(D, Name, binary_search, Region, legacy_candidate, Evidence) :-
    algorithm_instance_in(D, Name, binary_search, Region, Evidence).

/* Explain which AP8 audit obligation was not established. These predicates
   describe missing structural evidence, NEVER proof that the code is wrong. */
audit_blocker(D, bubble_sort, Outer, loop_bounds_not_established) :-
    bubble_instance(D, Outer, evidence(inner(Inner), array(A), index(J))),
    \+ canonical_bubble_bounds(Outer, Inner, A, J).
audit_blocker(D, bubble_sort, Outer, outer_not_direct_top_level) :-
    bubble_instance(D, Outer, _),
    function_definition(D, _, Body),
    \+ direct_statement(Body, Outer).
audit_blocker(D, bubble_sort, Outer, preceding_return) :-
    bubble_instance(D, Outer, _),
    function_definition(D, _, Body),
    \+ no_top_level_return_before(Body, Outer).
audit_blocker(D, bubble_sort, Outer, abrupt_exit_in_loop) :-
    bubble_instance(D, Outer, _),
    \+ no_abrupt_exit(Outer).
audit_blocker(D, bubble_sort, Outer, compare_swap_not_direct) :-
    bubble_instance(D, Outer, evidence(inner(Inner), array(A), index(J))),
    for_block(Inner, Body),
    \+ (direct_if_parts(Body, _, C, Then),
        adjacent_greater(C,A,J), direct_reverse_swap(Then,A,J)).

audit_blocker(D, rolling_hash_update, Update, update_not_direct_inner_statement) :-
    rolling_hash_thread(D, _, Inner, Update, _),
    for_block(Inner, InnerBody),
    \+ direct_assignment(InnerBody, Update).
audit_blocker(D, rolling_hash_update, Update, seed_not_direct) :-
    rolling_hash_thread(D, _, _, Update,
                        evidence(state(_),input(_,_),base(_),modulus(_),
                                 seed(Seed),inner(_),return(_))),
    function_definition(D, _, Body),
    \+ direct_assignment(Body, Seed).
audit_blocker(D, rolling_hash_update, Update, return_not_direct) :-
    rolling_hash_thread(D, _, _, Update,
                        evidence(state(_),input(_,_),base(_),modulus(_),
                                 seed(_),inner(_),return(Return))),
    function_definition(D, _, Body),
    \+ direct_return(Body, Return).
audit_blocker(D, rolling_hash_update, Update, preceding_return) :-
    rolling_hash_thread(D, Outer, _, Update, _),
    function_definition(D, _, Body),
    \+ no_top_level_return_before(Body, Outer).
audit_blocker(D, rolling_hash_update, Update, abrupt_exit_in_loop) :-
    rolling_hash_thread(D, Outer, _, Update, _),
    \+ no_abrupt_exit(Outer).
