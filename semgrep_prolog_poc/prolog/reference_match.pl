/* AP9 GENERIC match engine. ALL algorithm-specific clauses are generated
   statically from reference ASTs, not handwritten for bubble/hash/etc.
   The reference label is a user-supplied identifier, not inferred semantics.
   Run: swipl -q -f none -s reference_match.pl -s reference.pl -s target.pl
        -g main_reference -t halt
*/
:- dynamic reference_pattern/4, candidate_pattern/4.

distinct_binding_names([]).
distinct_binding_names([slot(_, Bound)|Rest]) :-
    forall(member(slot(_, Other), Rest), dif(Bound, Other)),
    distinct_binding_names(Rest).

reference_match(Label, Function, Region, Bindings) :-
    reference_pattern(Label, Kind, ReferenceTree, Bindings),
    candidate_pattern(Function, Region, Kind, TargetTree),
    ReferenceTree = TargetTree,
    distinct_binding_names(Bindings).

main_reference :-
    findall(match(L, F, R, B), reference_match(L, F, R, B), Matches),
    ( Matches == [] -> writeln('UNKNOWN: no reference structural match')
    ; forall(member(match(L, F, R, B), Matches),
             format('REFERENCE_STRUCTURAL_MATCH: ~q; function: ~q; region: ~q; bindings: ~q~n',
                    [L, F, R, B]))
    ),
    writeln('Limit: reference structural match only; NOT semantic equivalence proof').

/* Machine-consumable interface for ASCII identifier labels/functions. */
main_reference_machine :-
    forall(reference_match(L, F, R, _),
           format('AP9MATCH|~w|~w|~w~n', [L, F, R])).
