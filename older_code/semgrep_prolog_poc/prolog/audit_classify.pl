/* AP8 opt-in conservative structural audit; AP7 rules remain untouched.
   swipl -q -f none -s prolog/audit_classify.pl -s out/facts.pl -g main_audit -t halt
*/
:- ensure_loaded('thread_classify.pl').
:- ensure_loaded('audit_ast.pl').
:- ensure_loaded('audit_rules.pl').

/* Reversible public query: enumerate any of Function, Algorithm, Region,
   Status. This derives facts; it does not build a separate simplified AST. */
recognition_audit(Function, Algorithm, Region, Status) :-
    audit_status(_, Function, Algorithm, Region, Status, _).

show_audit(D, Name) :-
    findall(Status-Algo-Region-Evidence,
            audit_status(D, Name, Algo, Region, Status, Evidence), Raw),
    sort(Raw, Results),
    ( Results == []
    -> format('UNKNOWN: ~w (no supported structural candidate)~n', [Name])
    ; forall(member(Status-Algo-Region-Evidence, Results),
             (format('~w: ~w; function: ~w; AST region: ~w~n',
                     [Status, Algo, Name, Region]),
              format('Evidence: ~q~n', [Evidence]),
              (Status == unverified
              -> findall(Why, audit_blocker(D,Algo,Region,Why), Blocked),
                 sort(Blocked, Reasons),
                 format('Audit blockers: ~q~n', [Reasons])
              ; true)))
    ),
    findall(Bubble-Update-E,
            audited_interleaving(D, Bubble, Update, E), RawLinks),
    sort(RawLinks, Links),
    forall(member(Bubble-Update-Link, Links),
           (format('INTERLEAVED_AUDITED: rolling_hash_update + bubble_sort; function: ~w; regions: ~w, ~w~n',
                   [Name, Update, Bubble]),
            format('Thread link: ~q~n', [Link]))).

main_audit :-
    (ast_node_count(Count)
    -> format('AST nodes exported: ~w~n', [Count])
    ; writeln('ERROR: missing AST fact file'), halt(2)),
    (setof(D-N-B, function_definition(D,N,B), Defs)
    -> forall(member(D-N-_, Defs), show_audit(D,N))
    ; writeln('UNKNOWN: no named functions found')),
    writeln('Limit: audited_structural is only exact AST structural evidence, not semantic proof; unverified is not absent.').
