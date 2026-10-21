/* AP10 OPT-IN generic structural thread matcher.
   Retains all AST operators, branch structure and variable identity.
   Only OCaml Block statement lists may contain extra target statements.
   No algorithm names or algorithm-specific rules exist here.
   Reference labels come entirely from AP9-generated reference_pattern/4.
   Load AFTER AP9 reference_match.pl and generated reference/candidate .pl files.
*/

/* Record the same target loop path across independent matches. Paths are
   target-tree paths, not reference-tree paths. */
ap10_tree(binding(X), binding(Y), _, []) :- !, X = Y.
ap10_tree(obj(Reference), obj(Target), Path, Loops) :- !,
    ( Reference = [kv('For', _)] -> Here = [Path] ; Here = [] ),
    ap10_fields(Reference, Target, Path, Below),
    append(Here, Below, Loops).
ap10_tree(arr(Reference), arr(Target), Path, Loops) :- !,
    ap10_exact_list(Reference, Target, Path, 0, Loops).
ap10_tree(Value, Value, _, []).

ap10_fields([], [], _, []).
ap10_fields([kv(Key, Ref)|MoreRef], [kv(Key, Tgt)|MoreTgt], Path, Loops) :-
    ( Key == 'Block', Ref = arr(RefStatements), Tgt = arr(TgtStatements)
    -> ap10_statement_subsequence(RefStatements, TgtStatements, ['Block'|Path], 0, A)
    ;  ap10_tree(Ref, Tgt, [Key|Path], A)
    ),
    ap10_fields(MoreRef, MoreTgt, Path, B),
    append(A, B, Loops).

ap10_exact_list([], [], _, _, []).
ap10_exact_list([R|Rs], [T|Ts], Path, I, Loops) :-
    ap10_tree(R, T, [I|Path], A),
    Next is I + 1,
    ap10_exact_list(Rs, Ts, Path, Next, B),
    append(A, B, Loops).

/* This is where noncontiguous code becomes visible. We never omit any
   required reference statement, and preserve its original ordering. */
ap10_statement_subsequence([], _, _, _, []).
ap10_statement_subsequence([R|Rs], [T|Ts], Path, I, Loops) :-
    Next is I + 1,
    ( ap10_tree(R, T, [I|Path], A),
      ap10_statement_subsequence(Rs, Ts, Path, Next, B),
      append(A, B, Loops)
    ; ap10_statement_subsequence([R|Rs], Ts, Path, Next, Loops)
    ).

/* Only compare full body patterns for composition, so the candidate region
   identifies a single function instance, not two unrelated AST fragments. */
ap10_thread(Label, Function, Region, Bindings, Loops) :-
    reference_pattern(Label, body, Reference, Bindings),
    candidate_pattern(Function, Region, body, Target),
    ap10_tree(Reference, Target, [], Loops),
    distinct_binding_names(Bindings).

ap10_pair(L1, L2, Function, Region, Relation, Witness) :-
    ap10_thread(L1, Function, Region, _, Loops1),
    ap10_thread(L2, Function, Region, _, Loops2),
    L1 @< L2,
    ( member(LoopPath, Loops1), memberchk(LoopPath, Loops2)
    -> Relation = shared_loop, Witness = LoopPath
    ;  Relation = same_function, Witness = none
    ).

main_ap10 :-
    findall(thread(L,F,R,B,Ps), ap10_thread(L,F,R,B,Ps), Raw),
    sort(Raw, Matches),
    ( Matches = [] -> writeln('UNKNOWN: no AP10 thread match')
    ; forall(member(thread(L,F,R,B,Ps), Matches),
             format('AP10_THREAD: ~q; function: ~q; region: ~q; bindings: ~q; loops: ~q~n',
                    [L,F,R,B,Ps]))
    ),
    findall(pair(L1,L2,F,R,Rel,Path), ap10_pair(L1,L2,F,R,Rel,Path), Pairs0),
    sort(Pairs0, Pairs),
    forall(member(pair(A,B,Fn,Region,Rel,Path), Pairs),
           format('AP10_RELATION: ~q + ~q; function: ~q; region: ~q; relation: ~q; witness: ~q~n',
                  [A,B,Fn,Region,Rel,Path])),
    writeln('Limit: structural thread matches only. SHARED_LOOP is not proof of joint execution or algorithm correctness.').
