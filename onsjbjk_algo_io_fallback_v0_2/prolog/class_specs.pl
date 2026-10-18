/* v0.2 class relations (doc 04 section 18): what an algorithm computes, written as a relation between its input and
   its output, run in the mode the case needs (user: sum(2,3,X), sum(2,X,10)): the output computed from the input
   where it is a function (sorted/2), or checked where several outputs are right (a search returns any position of
   the target). A program is in class C when every run of its Prolog normal form on the battery (AP13 io_trace: the
   source never runs) satisfies spec(C, Inputs, Output), on at least min_runs runs.
     class_main -- Runs : reads run(Fun, Sig, Inputs, OutputText) facts (the output as io_trace prints it, read here
                          as a term), prints CLASS|Fun|Class
   A class names what is computed, not how: bubble sort and merge sort are both `sorting`; which one it is, is the
   structural rules' answer (ta_rules.pl). A program that runs and satisfies no class relation is a new class.
*/
:- dynamic run/4.
:- discontiguous spec/4.

min_runs(4).

class_main :-
    current_prolog_flag(argv, [Runs|_]), load_files(Runs, [if(true)]),
    forall(( distinct(F, run(F, _, _, _)), spec_name(C), holds_for_all(F, C) ), format('CLASS|~w|~w~n', [F, C])).

spec_name(C) :- distinct(C, clause(spec(C, _, _, _), _)).
holds_for_all(F, C) :-
    findall(S-I-O, ( run(F, S, I, A), catch(term_to_atom(O, A), _, fail) ), Rs), Rs = [S0-_-_|_], spec_sig(C, S0),
    include([_-I-O]>>catch(spec(C, S0, I, O), _, fail), Rs, Ok), length(Rs, N), length(Ok, N),
    min_runs(M), N >= M, \+ trivial(Rs), !.
% a function whose output never depends on its input says nothing
trivial(Rs) :- findall(O, member(_-_-O, Rs), Os), sort(Os, [_]).
spec_sig(C, S) :- clause(spec(C, S1, _, _), _), S1 == S, !.

% ----- list -> list ---------------------------------------------------------------------------------------------
spec(sorting, [list], [L], O) :- is_list(O), msort(L, O).                         % ascending, a permutation
spec(sorting, [list], [L], O) :- is_list(O), msort(L, S), reverse(S, O), L \== [].  % descending
spec(reverse_list, [list], [L], O) :- reverse(L, O), L \== O.
spec(dedup, [list], [L], O) :- is_list(O), list_to_set(L, O).
% ----- list -> scalar -------------------------------------------------------------------------------------------
spec(maximum, [list], [L], O) :- L \== [], max_list(L, O).
spec(minimum, [list], [L], O) :- L \== [], min_list(L, O).
spec(sum_list, [list], [L], O) :- sum_list(L, O).
spec(palindrome_check, [list], [L], O) :- truth(O, T), ( reverse(L, L) -> T = true ; T = false ).
% ----- search: list, target -> a position of it (or not found) ----------------------------------------------------
spec(search, [list, int], [L, T], O) :- integer(O), O >= 0, nth0(O, L, T).
spec(search, [list, int], [L, T], O) :- \+ memberchk(T, L), not_found(O).
not_found(O) :- memberchk(O, [-1, none, false, nil, 'None', []]).
% ----- int, int -> int --------------------------------------------------------------------------------------------
spec(gcd, [int, int], [A, B], O) :- O =:= gcd(A, B).
spec(lcm, [int, int], [A, B], O) :- A > 0, B > 0, O =:= A * B // gcd(A, B).
spec(lcm, [int, int], [A, B], 0) :- ( A =:= 0 ; B =:= 0 ).
spec(power, [int, int], [A, B], O) :- B >= 0, O =:= A ^ B.
% ----- int -> int / bool / list -------------------------------------------------------------------------------------
spec(factorial, [int], [N], O) :- N >= 0, N =< 40, fact(N, O).
spec(fibonacci, [int], [N], O) :- N =< 40, fib(N, O).                          % fib(0) = 0
spec(fibonacci, [int], [N], O) :- N =< 40, N1 is N + 1, fib(N1, O).           % fib(0) = 1
spec(fibonacci, [int], [N], O) :- N =< 25, is_list(O), fib_prefix(N, O).       % the first n numbers
spec(prime_check, [int], [N], O) :- truth(O, T), ( prime(N) -> T = true ; T = false ).
spec(primes_upto, [int], [N], O) :- is_list(O), N =< 128, findall(P, ( between(2, N, P), prime(P) ), O).
spec(primes_upto, [int], [N], O) :- is_list(O), N =< 128, M is N - 1, findall(P, ( between(2, M, P), prime(P) ), O).
spec(perfect_number, [int], [N], O) :- truth(O, T), ( N > 1, divisor_sum(N, N) -> T = true ; T = false ).
spec(digit_sum, [int], [N], O) :- N >= 0, digits(N, Ds), sum_list(Ds, O).
spec(collatz, [int], [N], O) :- N >= 1, N =< 128, is_list(O), collatz(N, O).
spec(collatz, [int], [N], O) :- N >= 1, N =< 128, integer(O), collatz(N, S), length(S, Len),
    ( O =:= Len ; O =:= Len - 1 ).
spec(leap_year, [int], [Y], O) :- truth(O, T), ( ( Y mod 4 =:= 0, Y mod 100 =\= 0 ; Y mod 400 =:= 0 ) -> T = true ; T = false ).
spec(luhn, [int], [N], O) :- truth(O, T), digits(N, Ds), reverse(Ds, Rs), luhn_sum(Rs, 0, S),
    ( S mod 10 =:= 0 -> T = true ; T = false ).
spec(n_queens_count, [int], [N], O) :- integer(O), queens_count(N, O).
spec(triangular, [int], [N], O) :- O =:= N * (N + 1) // 2.
spec(square, [int], [N], O) :- O =:= N * N.
spec(is_even, [int], [N], O) :- truth(O, T), ( N mod 2 =:= 0 -> T = true ; T = false ).

% ----- helpers ----------------------------------------------------------------------------------------------------
truth(O, true) :- memberchk(O, [true, 1, 'True', t]), !.
truth(O, false) :- memberchk(O, [false, 0, 'False', nil, []]).
fact(0, 1) :- !.
fact(N, F) :- N1 is N - 1, fact(N1, F1), F is N * F1.
fib(N, F) :- fib(N, 0, 1, F).
fib(0, A, _, A) :- !.
fib(N, A, B, F) :- N1 is N - 1, C is A + B, fib(N1, B, C, F).
fib_prefix(N, L) :- findall(F, ( between(0, N, K), K < N, fib(K, F) ), L0), ( L = L0 ; N1 is N + 1,
    findall(F, ( between(1, N1, K), K =< N, fib(K, F) ), L1), L = L1 ), !.
prime(N) :- N >= 2, \+ ( between(2, N, D), D * D =< N, N mod D =:= 0 ).
divisor_sum(N, S) :- M is N - 1, aggregate_all(sum(D), ( between(1, M, D), N mod D =:= 0 ), S).
digits(0, [0]) :- !.
digits(N, Ds) :- digits_(N, [], Ds).
digits_(0, Ds, Ds) :- !.
digits_(N, Acc, Ds) :- D is N mod 10, N1 is N // 10, digits_(N1, [D|Acc], Ds).
collatz(1, [1]) :- !.
collatz(N, [N|T]) :- ( N mod 2 =:= 0 -> M is N // 2 ; M is 3 * N + 1 ), collatz(M, T).
luhn_sum([], S, S).
luhn_sum([D], A, S) :- S is A + D.
luhn_sum([D, E|T], A, S) :- E2 is E * 2, ( E2 > 9 -> E3 is E2 - 9 ; E3 = E2 ), A1 is A + D + E3, luhn_sum(T, A1, S).
queens_count(N, C) :- N >= 0, N =< 9, nth0(N, [1, 1, 0, 0, 2, 10, 4, 40, 92, 352], C).
