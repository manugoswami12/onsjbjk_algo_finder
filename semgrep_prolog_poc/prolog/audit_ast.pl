/* AP8 generic AST predicates. Pure queries on the AP7 exact AST facts.
   No parser, AST rewriting, dynamic assertions, or extra dependencies.
*/

/* A direct statement is distinct from a nested statement under an If. */
direct_statement(Block, Statement) :-
    ast_tag(Block, 'Block'), value(Block, List), ast_tag(List, 'list'),
    child(List, _, Statement).

direct_assignment(Block, Assignment) :-
    direct_statement(Block, ExprStmt), ast_tag(ExprStmt, 'ExprStmt'),
    at(ExprStmt, '0', Assignment), assignment(Assignment, _, _).

direct_return(Block, Return) :-
    direct_statement(Block, Return), ast_tag(Return, 'Return').

/* `for Index in range(...)` with a single argument. Keep all bindings. */
for_each_range(For, Index, Argument) :-
    ast_tag(For, 'For'), at(For, '1', Each), ast_tag(Each, 'ForEach'),
    at(Each, '0', Pattern), ast_tag(Pattern, 'PatId'),
    at(Pattern, '0', PatternTuple), ast_tag(PatternTuple, 'list'),
    child(PatternTuple, '0', IndexScalar), ast_scalar(IndexScalar, Index),
    at(Each, '2', RangeCall), ast_tag(RangeCall, 'Call'),
    at(RangeCall, '0', RangeFunc), identifier(RangeFunc, range),
    call_arg(RangeCall, '0', Argument),
    \+ call_arg(RangeCall, '1', _).

/* `len(Array)` with a single argument. */
length_of(Expr, Array) :-
    ast_tag(Expr, 'Call'), at(Expr, '0', Fn), identifier(Fn, len),
    call_arg(Expr, '0', ArrExpr), identifier(ArrExpr, Array),
    \+ call_arg(Expr, '1', _).

/* Both loop bounds, including the decrement by the OUTER loop variable. */
canonical_bubble_bounds(Outer, Inner, Sequence, InnerIndex) :-
    for_each_range(Outer, OuterIndex, OuterBound),
    length_of(OuterBound, Sequence),
    for_each_range(Inner, InnerIndex, InnerBound),
    dif(OuterIndex, InnerIndex),
    operator_call(InnerBound, 'Minus'),
    call_arg(InnerBound, '0', Difference),
    call_arg(InnerBound, '1', One), integer_literal(One, 1),
    operator_call(Difference, 'Minus'),
    call_arg(Difference, '0', Length), length_of(Length, Sequence),
    call_arg(Difference, '1', OuterVar), identifier(OuterVar, OuterIndex).

/* Conservative structural flow gate: branches with any abrupt exit are not
   called audited. This does not imply complete control/dataflow analysis. */
abrupt_terminator(Node) :- ast_tag(Node, 'Break').
abrupt_terminator(Node) :- ast_tag(Node, 'Continue').
abrupt_terminator(Node) :- ast_tag(Node, 'Return').

no_abrupt_exit(Region) :-
    \+ (under(Region, N), abrupt_terminator(N)).

/* A direct If, not a search that borrows an If from a nested dead branch. */
direct_if_parts(Body, If, Cond, Then) :-
    direct_statement(Body, If), if_parts(If, Cond, Then).

/* A loop after an unconditional top-level return is syntactically dead. */
no_top_level_return_before(Body, Loop) :-
    \+ (direct_return(Body, PriorReturn), direct_block_order(PriorReturn, Loop)).
