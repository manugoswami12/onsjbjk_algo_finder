/* AP6 opt-in relational recognition of non-contiguous logic threads.
   Queries exact, unchanged Semgrep generic AST facts. No rewriting or learning.
   Requires a connected seeded-and-returned polynomial hash-update recurrence.
   The label rolling_hash_update is a structural CANDIDATE, not a proof.
*/

% A direct Block statement may itself be an event or contain it (ExprStmt/Assign).
% Event is often UNBOUND: =/2 must unify direct nodes; ==/2 never binds.
% This matters for Return nodes, which are direct Block children in Semgrep.
block_statement_holding(Block, Event, Statement) :-
    ast_tag(Block, 'Block'), value(Block, Statements),
    ast_tag(Statements, 'list'), child(Statements, _, Statement),
    ( Event = Statement ; under(Statement, Event) ).

% Structure: (accumulator * Base + sequence[index]) % Modulus.
% Variable identity is bound across both sides of the assignment by Prolog.
polynomial_recurrence(Assign, Accumulator, Sequence, Index, Base, Modulus) :-
    assignment(Assign, Left, Expression), identifier(Left, Accumulator),
    operator_call(Expression, 'Mod'),
    call_arg(Expression, '0', Sum), operator_call(Sum, 'Plus'),
    call_arg(Expression, '1', ModExpr), integer_literal(ModExpr, Modulus),
    call_arg(Sum, '0', Product), operator_call(Product, 'Mult'),
    call_arg(Sum, '1', Indexed),
    array_index_expression(Indexed, Sequence, IndexExpr),
    identifier(IndexExpr, Index),
    call_arg(Product, '0', AccExpr), identifier(AccExpr, Accumulator),
    call_arg(Product, '1', BaseExpr), integer_literal(BaseExpr, Base),
    Base > 1, Modulus > Base,
    dif(Accumulator, Sequence), dif(Accumulator, Index).

% Require a *real* seeded state thread and returning exactly that state.
% The seed and return are direct top-level statements surrounding the outer
% loop in the same function, not arbitrary evidence from another function.
state_seed_and_return(FunctionBody, OuterLoop, Accumulator, SeedAssignment, Return) :-
    block_statement_holding(FunctionBody, SeedAssignment, SeedStatement),
    assignment(SeedAssignment, SeedLeft, SeedRight),
    identifier(SeedLeft, Accumulator), integer_literal(SeedRight, 0),
    direct_block_order(SeedStatement, OuterLoop),
    block_statement_holding(FunctionBody, Return, ReturnStatement),
    return_identifier(Return, Accumulator),
    direct_block_order(OuterLoop, ReturnStatement),
    SeedStatement \== ReturnStatement.

% One full connection: seed -> loop -> update -> return.
rolling_hash_thread(Definition, Outer, Inner, Update,
                    evidence(state(Accumulator), input(Sequence, Index),
                             base(Base), modulus(Modulus),
                             seed(SeedAssignment), inner(Inner), return(Return))) :-
    function_definition(Definition, _, FunctionBody),
    block_statement_holding(FunctionBody, Outer, Outer),
    nested_for(Outer, Inner, InnerBody),
    under(InnerBody, Update),
    % Evidence may not be borrowed from a nested function with shadowed names.
    \+ (under(FunctionBody, NestedDef),
        ast_tag(NestedDef, 'DefStmt'), under(NestedDef, Update)),
    polynomial_recurrence(Update, Accumulator, Sequence, Index, Base, Modulus),
    state_seed_and_return(FunctionBody, Outer, Accumulator, SeedAssignment, Return),
    % Do not conflate a recurrence with an accumulator that is later reset
    % or independently overwritten. Conservative: exactly these two write sites.
    \+ (under(FunctionBody, OtherWrite),
        assignment(OtherWrite, OtherLeft, _),
        identifier(OtherLeft, Accumulator),
        OtherWrite \== SeedAssignment,
        OtherWrite \== Update).

% SWI-Prolog will enumerate more than one such thread if present.
rolling_hash_instance(Definition, Update, Evidence) :-
    rolling_hash_thread(Definition, _, _, Update, Evidence).

% Interleaved == same inner loop with the SAME indexed input, not merely two
% algorithms in the same function, or matches accidentally borrowed elsewhere.
interleaved_sort_hash(Definition, BubbleOuter, Update,
                      evidence(shared_inner(Inner), array(Sequence), index(Index),
                               accumulator(Accumulator))) :-
    bubble_instance(Definition, BubbleOuter,
                    evidence(inner(Inner), array(Sequence), index(Index))),
    rolling_hash_thread(Definition, BubbleOuter, Inner, Update,
                        evidence(state(Accumulator), input(Sequence, Index),
                                 base(_), modulus(_), seed(_), inner(Inner), return(_))).
