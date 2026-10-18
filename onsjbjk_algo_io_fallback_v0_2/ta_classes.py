"""Class relations (doc 04 section 18): which class of algorithm a program computes, by its input->output relation.

A class is what is computed (sorting, search, gcd, ...), not how. Each function's Prolog normal form is run on AP13's
fixed battery (io_trace: the source never runs) and prolog/class_specs.pl checks the class relations on every
(input, output) pair, in the mode each needs (user: sum(2,3,X)): the output computed from the input, or checked
where several outputs are right. A program that runs and satisfies no class relation is a new class.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners
import learn_facts
from ta_corpus import ROOT

PROGRAM = ROOT / 'prolog' / 'class_specs.pl'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError, RecursionError, KeyError, IndexError, TypeError,
          AttributeError, StopIteration, SyntaxError)


def quote(text: str) -> str:
    return "'" + text.replace('\\', '\\\\').replace("'", "\\'") + "'"


def runs(path: Path) -> dict[str, tuple[list, list[tuple[list, str]]]]:
    """{function: (logical signature, [(inputs, output text)])} of the runs that succeeded."""
    compare_learners._ap13()
    import io_trace
    try:
        info = io_trace.run_functions(path)
    except ERRORS:
        return {}
    out = {}
    for name, d in info.items():
        if not d.get('runs') or d.get('unsupported'):
            continue
        ins = io_trace.battery(tuple(d['sig']))
        ok = [(i, r[1]) for i, r in zip(ins, d['runs']) if r[0]]
        if ok:
            out[name] = (list(d['sig']), ok)
    return out


def classes(path: Path, rs: dict | None = None) -> dict[str, set[str]]:
    """{function: classes whose relation every run satisfies}; rs: the file's runs when the caller has them."""
    rs = runs(path) if rs is None else rs
    if not rs:
        return {}
    lines = [':- discontiguous run/4.']
    names = {}
    for k, (name, (sig, ok)) in enumerate(sorted(rs.items())):
        fid = f'f{k}'
        names[fid] = name
        sig_t = '[' + ','.join(sig) + ']'
        for ins, outp in ok:
            lines.append(f"run({fid},{sig_t},{repr(list(ins)).replace(' ', '')},{quote(outp)}).")
    with tempfile.TemporaryDirectory(prefix='v02_cls_') as td:
        f = Path(td) / 'runs.pl'
        f.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        try:
            res = learn_facts.env_run.swipl('class_main', [PROGRAM], [str(f)], timeout=120)
        except ERRORS:
            return {}
    out: dict[str, set[str]] = {}
    for line in res:
        if line.startswith('CLASS|'):
            _, fid, c = line.split('|')
            out.setdefault(names[fid], set()).add(c)
    return out


def runnable(path: Path, rs: dict | None = None) -> bool:
    """Some function of the file runs on the battery with an output that depends on its input."""
    rs = runs(path) if rs is None else rs
    return any(len({o for _, o in ok}) > 1 for _, ok in rs.values())
