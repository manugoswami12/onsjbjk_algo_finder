/* Semgrep OCaml AST_generic JSON -> structural algorithm identification.
   This is a candidate recognizer, NOT a proof of algorithm equivalence.
   It reads only generic ast_tag/2, ast_edge/3, ast_scalar/2 facts.
   No Python AST parsing, filename-based labels, or hard-coded variable names.
*/
:- dynamic ast_tag/2, ast_edge/3, ast_scalar/2, ast_node_count/1.
% Old AP1 interleaved facts still load without warning; AP2 outputs grouped facts.
:- discontiguous ast_tag/2, ast_edge/3, ast_scalar/2, ast_node_count/1.

% ----- Generic JSON AST navigation (shared by every future algorithm rule) -----
child(Parent, Label, Child) :- ast_edge(Parent, Child, Label).
value(Node, Payload) :- child(Node, 'value', Payload).

% Semgrep JSON variants {"While": [ ... ]} become:
% ast_tag(While, 'While'), ast_edge(While, List, 'value'),
% ast_tag(List, 'list'), ast_edge(List, Element, '0'/'1'/...).
at(Variant, Index, Element) :-
    value(Variant, List), ast_tag(List, 'list'),
    child(List, Index, Element).

% Tree descent is deliberately restricted to a single while-loop body in
% the algorithm rule; a complete program-wide grep would mix functions.
under(Ancestor, Descendant) :- child(Ancestor, _, Descendant).
under(Ancestor, Descendant) :-
    child(Ancestor, _, Intermediate), under(Intermediate, Descendant).

% Semgrep does NOT encode Plus/FloorDiv/LtE as ast_tag(_, 'Plus').
% OCaml generic AST represents binary operators as:
% Call[Special[Op:"Plus", token], [Arg(x), Arg(y)]].
operator_call(Call, Operator) :-
    ast_tag(Call, 'Call'),
    at(Call, '0', Special), ast_tag(Special, 'Special'),
    at(Special, '0', OpNode), ast_tag(OpNode, 'Op'),
    value(OpNode, Scalar), ast_scalar(Scalar, Operator).

call_arg(Call, Index, Expr) :-
    at(Call, '1', Args), ast_tag(Args, 'list'),
    child(Args, Index, Wrapped), ast_tag(Wrapped, 'Arg'),
    value(Wrapped, Expr).

% N -> Id -> [ [name, token], id_info ]. Symbol identity is bound by name
% inside the same loop, not by the input function name or source filename.
identifier(Expr, Name) :-
    ast_tag(Expr, 'N'), value(Expr, Id), ast_tag(Id, 'Id'),
    at(Id, '0', NameTuple), ast_tag(NameTuple, 'list'),
    child(NameTuple, '0', Scalar), ast_scalar(Scalar, Name).

integer_literal(Expr, Number) :-
    ast_tag(Expr, 'L'), value(Expr, Int), ast_tag(Int, 'Int'),
    at(Int, '0', Some), ast_tag(Some, 'some'),
    value(Some, Scalar), ast_scalar(Scalar, Raw),
    atom_number(Raw, Number).

assignment(Node, Lhs, Rhs) :-
    ast_tag(Node, 'Assign'), at(Node, '0', Lhs), at(Node, '2', Rhs).

while_parts(While, Condition, Body) :-
    ast_tag(While, 'While'),
    at(While, '1', CondNode), ast_tag(CondNode, 'Cond'),
    value(CondNode, Condition),
    at(While, '2', Body), ast_tag(Body, 'Block').

if_parts(If, Condition, Then) :-
    ast_tag(If, 'If'),
    at(If, '1', CondNode), ast_tag(CondNode, 'Cond'),
    value(CondNode, Condition),
    at(If, '2', Then), ast_tag(Then, 'Block').

array_access(Expr, SequenceName, IndexName) :-
    ast_tag(Expr, 'ArrayAccess'),
    at(Expr, '0', Seq), identifier(Seq, SequenceName),
    at(Expr, '1', Index), identifier(Index, IndexName).

return_identifier(Return, Name) :-
    ast_tag(Return, 'Return'),
    at(Return, '1', Some), ast_tag(Some, 'some'),
    value(Some, Expr), identifier(Expr, Name).

% ----- Algorithm rule: inclusive-bounds iterative binary search ----------
% Require all conditions in the same While body AND unify the actual
% low/high/mid variables across condition, midpoint and updates.
loop_bounds(Condition, Low, High) :-
    operator_call(Condition, 'LtE'),
    call_arg(Condition, '0', LowExpr), identifier(LowExpr, Low),
    call_arg(Condition, '1', HighExpr), identifier(HighExpr, High),
    Low \== High.

midpoint_assignment(Body, Low, High, Mid) :-
    under(Body, Assign), assignment(Assign, MidExpr, Divide),
    identifier(MidExpr, Mid),
    Mid \== Low, Mid \== High,
    operator_call(Divide, 'FloorDiv'),
    call_arg(Divide, '0', Plus), operator_call(Plus, 'Plus'),
    call_arg(Plus, '0', AddA), identifier(AddA, Low),
    call_arg(Plus, '1', AddB), identifier(AddB, High),
    call_arg(Divide, '1', Two), integer_literal(Two, 2).

indexed_equal(Condition, Mid, Sequence, Target) :-
    operator_call(Condition, 'Eq'),
    call_arg(Condition, '0', Indexed),
    call_arg(Condition, '1', TargetExpr),
    array_access(Indexed, Sequence, Mid), identifier(TargetExpr, Target).
indexed_equal(Condition, Mid, Sequence, Target) :-
    operator_call(Condition, 'Eq'),
    call_arg(Condition, '1', Indexed),
    call_arg(Condition, '0', TargetExpr),
    array_access(Indexed, Sequence, Mid), identifier(TargetExpr, Target).

successful_match_branch(Body, Mid, Sequence, Target) :-
    under(Body, If), if_parts(If, Condition, Then),
    indexed_equal(Condition, Mid, Sequence, Target),
    under(Then, Return), return_identifier(Return, Mid).

narrow_lower_bound(Body, Low, Mid) :-
    under(Body, Assign), assignment(Assign, Lhs, Rhs),
    identifier(Lhs, Low), operator_call(Rhs, 'Plus'),
    call_arg(Rhs, '0', Index), identifier(Index, Mid),
    call_arg(Rhs, '1', One), integer_literal(One, 1).

narrow_upper_bound(Body, High, Mid) :-
    under(Body, Assign), assignment(Assign, Lhs, Rhs),
    identifier(Lhs, High), operator_call(Rhs, 'Minus'),
    call_arg(Rhs, '0', Index), identifier(Index, Mid),
    call_arg(Rhs, '1', One), integer_literal(One, 1).

% New rules can reuse child/3, at/3, operator_call/2 and identifier/2.
candidate(binary_search, evidence(Low, High, Mid, Sequence, Target)) :-
    while_parts(_, Condition, Body),
    loop_bounds(Condition, Low, High),
    midpoint_assignment(Body, Low, High, Mid),
    successful_match_branch(Body, Mid, Sequence, Target),
    narrow_lower_bound(Body, Low, Mid),
    narrow_upper_bound(Body, High, Mid).

% Original public predicate remains available for callers of AP1.
candidate(Algorithm) :- candidate(Algorithm, _).

main :-
    (   ast_node_count(Count)
    ->  format('AST nodes exported: ~w~n', [Count])
    ;   writeln('ERROR: missing AST fact file'), halt(2)
    ),
    (   once(candidate(binary_search, evidence(Low, High, Mid, Seq, Target)))
    ->  writeln('CANDIDATE: binary_search'),
        format('Evidence: loop ~w =< ~w; midpoint ~w = (~w + ~w) // 2; indexed comparison ~w[~w] == ~w; both bound updates~n',
               [Low, High, Mid, Low, High, Seq, Mid, Target]),
        writeln('Limit: candidate only; no semantic-equivalence proof')
    ;   writeln('UNKNOWN: no algorithm signature matched')
    ).
