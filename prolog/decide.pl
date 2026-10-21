/* The answer of a file from its evidence (doc 04 section 17): the tiers are data, tried in the order tier/2 states;
   inside a tier every label is collected (setof), so no clause order and no cut decide anything.
     tier 1 file_rule  a file rule (ta_file_rules.pl hand_specific/2)
     tier 2 built      a built or hand branch at the file's node (families_v02.pl, ta_rules.pl hand_branch/3)
     tier 3 trace      a learned branch holding with an exact trace (write trace, or AP13's traced logic)
     tier 4 learned    a learned branch holding with the behaviour (input -> output)
     tier 5 canonical  traced logic in the canonical view (eval_ta.CanonicalLogic: the tree's facts, input checks as
                       context, range bounds variables), where the literal view matches nothing, for a label learned
                       at the file's own node (doc 04 section 19.13)
     tier 6 io         the behaviour alone: the input -> output fallback
   The first tier that names anything decides: one group is the answer, several are UNKNOWN (ambiguous); a file whose
   evidence names nothing at any tier has no answer.
     decide_main -- Facts : GOT|Tier|Group, AMBIGUOUS|Tier|Group,Group,..., or NONE
   Facts: evidence(Tier, Label) for the file, group(Label, Group) for its labels (a Rosetta task, a numbered variant's
   base label; a label without a group fact is its own group).
*/
:- dynamic evidence/2, group/2.

tier(1, file_rule).
tier(2, built).
tier(3, trace).
tier(4, learned).
tier(5, canonical).
tier(6, io).

grouped(L, G) :- ( group(L, G0) -> G = G0 ; G = L ).
tier_groups(Tier, Gs) :- setof(G, L^( evidence(Tier, L), grouped(L, G) ), Gs).

decide(Answer) :-
    (   tier(_, Tier), tier_groups(Tier, Gs)
    ->  ( Gs = [G] -> Answer = got(Tier, G) ; Answer = ambiguous(Tier, Gs) )
    ;   Answer = none
    ).

decide_main :-
    current_prolog_flag(argv, [Facts|_]), load_files(Facts, []), decide(A),
    (   A = got(T, G) -> format('GOT|~w|~w~n', [T, G])
    ;   A = ambiguous(T, Gs) -> atomic_list_concat(Gs, ',', GA), format('AMBIGUOUS|~w|~w~n', [T, GA])
    ;   format('NONE~n', [])
    ).
