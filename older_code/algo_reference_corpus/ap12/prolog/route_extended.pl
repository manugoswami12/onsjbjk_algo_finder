% Independent AP12 router. Frozen v0.1 Prolog router remains unchanged.
% No substring/filename or function-name algorithm guesses.
:- dynamic program/2.
:- dynamic observed/3.

route(F, sequence_rearrangement) :-
    observed(F,input_sequence_mutated,_),
    observed(F,element_exchange,_).
route(F, comparison_driven_reordering) :-
    route(F,sequence_rearrangement), observed(F,comparison_controls_exchange,_).
route(F, indexed_lookup) :-
    observed(F,indexed_equality_controls_index_return,_).
route(F, interval_lookup) :-
    route(F,indexed_lookup), observed(F,coherent_midpoint_interval_update,_).
route(F, interval_lookup) :-
    observed(F,bounded_indexed_interval_lookup,_).
route(F, unknown) :-
    \+ route(F,sequence_rearrangement),
    \+ route(F,indexed_lookup),
    \+ route(F,interval_lookup).

main :-
    current_prolog_flag(argv,[File|_]),
    consult(File),
    forall(program(F,_),(
        findall(Branch,route(F,Branch),Raw),
        sort(Raw,Unique),
        forall(member(B,Unique),format('ROUTE ~w ~w~n',[F,B]))
    )),
    halt.
