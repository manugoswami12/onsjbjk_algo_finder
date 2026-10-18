/* v0.2 file rules for TheAlgorithms/Python (doc 04 section 17.5): written by hand, one label at a time, for the files the
   learned branches and the general hand rules (ta_rules.pl) do not answer with their own label. Each rule names the
   component that makes the file its algorithm and that no file of another label has (found with ta_distinct.py,
   checked over the whole corpus: T2).
     hand_specific(F, Label)   function F's file is the algorithm Label
   A label from this tier is the answer before the general hand rules (a sieve inside an Euler problem file is that
   problem): the tiers are separate predicates, so no clause order decides. has_rel/2 (ta_signature.pl) matches a
   relation with names abstracted away.
*/
:- prolog_load_context(directory, Dir), directory_file_path(Dir, 'ta_signature.pl', T), load_files(T, []).
:- discontiguous hand_specific/2.
:- dynamic hand_specific/2.
