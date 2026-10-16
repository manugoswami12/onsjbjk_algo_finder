bsearch(A, T, Lo, Hi, M) :- Lo =< Hi, M0 is (Lo + Hi) // 2, nth0(M0, A, X),
    ( X =:= T -> M = M0 ; X < T -> Lo1 is M0 + 1, bsearch(A, T, Lo1, Hi, M) ; Hi1 is M0 - 1, bsearch(A, T, Lo, Hi1, M) ).
