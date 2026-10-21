/* v0.2 library-name fallback (doc 04 section 18.1), kept separate from the pipeline: a program whose computation IS
   one library call is named by that library's algorithm, from a table of library names (the user: "maintain prolog
   rules which map library name to algorithm name"). The program never runs; the facts are AP13's normal form.
     library_main -- Facts Kind Lang : prints LIB|Func|Name|Algorithm for every function (or script) that is a call,
                                       FUNC|Func for every function of the file, PART|Func for a function passed to
                                       the call (qsort's comparator)
   A library name inside other code is not the algorithm (gcd inside Pollard's rho, factorial inside nCr, sorted inside a
   median), so the call must be the function's whole result, or the whole of a script that defines no other code.
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'ta_signature.pl', T), load_files(T, []).

library_main :-
    current_prolog_flag(argv, [Facts, Kind, Lang|_]), tree_load(Facts, Kind),
    forall(distinct(F-N-A, library_answer(Lang, F, N, A)), ( func(F, FN, _), format('LIB|~w|~w|~w~n', [FN, N, A]) )),
    forall(( func(_, FN, _), FN \== '<toplevel>' ), format('FUNC|~w~n', [FN])),
    forall(distinct(G, part_of_call(Lang, G)), format('PART|~w~n', [G])).
% part_of_call(Lang, G): own function G is passed to the library call (a comparator, a key function)
part_of_call(Lang, G) :-
    library_answer(Lang, F, N, _), in_func(S, F), call_at(S, N, Args), sub_term(var(G0), Args), atom(G0),
    func(_, G, _), base_name(G, G0).

% library_algorithm(Lang, Name, Shape, Algorithm): the call Name(Args) computes Algorithm. Lang is any or one language
% (python, haskell, c, lisp); Shape has one entry per argument: in (an input of the function), any (a constant, a
% comparator). Names too generic to say what is computed (distance, find, index, search) are left out.
library_algorithm(python, factorial, [in], factorial).          % math.factorial, scipy.special.factorial
library_algorithm(python, gcd, [in, in], gcd).                  % math.gcd, fractions.gcd
library_algorithm(python, lcm, [in, in], lcm).                  % math.lcm
library_algorithm(python, sorted, [in], sorting).
library_algorithm(python, sort, [in], sorting).                 % xs.sort() (the object is the first argument)
library_algorithm(python, isprime, [in], prime_check).          % sympy.isprime
library_algorithm(haskell, gcd, [in, in], gcd).
library_algorithm(haskell, lcm, [in, in], lcm).
library_algorithm(haskell, sort, [in], sorting).                % Data.List.sort
library_algorithm(c, qsort, [in, any, any, any], sorting).
library_algorithm(lisp, cl_gcd, [any, in, in], gcd).            % ECL: (gcd a b) -> cl_gcd(2, a, b)
library_algorithm(lisp, cl_lcm, [any, in, in], lcm).
library_algorithm(lisp, cl_sort, [any, in, any], sorting).      % (sort xs #'<)
library_algorithm(lisp, cl_stable_sort, [any, in, any], sorting).

% library_answer(Lang, F, Name, Algorithm)
% 1. a function whose every result is the library call on its own parameters
library_answer(Lang, F, N, A) :-
    func(F, FN, _), FN \== '<toplevel>',
    findall(V, ( in_func(S, F), ret(S, V) ), Vs), Vs = [V0|_],
    lib_call(Lang, F, V0, N, A, param), forall(member(V, Vs), lib_call(Lang, F, V, N, A, param)).
% 2. an in-place library sort of a parameter, the parameter then returned (or nothing returned)
library_answer(Lang, F, N, sorting) :-
    func(F, FN, _), FN \== '<toplevel>', \+ under(_, _),
    stmt(S, F, call, _), call_at(S, N, Args), lib_args(F, Args, As), library_algorithm(L, N, Shape, sorting), lang(L, Lang),
    shape(Shape, As, F, param),
    forall(( in_func(S2, F), S2 \== S ), ( ret(S2, R), memberchk(R, As) )).
% 3. a script: top-level code of no loop, in a file with no other function, whose result or printed value is the call
library_answer(Lang, F, N, A) :-
    func(F, '<toplevel>', _), \+ ( func(G, GN, _), GN \== '<toplevel>', \+ library_answer(Lang, G, _, _) ),
    \+ ( in_func(S0, F), under(S0, _) ),
    in_func(S, F), ( ret(S, V) ; call_at(S, print, [V]) ; call_at(S, N0, As0), V = call(N0, As0) ),
    lib_call(Lang, F, V, N, A, script).

lib_call(Lang, F, call(N, Args), N, A, Mode) :-
    atom(N), N \== '$self', \+ own_function(N), lib_args(F, Args, As),
    library_algorithm(L, N, Shape, A), lang(L, Lang), shape(Shape, As, F, Mode).
lang(any, _) :- !.
lang(L, L).
% a module written as the call's object (math.factorial(n) -> factorial(math, n)) is not an argument
lib_args(F, [var(M)|As], As) :- \+ param(F, _, M), \+ value(_, var(M), _), !.
lib_args(_, As, As).
% shape(Shape, Args, F, Mode): an `in` argument is a parameter of F (a function) or any value (a script)
shape([], [], _, _).
shape([in|Sh], [X|Xs], F, Mode) :- input(Mode, F, X), shape(Sh, Xs, F, Mode).
shape([any|Sh], [_|Xs], F, Mode) :- shape(Sh, Xs, F, Mode).
input(param, F, var(P)) :- param(F, _, P).
input(script, _, _).
