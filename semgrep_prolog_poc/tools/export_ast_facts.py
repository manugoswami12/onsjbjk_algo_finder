#!/usr/bin/env python3
"""Lossless-for-JSON-shape conversion of Semgrep AST JSON to Prolog tree facts.

Uses no Python AST, no Semgrep patterns, and no external Python libraries.
One-key JSON objects are OCaml variant constructors in Semgrep's AST dump.
Everything else (record fields, arrays, scalar nodes) is preserved explicitly.
The exporter does not itself label algorithms.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def atom(value: object) -> str:
    """Emit a safely quoted Prolog atom without treating input as Prolog code."""
    if not isinstance(value, str):
        value = str(value)
    escaped = (
        value.replace('\\', '\\\\')
        .replace("'", "\\'")
        .replace('\r', '\\r')
        .replace('\n', '\\n')
        .replace('\t', '\\t')
    )
    return "'" + escaped + "'"


def flatten(value: object, max_nodes: int = 100000) -> list[str]:
    # Group predicate clauses so SWI-Prolog does not emit thousands of
    # discontiguous-predicate warnings. Do not change preorder node IDs.
    groups: dict[str, list[str]] = {
        'ast_edge': [], 'ast_tag': [], 'ast_scalar': [],
    }
    stack: list[tuple[str | None, object, str]] = [(None, value, 'root')]
    seq = 0
    while stack:
        parent, current, field = stack.pop()
        seq += 1
        if seq > max_nodes:
            raise ValueError(f'AST exceeds safety limit ({max_nodes} nodes)')
        ident = f'n{seq:07d}'
        if parent is not None:
            groups['ast_edge'].append(f'ast_edge({atom(parent)}, {atom(ident)}, {atom(field)}).')
        if isinstance(current, dict):
            if len(current) == 1:
                k, v = next(iter(current.items()))
                groups['ast_tag'].append(f'ast_tag({atom(ident)}, {atom(k)}).')
                stack.append((ident, v, 'value'))
            else:
                groups['ast_tag'].append(f'ast_tag({atom(ident)}, {atom("record")}).')
                # Reversed for reproducible preorder traversal.
                for k, v in reversed(list(current.items())):
                    stack.append((ident, v, str(k)))
        elif isinstance(current, list):
            groups['ast_tag'].append(f'ast_tag({atom(ident)}, {atom("list")}).')
            for i in range(len(current) - 1, -1, -1):
                stack.append((ident, current[i], str(i)))
        else:
            groups['ast_tag'].append(f'ast_tag({atom(ident)}, {atom("scalar")}).')
            if current is None:
                txt = 'null'
            elif current is True:
                txt = 'true'
            elif current is False:
                txt = 'false'
            else:
                txt = str(current)
            groups['ast_scalar'].append(f'ast_scalar({atom(ident)}, {atom(txt)}).')
    lines = ["% Generated from Semgrep's OCaml generic-AST JSON dump.",
             "% All predicates are grouped; node IDs preserve preorder traversal."]
    for clauses in groups.values():
        lines.extend(clauses)
    lines.append(f'ast_node_count({seq}).')
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ast_json', type=pathlib.Path)
    parser.add_argument('out_facts', type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.ast_json.read_text(encoding='utf-8-sig'))
        lines = flatten(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f'ERROR: invalid/unreadable Semgrep AST JSON: {exc}', file=sys.stderr)
        return 2
    args.out_facts.parent.mkdir(parents=True, exist_ok=True)
    args.out_facts.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Exported {len(lines)} Prolog facts/lines into {args.out_facts}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
