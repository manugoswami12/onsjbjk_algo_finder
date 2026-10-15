/* AP3 candidate bubble-sort substructure detector.
   No filename or declared function name is used for recognition.
   Requires a Python-style nested 'For' loop, adjacent comparison, and
   parallel reverse swap in the *same* branch. The AST is not simplified.
*/

for_block(For, Body) :-
    ast_tag(For, 'For'),
    at(For, '2', Body), ast_tag(Body, 'Block').

% Require that the nested loop is within the outer loop's body.
nested_for(Outer, Inner, InnerBody) :-
    for_block(Outer, OuterBody),
    under(OuterBody, Inner),
    for_block(Inner, InnerBody),
    Outer \== Inner.

% Strict adjacency: a[j] > a[j+1], with stable name/index bindings.
adjacent_greater(Condition, Sequence, IndexVar) :-
    operator_call(Condition, 'Gt'),
    call_arg(Condition, '0', A),
    array_index_expression(A, Sequence, IndexA), index_base(IndexA, IndexVar),
    call_arg(Condition, '1', B),
    array_index_expression(B, Sequence, IndexB), index_plus_one(IndexB, IndexVar).

% Two *complete* indexed accesses, and no additional accesses, in the
% direct LHS or RHS subtree. Preorder node IDs from exporter preserve left-to-
% right ordering for AST nodes. Ordered keysort makes that relation explicit.
ordered_two_accesses(Root, AccessA, AccessB) :-
    findall(Node, (under(Root, Node), ast_tag(Node, 'ArrayAccess')), Unordered),
    sort(Unordered, [AccessA, AccessB]).

% Python parallel assignment: a[j], a[j+1] = a[j+1], a[j].
% Both sides must access exactly the same sequence and reverse index order.
reverse_adjacent_swap(ThenBody, Sequence, IndexVar) :-
    under(ThenBody, Assignment),
    assignment(Assignment, Lhs, Rhs),
    ordered_two_accesses(Lhs, L0, L1),
    ordered_two_accesses(Rhs, R0, R1),
    array_index_expression(L0, Sequence, Left0),
    index_base(Left0, IndexVar),
    array_index_expression(L1, Sequence, Left1),
    index_plus_one(Left1, IndexVar),
    array_index_expression(R0, Sequence, Right0),
    index_plus_one(Right0, IndexVar),
    array_index_expression(R1, Sequence, Right1),
    index_base(Right1, IndexVar).

% Each bubble instance has its own outer root. The same indexed sequence and
% position must occur in comparison and swap. Does not assert sorted output.
bubble_instance(Definition, Outer,
                evidence(inner(Inner), array(Sequence), index(IndexVar))) :-
    function_definition(Definition, _, FunctionBody),
    under(FunctionBody, Outer),
    nested_for(Outer, Inner, InnerBody),
    under(InnerBody, If), if_parts(If, Condition, ThenBody),
    adjacent_greater(Condition, Sequence, IndexVar),
    reverse_adjacent_swap(ThenBody, Sequence, IndexVar),
    \+ (under(FunctionBody, NestedDef),
        ast_tag(NestedDef, 'DefStmt'), under(NestedDef, Outer)).
