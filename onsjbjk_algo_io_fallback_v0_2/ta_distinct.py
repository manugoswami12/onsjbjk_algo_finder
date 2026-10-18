"""Helper for writing file rules by hand (doc 04 section 17.5): which components of a label's files no other label of
TheAlgorithms/Python has.

usage: python ta_distinct.py CORPUS --index            abstracted relations of every corpus file -> benchmark/ta_signatures.json
       python ta_distinct.py CORPUS LABEL [LABEL ...]   the label's components found in no other label (smallest first)
       python ta_distinct.py CORPUS --propose LABEL ...  candidate hand_specific/2 clauses covering every file of the label
       python ta_distinct.py CORPUS --write              the proposed section of ta_file_rules.pl for the labels in
                                                         benchmark/ta_file_rule_labels.json
A component is a statement's relation with its variable names and the file's own function names abstracted away
(prolog/ta_signature.pl), so it is the same component in every spelling. The rule is then written by hand in
prolog/ta_file_rules.pl from one or two of them.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import learn_facts
import ta_corpus
from ta_corpus import ROOT

PROGRAM = ROOT / 'prolog' / 'ta_signature.pl'
INDEX = ROOT / 'benchmark' / 'ta_signatures.json'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError)


def signatures(path: Path) -> list[str]:
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return []
    return sorted({line.split('|', 1)[1] for line in learn_facts.swipl_facts('signature_main', PROGRAM, kind, text)
                   if line.startswith('SIG|')})


def index(corpus: Path, workers: int = 4):
    labels = ta_corpus.files(corpus)

    def one(rel):
        try:
            return rel, signatures(corpus / rel)
        except ERRORS:
            return rel, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = dict(pool.map(one, sorted(labels)))
    INDEX.write_text(json.dumps(out, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{len(out)} files -> {INDEX}')


def distinct(corpus: Path, label: str, top: int = 12) -> list[tuple[str, list[str]]]:
    """[(component, files of the label having it)] for the components no file of another label has."""
    labels = ta_corpus.files(corpus)
    sigs = json.loads(INDEX.read_text(encoding='utf-8'))
    owners = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            owners[s].add(labels[rel])
    mine = [rel for rel, lab in labels.items() if lab == label]
    found = defaultdict(list)
    for rel in mine:
        for s in sigs.get(rel, []):
            if owners[s] == {label}:
                found[s].append(rel)
    return sorted(found.items(), key=lambda kv: (-len(kv[1]), len(kv[0])))[:top]


TRIVIAL = ('var(v)', 'var(v)-other(string)', 'var(v)-var(v)', 'var(v)-int(0)', 'var(v)-int(1)', 'var(v)-list([])')


NOISE = ('call(input', 'call(print', 'call(format', 'call(strip,[call(input', 'call(time', 'call(perf_counter',
         'call(timeit', 'call(urlopen', 'call(get,[var(requests)', 'call(open,', 'call(write', 'call(read',
         'call(assert', 'call(testmod', 'call(exit', 'call(sleep', 'call(seed')


def structural(s: str) -> bool:
    """A component worth naming: an operation, a call or an element, not a bare constant assignment."""
    return s not in TRIVIAL and any(k in s for k in ('op(', 'call(', 'elem(', 'map(', 'filter(', 'concat(', 'cons('))


VALIDATION = re.compile(r"^op\((lt|le|gt|ge|eq|ne),\[(var\(p\(\d+\)\)|int\(-?\d+\)),(var\(p\(\d+\)\)|int\(-?\d+\))\]\)$")


def validation(s: str) -> bool:
    """An input check, not the algorithm: isinstance, or a parameter compared with a constant (n < 0, n >= 3)."""
    return 'isinstance' in s or bool(VALIDATION.match(s))


def rank(s: str) -> tuple:
    """Preference among a label's own components: the logic on its inputs (a parameter in it), not reading input,
    printing, timing or checking the input; an operation, call or element; a mid-size term."""
    return (not any(n in s for n in NOISE), not validation(s), structural(s), 'var(p(' in s, -abs(len(s) - 70))


def cover(corpus: Path, label: str):
    """[(component, ...)] whose union covers every file of the label: single components owned by the label first
    (structural ones preferred), else a pair of components that together occur only in the label's files, else a
    component with, for each other file having it, a component that file has and the label never has
    (('not', c): \\+ has_rel(_, c), anywhere in the file)."""
    labels = ta_corpus.files(corpus)
    sigs = json.loads(INDEX.read_text(encoding='utf-8'))
    owners = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            owners[s].add(labels[rel])
    files_of = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            files_of[s].add(rel)
    mine = [rel for rel, lab in labels.items() if lab == label]
    chosen, left = [], set(mine)
    while left:
        best = None
        for rel in sorted(left):
            for s in sigs.get(rel, []):
                if owners[s] == {label}:
                    key = (len(files_of[s] & left),) + rank(s)
                    if best is None or key > best[0]:
                        best = (key, (s,), files_of[s] & left)
        if best is None:                              # no single component: a pair present only in the label's files
            rel = min(left)
            ss = sorted((x for x in sigs.get(rel, []) if x not in TRIVIAL), key=rank, reverse=True)[:40]
            for i, a in enumerate(ss):
                for b in ss[i + 1:]:
                    both = files_of[a] & files_of[b]
                    if {labels[r] for r in both} == {label}:
                        key = (len(both & left), min(rank(a), rank(b)))
                        if best is None or key > best[0]:
                            best = (key, (a, b), both & left)
        if best is None:                              # a component and, for each other file having it, one it lacks
            rel = min(left)
            ours = set().union(*(set(sigs.get(r, [])) for r in mine))
            for a in sorted(sigs.get(rel, []), key=rank, reverse=True)[:40]:
                nots = []
                for other in sorted(files_of[a] - set(mine)):
                    extra = sorted((set(sigs[other]) - ours), key=rank, reverse=True)
                    if not extra:
                        break
                    if not any(n in sigs[other] for n in nots):
                        nots.append(extra[0])
                else:
                    if nots:
                        best = (None, (a,) + tuple(('not', n) for n in nots), files_of[a] & left)
                        break
        if best is None:
            return chosen, sorted(left)                # identical to another label's file in every component
        chosen.append(best[1])
        left -= best[2]
    return chosen, []


def propose(corpus: Path, label: str) -> str:
    """Candidate clauses of hand_specific/2 for the label (to be reviewed before they go in ta_file_rules.pl)."""
    chosen, left = cover(corpus, label)
    out = [f"% {label}"]
    for comps in chosen:
        body = ', '.join(f'\\+ file_has({c[1]})' if isinstance(c, tuple) else f'file_has({c})' for c in comps)
        out.append(f"hand_specific(_, '{label}') :- {body}.")
    if left:
        out.append(f"% no component of {', '.join(left)} separates it from another label (identical logic)")
    return '\n'.join(out)


RULES = ROOT / 'prolog' / 'ta_file_rules.pl'
RULE_LABELS = ROOT / 'benchmark' / 'ta_file_rule_labels.json'
MARK = '% ----- generated by ta_distinct.py --write (doc 04 section 17.5) -----'


def write_rules(corpus: Path):
    """Regenerate the proposed section of ta_file_rules.pl for the labels of benchmark/ta_file_rule_labels.json,
    grouped by folder; the hand-written part above the mark is kept."""
    labels = ta_corpus.files(corpus)
    first = {}
    for rel, lab in sorted(labels.items()):
        first.setdefault(lab, rel.split('/')[0])
    todo = json.loads(RULE_LABELS.read_text(encoding='utf-8'))
    by = defaultdict(list)
    for lab in todo:
        by[first[lab]].append(lab)
    out = [MARK, ("% the label's own components (logic on its inputs preferred over input reading, printing, tests and "
                  "input checks), reviewed"), '% per folder; T1/T2 checked by eval_ta.py --rehand and --status']
    for folder in sorted(by):
        out.append(f'% ===== {folder}')
        out += [propose(corpus, lab) for lab in sorted(by[folder])]
    head = RULES.read_text(encoding='utf-8').split(MARK)[0].rstrip('\n')
    RULES.write_text(head + '\n\n' + '\n'.join(out) + '\n', encoding='utf-8')
    print(f'{len(todo)} labels -> {RULES}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('labels', nargs='*')
    p.add_argument('--index', action='store_true')
    p.add_argument('--propose', action='store_true', help='candidate file-rule clauses for the labels')
    p.add_argument('--write', action='store_true', help='regenerate the proposed section of ta_file_rules.pl')
    a = p.parse_args()
    if a.index:
        index(a.corpus)
    if a.write:
        return write_rules(a.corpus)
    if a.propose:
        for lab in a.labels:
            print(propose(a.corpus, lab))
        return
    for lab in a.labels:
        print(f'== {lab}')
        for s, rels in distinct(a.corpus, lab):
            print(f'  [{len(rels)}] {s[:220]}')


if __name__ == '__main__':
    main()
