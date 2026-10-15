/* AP6 opt-in; includes original AP5 binary and bubble matchers unchanged.
   Usage: swipl -q -f none -s prolog/thread_classify.pl -s out/facts.pl
                  -g main_threads -t halt
*/
:- ensure_loaded('multi_classify.pl').
:- ensure_loaded('thread_rules.pl').

thread_instance_in(D, N, A, R, E) :- algorithm_instance_in(D, N, A, R, E).
thread_instance_in(D, N, rolling_hash_update, R, E) :-
    function_definition(D, N, _), rolling_hash_instance(D, R, E).

% Public reversible query: ask for function, operation, region or all three.
recognized_thread(Function, Algorithm, Region) :-
    thread_instance_in(_, Function, Algorithm, Region, _).

show_threads(Definition, Name) :-
    findall(Algo-Region-Evidence,
            thread_instance_in(Definition, Name, Algo, Region, Evidence),
            Matches),
    sort(Matches, Unique),
    ( Unique = []
    -> format('UNKNOWN: ~w (no recognized logic thread)~n', [Name])
    ; forall(member(Algo-Region-Evidence, Unique),
             (format('CANDIDATE: ~w; function: ~w; AST region: ~w~n',
                     [Algo, Name, Region]),
              format('Evidence: ~q~n', [Evidence])))
    ),
    % AP5 sibling BEFORE reports continue to work for direct sibling regions.
    forall((member(AlgoA-RegionA-_,Unique),
            member(AlgoB-RegionB-_,Unique),
            function_region_order(Definition, RegionA, RegionB)),
           format('RELATION: ~w BEFORE ~w; function: ~w; regions: ~w, ~w~n',
                  [AlgoA, AlgoB, Name, RegionA, RegionB])),
    findall(Bubble-Update-Evidence,
            interleaved_sort_hash(Definition, Bubble, Update, Evidence),
            RawLinks),
    sort(RawLinks, Links),
    forall(member(Bubble-Update-LinkEvidence, Links),
           (format('RELATION: rolling_hash_update INTERLEAVED_WITH bubble_sort; function: ~w; regions: ~w, ~w~n',
                   [Name, Update, Bubble]),
            format('Thread link: ~q~n', [LinkEvidence]))).

main_threads :-
    (ast_node_count(Count)
    -> format('AST nodes exported: ~w~n', [Count])
    ; writeln('ERROR: missing AST fact file'), halt(2)),
    (setof(Def-Name-Body, function_definition(Def, Name, Body), Definitions)
    -> forall(member(Def-Name-_, Definitions), show_threads(Def, Name))
    ; writeln('UNKNOWN: no named functions found')),
    writeln('Limit: structural candidates only; no semantic equivalence or hash correctness proof').
