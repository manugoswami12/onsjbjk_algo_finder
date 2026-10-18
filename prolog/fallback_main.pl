/* v0.2 fallback (doc 03 section 9), SEPARATE from the normal process. It reads only the normal
   process's exported output (ecl_main.pl ecl_export: the facts after ecl_norm and the FAMILY
   answers) and answers, for a function the normal process gave no v0.2 branch, by deterministic
   pattern rules (prolog/fallback_rules.pl, DCGs) over a token stream of the function's result:
     - every result term is written in prefix order as tokens (tokens//3 below, a DCG too);
     - a call of (or a function object naming) a function of the same file is a LINK: its result
       tokens are spliced in between enter(G) and leave(G), at most 4 deep and never re-entering a
       function already on the path, so the walk always ends;
     - fallback_pattern(Branch, Rule)//0 rules parse the stream; the first that parses answers.
   fallback_main -- Export : FALLBACK|F|Name|Branch|Rule lines
   The tokenizer is shared with the learner: prolog/flow_tokens.pl.
*/
:- prolog_load_context(directory, Dir),
   forall(member(F, ['flow_tokens.pl', 'fallback_rules.pl']), ( directory_file_path(Dir, F, R), load_files(R, []) )).


fallback_main :-
    current_prolog_flag(argv, [Export|_]), load_files(Export, [if(true)]),
    forall(( func(F, Name, _), \+ answered(F), result_tokens(F, Ts), once(phrase(fallback_pattern(B, Rule), Ts)) ),
           format('FALLBACK|~w|~w|~w|~w~n', [F, Name, B, Rule])).
answered(F) :- family(F, _, B), B \== none, !.

% the function's results: its returned values, in statement order
