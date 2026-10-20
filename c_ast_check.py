"""clang's own parser checks the structure facts of a C file (doc 04 section 19.11), as GHC's does for Haskell
(haskell_ast_check.py). clang -fsyntax-only -Xclang -ast-dump=json parses and type-checks the file (nothing compiled,
linked or run); its function definitions in the file itself, with their parameters in order, are the file's.
  check(facts, path)   with clang's parse free of errors: a function tree-sitter reports that clang does not define
                       is dropped; a function with fewer parameters than clang's (a function-pointer parameter
                       int (*cmp)(const void *, const void *) has no plain declarator name) takes clang's
                       parameters. Unchanged when clang reports an error (a GCC nested function, a missing header):
                       nothing to check against.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def clang_functions(path: Path, timeout=60):
    """{name: [parameter names]} of the function definitions in the file, or None (clang error or no AST)."""
    try:
        proc = subprocess.run(['clang', '-fsyntax-only', '-w', '-Xclang', '-ast-dump=json', str(path)],
                              capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        ast = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    if 'error:' in proc.stderr:
        return None
    out = {}
    for d in ast.get('inner', []):
        inner = d.get('inner', [])
        if d.get('kind') == 'FunctionDecl' and any(c.get('kind') == 'CompoundStmt' for c in inner) \
                and 'includedFrom' not in d.get('loc', {}):
            out[d['name']] = [c.get('name', '') for c in inner if c.get('kind') == 'ParmVarDecl']
    return out


FUNC = re.compile(r"^func\('([^']+)','((?:[^'\\]|\\.)*)'")
STMT = re.compile(r"^stmt\('([^']+)','([^']+)'")
PARAM = re.compile(r"^param\('([^']+)',")
IDS = re.compile(r"'([fs]\d+(?:_\w+)?)'")


def check(facts: str, path: Path) -> str:
    known = clang_functions(path)
    if known is None or not facts.strip():
        return facts
    lines = facts.splitlines()
    funcs = {m.group(1): m.group(2) for m in map(FUNC.match, lines) if m and m.group(2) != '<toplevel>'}
    dropped = {f for f, name in funcs.items() if name not in known}
    count = {}
    for m in map(PARAM.match, lines):
        if m:
            count[m.group(1)] = count.get(m.group(1), 0) + 1
    repaired = {f: known[name] for f, name in funcs.items()
                if f not in dropped and count.get(f, 0) < len(known[name]) and all(known[name])}
    if not dropped and not repaired:
        return facts
    dropped |= {m.group(1) for m in map(STMT.match, lines) if m and m.group(2) in dropped}
    out = []
    for line in lines:
        if set(IDS.findall(line)) & dropped:
            continue
        m = PARAM.match(line)
        if m and m.group(1) in repaired:
            continue
        out.append(line)
        m = FUNC.match(line)
        if m and m.group(1) in repaired:
            out += [f"param('{m.group(1)}',{k},'{p}')." for k, p in enumerate(repaired[m.group(1)])]
    return '\n'.join(out) + '\n'
