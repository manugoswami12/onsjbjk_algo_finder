/* AP3 opt-in multi-algorithm recognition. AP2 classify.pl is preserved.
   Usage: swipl -q -f none -s prolog/multi_classify.pl -s out/facts.pl
                 -g main_multi -t halt
*/
:- ensure_loaded('classify.pl').
:- ensure_loaded('ast_regions.pl').
:- ensure_loaded('bubble_rules.pl').

% Existing binary search rule localized to each While in its own function.
% Strengthened for multi-recognition by checking the Lt branch and the
% corresponding Else branch update. The legacy AP2 candidate/2 is unchanged.
indexed_less(Condition, Mid, Sequence, Target) :-
    operator_call(Condition, 'Lt'),
    call_arg(Condition, '0', Indexed),
    array_access(Indexed, Sequence, Mid),
    call_arg(Condition, '1', Expr), identifier(Expr, Target).

% Semgrep encodes 'else:' under the 4th If tuple element, Some(Block).
if_else_body(If, ElseBody) :-
    at(If, '3', Maybe), ast_tag(Maybe, 'some'),
    value(Maybe, ElseBody), ast_tag(ElseBody, 'Block').

correct_binary_branch(Body, Low, High, Mid, Sequence, Target) :-
    under(Body, If), if_parts(If, Condition, ThenBody),
    indexed_less(Condition, Mid, Sequence, Target),
    narrow_lower_bound(ThenBody, Low, Mid),
    if_else_body(If, ElseBody),
    narrow_upper_bound(ElseBody, High, Mid).

% Support 'elif' encoding as Else(Some(If)) in addition to a direct If.
correct_binary_branch(Body, Low, High, Mid, Sequence, Target) :-
    under(Body, If), if_parts(If, Condition, ThenBody),
    indexed_less(Condition, Mid, Sequence, Target),
    narrow_lower_bound(ThenBody, Low, Mid),
    at(If, '3', Maybe), ast_tag(Maybe, 'some'),
    value(Maybe, ElseIf), ast_tag(ElseIf, 'If'),
    if_else_body(ElseIf, ElseBody),
    narrow_upper_bound(ElseBody, High, Mid).

binary_instance(Definition, While,
                evidence(bounds(Low, High), midpoint(Mid),
                         array(Sequence), target(Target))) :-
    function_definition(Definition, _, FunctionBody),
    under(FunctionBody, While),
    while_parts(While, Condition, Body),
    loop_bounds(Condition, Low, High),
    midpoint_assignment(Body, Low, High, Mid),
    successful_match_branch(Body, Mid, Sequence, Target),
    correct_binary_branch(Body, Low, High, Mid, Sequence, Target),
    \+ (under(FunctionBody, NestedDef),
        ast_tag(NestedDef, 'DefStmt'), under(NestedDef, While)).

% Backtracking enumerates all regions rather than using once/1. Keep a
% definition ID so duplicate names in separate functions do not mix.
algorithm_instance_in(Definition, Name, binary_search, Region, Evidence) :-
    function_definition(Definition, Name, _),
    binary_instance(Definition, Region, Evidence).
algorithm_instance_in(Definition, Name, bubble_sort, Region, Evidence) :-
    function_definition(Definition, Name, _),
    bubble_instance(Definition, Region, Evidence).

% Requested public 3-place relational query.
algorithm_instance(FunctionName, Algorithm, Region) :-
    algorithm_instance_in(_, FunctionName, Algorithm, Region, _).

algorithm_before(Definition, AlgoA, RegionA, AlgoB, RegionB) :-
    algorithm_instance_in(Definition, _, AlgoA, RegionA, _),
    algorithm_instance_in(Definition, _, AlgoB, RegionB, _),
    function_region_order(Definition, RegionA, RegionB).

show_instances(Definition, Name) :-
    findall(Algo-Region-Evidence,
            algorithm_instance_in(Definition, Name, Algo, Region, Evidence),
            Found),
    sort(Found, Unique),
    ( Unique = [] -> format('UNKNOWN: ~w (no recognized algorithm region)~n', [Name])
    ; forall(member(Algo-Region-Evidence, Unique),
             ( format('CANDIDATE: ~w; function: ~w; AST region: ~w~n',
                      [Algo, Name, Region]),
               format('Evidence: ~q~n', [Evidence]) ))
    ),
    forall((member(AlgoA-RegionA-_,Unique),
            member(AlgoB-RegionB-_,Unique),
            function_region_order(Definition, RegionA, RegionB)),
           format('RELATION: ~w BEFORE ~w; function: ~w; regions: ~w, ~w~n',
                  [AlgoA,AlgoB,Name,RegionA,RegionB])).

main_multi :-
    ( ast_node_count(N) -> format('AST nodes exported: ~w~n', [N])
    ; writeln('ERROR: missing AST fact file'), halt(2) ),
    ( setof(Def-Name-Body, function_definition(Def,Name,Body), Definitions)
    -> forall(member(Def-Name-_, Definitions), show_instances(Def,Name))
    ; writeln('UNKNOWN: no named functions found') ),
    writeln('Limit: structural candidates only, no semantic-equivalence proof').
