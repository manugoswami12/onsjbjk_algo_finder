#!/usr/bin/env python3
"""AP9 deterministic Semgrep-OCaml-AST → Prolog reference rule compiler.

Generates EXACT, scoped, alpha-aware structural templates. Algorithm names are
USER-SUPPLIED labels, never inferred. The compiler does not use Python ast or
Semgrep patterns. Normalized projection is separate from exact typed AST facts.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import pathlib
import sys

from export_ast_facts import atom
from typed_ast_codec import JsonNumber, strict_load

REGIONS = ('body', 'for', 'while', 'if', 'assign')
VARIANTS = {'for': 'For', 'while': 'While', 'if': 'If', 'assign': 'Assign'}


@dataclass(frozen=True)
class Binding:
    name: str


def walk(tree, path=()):
    yield path, tree
    if isinstance(tree, dict):
        for k, v in tree.items():
            yield from walk(v, path + (k,))
    elif isinstance(tree, list):
        for i, v in enumerate(tree):
            yield from walk(v, path + (i,))


def functions(tree):
    """Return Semgrep DefStmt/FuncDef bodies without reading Python source."""
    for path, obj in walk(tree):
        if not isinstance(obj, dict) or 'DefStmt' not in obj or len(obj) != 1:
            continue
        pair = obj['DefStmt']
        if not isinstance(pair, list) or len(pair) < 2:
            continue
        try:
            entity, signature = pair[0], pair[1]['FuncDef']
            name = entity['name']['EN']['Id'][0][0]
            body = signature['fbody']['FBStmt']['Block']
            params = signature.get('fparams', [])
            if not isinstance(name, str) or not isinstance(body, list):
                continue
        except (KeyError, TypeError, IndexError, ValueError):
            continue
        yield path, name, params, body


def walk_scoped(tree, path=()):
    """Walk current function only; nested DefStmt owns a separate scope."""
    yield path, tree
    if isinstance(tree, dict):
        for k, v in tree.items():
            if k == 'DefStmt':
                continue
            yield from walk_scoped(v, path + (k,))
    elif isinstance(tree, list):
        for i, v in enumerate(tree):
            yield from walk_scoped(v, path + (i,))


def declared_names(params, body):
    """Conservative local binder collector, no global/builtin wildcarding."""
    names = set()
    for param in params:
        try:
            val = param['Param']['pname']['some'][0]
            if isinstance(val, str): names.add(val)
        except (KeyError, TypeError, IndexError):
            pass
    for _, node in walk_scoped(body):
        if not isinstance(node, dict):
            continue
        if 'PatId' in node:
            try:
                name = node['PatId'][0][0]
                if isinstance(name, str): names.add(name)
            except (KeyError, TypeError, IndexError):
                pass
        if 'Assign' in node:
            try:
                lhs = node['Assign'][0]
                # Simple local assign; don't treat attribute / array write as binder.
                name = lhs['N']['Id'][0][0]
                if isinstance(name, str): names.add(name)
            except (KeyError, TypeError, IndexError):
                pass
    return names


def select_regions(body, kind):
    if kind == 'body':
        yield ('body',), {'Block': body}
        return
    for path, node in walk({'Block': body}):
        if (isinstance(node, dict) and len(node) == 1
                and VARIANTS[kind] in node
                and 'DefStmt' not in path):
            yield path, node


def project(node, binders, *, field=None):
    """Drop only OCaml binder metadata. Keep operators, globals, literals."""
    if isinstance(node, dict):
        if len(node) == 1 and ('Id' in node or 'PatId' in node):
            tag = 'Id' if 'Id' in node else 'PatId'
            pair = node[tag]
            if isinstance(pair, list) and pair and isinstance(pair[0], list):
                return {tag: [project(pair[0], binders, field=tag)]}
        out = {}
        for key, value in node.items():
            if key in ('id_info', 'pinfo'):
                continue
            out[key] = project(value, binders, field=key)
        return out
    if isinstance(node, list):
        return [project(value, binders, field=('identifier' if field in ('Id', 'PatId') and i == 0
                                                    else field))
                for i, value in enumerate(node)]
    if isinstance(node, str) and not isinstance(node, JsonNumber):
        if field == 'identifier' and node in binders:
            return Binding(node)
        if field == 'pname_name' and node in binders:
            return Binding(node)
    return node


def project_region(region, binders):
    """Replace Param pname when reference selection is extended to signatures."""
    # Function body / statements carry Id / PatId tokens. These are the only
    # supported bound-name encodings for the current AP9 structural contract.
    return project(region, binders)


def quote_term(value, reference=False, slots=None):
    """Create an inert Prolog term; never splice source code as syntax."""
    if slots is None: slots = {}
    if isinstance(value, Binding):
        if reference:
            var = slots.setdefault(value.name, f'V{len(slots)}')
            return f'binding({var})'
        return f'binding({atom(value.name)})'
    if isinstance(value, dict):
        return 'obj([' + ','.join(f'kv({atom(k)},{quote_term(v,reference,slots)})'
                                  for k, v in value.items()) + '])'
    if isinstance(value, list):
        return 'arr([' + ','.join(quote_term(x, reference, slots) for x in value) + '])'
    if isinstance(value, JsonNumber): return f'number({atom(str(value))})'
    if value is None: return 'null'
    if value is True: return 'boolean(true)'
    if value is False: return 'boolean(false)'
    if isinstance(value, str): return f'string({atom(value)})'
    if type(value) in (int, float): return f'number({atom(str(value))})'
    raise TypeError(f'unsupported Prolog term leaf: {type(value)}')


def path_string(path):
    return '/'.join(str(x) for x in path)


def references(tree, label, function, kind, ordinal):
    hits = [item for item in functions(tree) if item[1] == function]
    if len(hits) != 1:
        raise ValueError(f'expected one function {function!r}, found {len(hits)}')
    fpath, fname, params, body = hits[0]
    regions = list(select_regions(body, kind))
    if not 0 <= ordinal < len(regions):
        raise ValueError(f'region ordinal {ordinal} out of range (count={len(regions)})')
    region_path, node = regions[ordinal]
    slots = {}
    term = quote_term(project_region(node, declared_names(params, body)), True, slots)
    mappings = ','.join(f'slot({atom(name)},{var})' for name, var in slots.items())
    clause = f'reference_pattern({atom(label)},{atom(kind)},{term},[{mappings}]).'
    return clause, {'label': label, 'reference_function': function, 'region': kind,
                    'ordinal': ordinal, 'reference_region_path': path_string(fpath+region_path),
                    'local_slots': list(slots)}


def candidates(tree, kind):
    for fpath, fname, params, body in functions(tree):
        binders = declared_names(params, body)
        for region_path, node in select_regions(body, kind):
            term = quote_term(project_region(node, binders))
            yield f'candidate_pattern({atom(fname)},{atom(path_string(fpath+region_path))},{atom(kind)},{term}).'


def compile_reference(input_json, label, function, kind, ordinal, out):
    tree = strict_load(input_json)
    clause, metadata = references(tree, label, function, kind, ordinal)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('% AP9 GENERATED from reference OCaml AST. Label is user-supplied.\n'
                   + clause + '\n', encoding='utf8')
    return metadata


def compile_candidates(input_json, kinds, out):
    tree = strict_load(input_json)
    clauses = ['% AP9 GENERATED candidate OCaml AST projections. No labels.']
    for kind in kinds:
        clauses.extend(candidates(tree, kind))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(clauses) + '\n', encoding='utf8')
    return len(clauses) - 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('reference', 'candidates'))
    p.add_argument('input_json', type=pathlib.Path)
    p.add_argument('out_pl', type=pathlib.Path)
    p.add_argument('--label')
    p.add_argument('--function')
    p.add_argument('--region', choices=REGIONS, default='body')
    p.add_argument('--ordinal', type=int, default=0)
    args = p.parse_args()
    try:
        if args.mode == 'reference':
            if not args.label or not args.function:
                p.error('reference mode requires --label and --function')
            info = compile_reference(args.input_json, args.label, args.function,
                                     args.region, args.ordinal, args.out_pl)
            print('GENERATED_REFERENCE:', info)
        else:
            count = compile_candidates(args.input_json, REGIONS, args.out_pl)
            print(f'GENERATED_CANDIDATES: {count}')
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f'ERROR: generation failed: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
