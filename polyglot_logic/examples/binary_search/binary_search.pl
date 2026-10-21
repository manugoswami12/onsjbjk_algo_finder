binary_search(List, Target, Index) :-
    length(List, N), High is N - 1,
    search(List, Target, 0, High, Index).
search(_, _, Low, High, -1) :- Low > High, !.
search(List, Target, Low, High, Index) :-
    Mid is (Low + High) // 2,
    nth0(Mid, List, Value),
    (   Value =:= Target -> Index = Mid
    ;   Value < Target -> Low1 is Mid + 1, search(List, Target, Low1, High, Index)
    ;   High1 is Mid - 1, search(List, Target, Low, High1, Index)
    ).
