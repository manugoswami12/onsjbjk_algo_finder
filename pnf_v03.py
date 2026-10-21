"""v0.3 runner of the Prolog normal form (doc 04 section 18.4), kept separate from the pipeline: AP13's PNF lowerer
(polyglot_logic/tools/to_prolog.py) and interpreter (polyglot_logic/prolog/interp.pl) extended, not edited.
  PNFv03           PNFLowerer subclass, for Python (other languages keep their own route): `lambda` -> lambda(Params, Body); a generator as a call's only argument
                   (any(x % d == 0 for d in ...)) -> one comprehension argument, not an expression plus
                   other(for_in_clause); module-level `name = value` -> pnf_const(Name, Value)
  run_functions    io_trace.run_functions with PNFv03 and prolog/run_main_v03.pl (interp.pl plus closures, function
                   values, module constants and more library relations, prolog/interp_v03.pl)
The source still never runs: only its Prolog normal form does. The pipeline uses AP13's io_trace unchanged; only the
separate tools (ta_classes.runs(..., v03=True), tools_manual/decide_new_or_known.py --v03) use this runner.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import compare_learners

compare_learners._ap13()                                   # AP13's tools directory on the path
import io_trace
from fact_io import term
from lower_imperative import named, text
from parse_source import parse
from to_prolog import PNFLowerer, render

RUN_MAIN = Path(__file__).resolve().parent / 'prolog' / 'run_main_v03.pl'


class PNFv03(PNFLowerer):
    def expr(self, node):
        if node is not None and node.type == 'lambda':
            ps = node.child_by_field_name('parameters')
            names = [text(c.child_by_field_name('name') or c) for c in named(ps)] if ps is not None else []
            return ('lambda', names, self.expr(node.child_by_field_name('body')))
        out = super().expr(node)
        if node is not None and node.type == 'call' and isinstance(out, tuple) and out and out[0] == 'call':
            args = node.child_by_field_name('arguments')
            if args is not None and args.type == 'generator_expression':
                return ('call', out[1], [self.comp(args)])
        return out


def constants(funs) -> list[tuple[str, object]]:
    """[(name, value expression)] of the module-level `name = value` statements (the <toplevel> pseudo-function)."""
    out = []
    for name, _, body in funs:
        if name == '<toplevel>' and body and body[0] == 'seq':
            for st in body[1]:
                if isinstance(st, tuple) and len(st) == 3 and st[0] == 'assign' and isinstance(st[1], tuple) \
                        and st[1][0] == 'var':
                    out.append((st[1][1], st[2]))
    return out


def normal_form(path: Path):
    if path.suffix != '.py':                                # other languages: their own (installed) route
        return io_trace.normal_form(path) + ([],)
    lang, _, root = parse(path)
    if root is None:
        return io_trace.normal_form(path) + ([],)
    funs = PNFv03(lang).run(root)
    return lang, funs, constants(funs)


def run_functions(path: Path, timeout=120):
    """io_trace.run_functions with the v0.3 lowerer and interpreter (same result format)."""
    lang, funs, consts = normal_form(path)
    if lang == 'prolog':
        return io_trace.run_native_prolog(path, timeout)
    if not funs:
        return {}
    pnf = [f"pnf_lang({term(lang)})."] + \
          [f"pnf_fun({term(n)},{term(list(ps))},{render(b)})." for n, ps, b in funs] + \
          [f"pnf_const({term(n)},{render(v)})." for n, v in consts]
    info, jobs = {}, []
    for name, params, body in funs:
        ks = io_trace.kinds(params, body)
        sig = io_trace.logical(ks)
        inputs = io_trace.battery(sig)
        info[name] = {'kinds': ks, 'sig': sig, 'inputs': inputs, 'runs': [], 'unsupported': io_trace.has_unsupported(body)}
        for x in inputs:
            jobs.append((len(jobs), name, io_trace.concrete(ks, x)))
    if not jobs:
        return info
    with tempfile.TemporaryDirectory(prefix='v03_pnf_') as td:
        pf, jf = Path(td) / 'pnf.pl', Path(td) / 'jobs.pl'
        pf.write_text('\n'.join(pnf) + '\n', encoding='utf-8')
        jf.write_text(''.join(f"job({i},{term(n)},{io_trace.prolog_value(a)}).\n" for i, n, a in jobs), encoding='utf-8')
        lines = io_trace.swipl('run_main', [RUN_MAIN], [str(pf), str(jf)], timeout=timeout)
    by_id = {}
    for line in lines:
        m = io_trace._RES.match(line)
        if m:
            by_id[int(m.group(1))] = (m.group(2), m.group(3))
    for i, name, _ in jobs:
        status, rest = by_id.get(i, ('err', 'no result'))
        if status == 'ok' and rest.lstrip().startswith(('closure(', 'fun(', 'op_fun(')):
            status, rest = 'err', 'returns a function'     # a curried function computed no value yet
        if status == 'ok':
            result, finals, h, nt, nw = io_trace.split_ok(rest)
            if result == 'false' and int(nw) > 0:
                result = 'none'
            info[name]['runs'].append((True, io_trace.effective(result, finals, info[name]['kinds']),
                                       h if int(nt) > 0 else None))
        else:
            info[name]['runs'].append((False, rest, None))
    return info


if __name__ == '__main__':
    for n, d in run_functions(Path(sys.argv[1])).items():
        print(n, d['sig'], [r[:2] for r in d['runs']][:12])
