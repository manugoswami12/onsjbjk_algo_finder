/* AP3 shared region queries over the *unchanged* exact Semgrep AST facts.
   Loaded after AP2 classify.pl, which supplies child/3, value/2, at/3,
   under/2, identifier/2 and operator_call/2. No derived fact rewriting.
*/

% A function is a DefStmt carrying a FuncDef with FBStmt(Block(...)).
function_definition(Definition, Name, Body) :-
    ast_tag(Definition, 'DefStmt'),
    at(Definition, '0', Entity),
    child(Entity, 'name', EN), ast_tag(EN, 'EN'),
    value(EN, Id), ast_tag(Id, 'Id'),
    at(Id, '0', NameTuple),
    child(NameTuple, '0', NameScalar), ast_scalar(NameScalar, Name),
    at(Definition, '1', Kind), ast_tag(Kind, 'FuncDef'),
    % Semgrep's OCaml FuncDef variant wraps a record payload.  fbody is
    % a field on THAT record, not a child directly under FuncDef.
    value(Kind, Fields), ast_tag(Fields, 'record'),
    child(Fields, 'fbody', FBStmt), ast_tag(FBStmt, 'FBStmt'),
    value(FBStmt, Body), ast_tag(Body, 'Block').

% A statement belongs to the given function body; matches must never borrow
% evidence from a different function. Function scopes within nested functions
% are excluded, should the generic AST contain any.
function_region(Definition, Name, Region) :-
    function_definition(Definition, Name, Body),
    under(Body, Region),
    \+ (under(Body, NestedDef),
        ast_tag(NestedDef, 'DefStmt'),
        under(NestedDef, Region)).

% Only infer before/after for direct siblings of a single concrete Block.
% Index is the actual OCaml AST list-position label (not a source-line guess).
direct_block_order(First, Second) :-
    ast_tag(Block, 'Block'), value(Block, Statements),
    ast_tag(Statements, 'list'),
    child(Statements, Index1, First),
    child(Statements, Index2, Second),
    atom_number(Index1, Order1), atom_number(Index2, Order2),
    Order1 < Order2.

% Strictly tied to one containing function rather than all blocks in a file.
function_region_order(Definition, First, Second) :-
    function_definition(Definition, _, Body),
    under(Body, First), under(Body, Second),
    direct_block_order(First, Second).

% Useful generic structural terms for all algorithms.
array_index_expression(Array, Name, Index) :-
    ast_tag(Array, 'ArrayAccess'),
    at(Array, '0', Sequence), identifier(Sequence, Name),
    at(Array, '1', Index).

index_base(Index, Name) :- identifier(Index, Name).
index_plus_one(Index, Name) :-
    operator_call(Index, 'Plus'),
    call_arg(Index, '0', Left), identifier(Left, Name),
    call_arg(Index, '1', Right), integer_literal(Right, 1).
index_plus_one(Index, Name) :-
    operator_call(Index, 'Plus'),
    call_arg(Index, '1', Left), identifier(Left, Name),
    call_arg(Index, '0', Right), integer_literal(Right, 1).
