% Standalone proof of concept only. Loaded facts use anonymous f1/f2 identifiers.
% These routes are BROAD candidate branches, never algorithm identifications.
:- dynamic program/2.
:- dynamic observed/3.

route(F, sequence_rearrangement) :-
    observed(F, input_sequence_mutated, _),
    observed(F, element_exchange, _).

route(F, comparison_driven_reordering) :-
    route(F, sequence_rearrangement),
    observed(F, comparison_controls_exchange, _).

route(F, indexed_lookup) :-
    observed(F, indexed_equality_controls_index_return, _).

route(F, interval_lookup) :-
    route(F, indexed_lookup),
    observed(F, coherent_midpoint_interval_update, _).

route(F, unknown) :-
    \+ route(F, sequence_rearrangement),
    \+ route(F, indexed_lookup).

main :-
    current_prolog_flag(argv, [FactsFile|_]),
    consult(FactsFile),
    forall(program(F, _), (
        findall(Route, route(F, Route), Routes0),
        sort(Routes0, Routes),
        forall(member(Route, Routes), format('ROUTE ~w ~w~n', [F, Route]))
    )),
    halt.
