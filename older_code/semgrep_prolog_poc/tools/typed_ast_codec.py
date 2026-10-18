#!/usr/bin/env python3
"""AP9 opt-in typed, reversible JSON-value ↔ Prolog fact codec.

No changes to the AP8 exported facts. The supplemental dialect is explicitly
separate. JSON numbers retain their original decimal/exponent lexeme; JSON
string-escape spellings and whitespace are NOT semantically relevant JSON data.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sys

from export_ast_facts import flatten


class JsonNumber(str):
    """A JSON numeric token, kept distinct from an ordinary JSON string."""


def strict_loads(text: str):
    def obj(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON object key: {key!r}')
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f'non-standard JSON constant: {value}')

    return json.loads(text, parse_int=JsonNumber, parse_float=JsonNumber,
                      parse_constant=reject_constant, object_pairs_hook=obj)


def strict_load(path: pathlib.Path):
    return strict_loads(path.read_text(encoding='utf-8-sig'))


def b64(text: str) -> str:
    return base64.b64encode(text.encode('utf-8', errors='surrogatepass')).decode('ascii')


def unb64(encoded: str) -> str:
    return base64.b64decode(encoded, validate=True).decode('utf-8', errors='surrogatepass')


def typed_lines(tree, max_nodes=100000):
    """Append typed metadata keyed by the UNCHANGED legacy preorder node IDs."""
    base = flatten(tree, max_nodes=max_nodes)
    types, keys, values = [], [], []
    stack = [tree]
    count = 0
    while stack:
        node = stack.pop()
        count += 1
        if count > max_nodes:
            raise ValueError('typed AST exceeds node limit')
        ident = f'n{count:07d}'
        if isinstance(node, dict):
            types.append(f"ast_json_type('{ident}', object).")
            for index, key in enumerate(node):
                keys.append(f"ast_json_key64('{ident}', {index}, '{b64(key)}').")
            stack.extend(reversed(list(node.values())))
        elif isinstance(node, list):
            types.append(f"ast_json_type('{ident}', array).")
            stack.extend(reversed(node))
        else:
            if node is None:
                kind, payload = 'null', 'null'
            elif node is True or node is False:
                kind, payload = 'boolean', 'true' if node else 'false'
            elif isinstance(node, JsonNumber):
                kind, payload = 'number', str(node)
            elif isinstance(node, str):
                kind, payload = 'string', node
            elif type(node) in (int, float):
                # Only for programmatic callers, CLI uses strict_load().
                if isinstance(node, float) and not __import__('math').isfinite(node):
                    raise ValueError('non-finite JSON number')
                kind, payload = 'number', str(node)
            else:
                raise ValueError(f'not a JSON scalar: {type(node)}')
            types.append(f"ast_json_type('{ident}', {kind}).")
            values.append(f"ast_json_scalar64('{ident}', '{b64(payload)}').")
    return base + ['% AP9 typed JSON-value extension, no AST rewriting.'] + types + keys + values


EDGE = re.compile(r"^ast_edge\('(n\d+)', '(n\d+)', .+\)\.$")
TYPE = re.compile(r"^ast_json_type\('(n\d+)', (object|array|string|number|boolean|null)\)\.$")
KEY = re.compile(r"^ast_json_key64\('(n\d+)', (\d+), '([A-Za-z0-9+/=]*)'\)\.$")
VALUE = re.compile(r"^ast_json_scalar64\('(n\d+)', '([A-Za-z0-9+/=]*)'\)\.$")


def decode_typed(lines: list[str]):
    """Reconstruct from generated facts, never evaluate foreign Prolog text.

    Typed codec uses the existing ast_edge/3 node connections with ordering of
    grouped preorder edges. Keys are taken from explicit ordered metadata.
    """
    children, kinds, fields, vals = {}, {}, {}, {}
    for line in lines:
        if m := EDGE.fullmatch(line):
            parent, child = m.groups()
            children.setdefault(parent, []).append(child)
        elif m := TYPE.fullmatch(line):
            ident, kind = m.groups()
            if ident in kinds: raise ValueError('duplicate node type')
            kinds[ident] = kind
        elif m := KEY.fullmatch(line):
            ident, ordinal, encoded = m.groups()
            fields.setdefault(ident, []).append((int(ordinal), unb64(encoded)))
        elif m := VALUE.fullmatch(line):
            ident, encoded = m.groups()
            if ident in vals: raise ValueError('duplicate scalar')
            vals[ident] = unb64(encoded)
    if not kinds or 'n0000001' not in kinds:
        raise ValueError('no typed root in facts')
    seen = set()
    def build(ident):
        if ident in seen: raise ValueError('cycle or shared node')
        seen.add(ident)
        kind = kinds[ident]
        sub = children.get(ident, [])
        if kind == 'object':
            names = sorted(fields.get(ident, []))
            if len(names) != len(sub) or [i for i, _ in names] != list(range(len(sub))):
                raise ValueError('object keys/edge counts disagree')
            return {key: build(child) for (_, key), child in zip(names, sub)}
        if kind == 'array':
            return [build(child) for child in sub]
        if sub or ident not in vals:
            raise ValueError('invalid scalar edge or missing value')
        s = vals[ident]
        if kind == 'string': return s
        if kind == 'number':
            if not re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', s):
                raise ValueError('invalid numeric token')
            return JsonNumber(s)
        if kind == 'boolean':
            if s not in ('true', 'false'): raise ValueError('invalid boolean token')
            return s == 'true'
        if kind == 'null':
            if s != 'null': raise ValueError('invalid null')
            return None
        raise ValueError('unknown node type')
    result = build('n0000001')
    if seen != set(kinds): raise ValueError('unreachable typed nodes')
    return result


def json_text(value) -> str:
    """Emit canonical JSON syntax while keeping original number lexemes."""
    if isinstance(value, JsonNumber): return str(value)
    if value is None: return 'null'
    if value is True: return 'true'
    if value is False: return 'false'
    if isinstance(value, str): return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list): return '[' + ','.join(json_text(x) for x in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=True) + ':' + json_text(v)
                              for k, v in value.items()) + '}'
    raise TypeError('unsupported JSON value')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input_json', type=pathlib.Path)
    ap.add_argument('out_typed_pl', type=pathlib.Path)
    ap.add_argument('--verify-roundtrip', action='store_true')
    args = ap.parse_args()
    try:
        tree = strict_load(args.input_json)
        lines = typed_lines(tree)
        if args.verify_roundtrip and json_text(tree) != json_text(decode_typed(lines)):
            raise ValueError('typed JSON roundtrip mismatch')
        args.out_typed_pl.parent.mkdir(parents=True, exist_ok=True)
        args.out_typed_pl.write_text('\n'.join(lines) + '\n', encoding='utf8')
        print(f'TYPED_JSON_PASS nodes={sum(x.startswith("ast_json_type(") for x in lines)} output={args.out_typed_pl}')
        return 0
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        print(f'ERROR: typed export: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
