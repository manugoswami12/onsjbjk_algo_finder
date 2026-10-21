"""Common Lisp -> ECL-generated C -> plain C for the existing C algorithm identifier.

ECL (`compile-file ... :c-file`) compiles the Lisp file to C; nothing is run. Its C calls the ECL
runtime and expresses every Lisp loop with labels and goto. This filter
  1. maps ECL runtime calls and boxing macros to plain C operators (table below),
  2. removes runtime boilerplate (environment, multiple-value counters, stack checks),
  3. replaces each function's labels/gotos by a dispatcher loop (Boehm-Jacopini):
       long state = 0; while (1) { if (state == 0) {..; state = 1; continue;} if (state == 1) {..} }
     (ECL's C contains no loops of its own, so `continue` always means "jump").
Anything else the identifier cannot run stays as an unknown call -> the function is not run (UNKNOWN).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

BINARY = {'ecl_plus': '+', 'ecl_minus': '-', 'ecl_times': '*', 'ecl_lower': '<', 'ecl_lowereq': '<=',
          'ecl_greater': '>', 'ecl_greatereq': '>=', 'ecl_number_equalp': '==', 'ecl_eql': '==',
          'ecl_equal': '==', 'ecl_truncate2': '/', 'ecl_divide': '/'}
UNARY = {'ecl_make_fixnum': '{0}', 'ecl_fixnum': '{0}', 'ecl_make_integer': '{0}', 'ecl_to_fixnum': '{0}',
         'ecl_one_plus': '({0} + 1)', 'ecl_one_minus': '({0} - 1)', 'ecl_zerop': '({0} == 0)',
         'ecl_minusp': '({0} < 0)', 'ecl_plusp': '({0} > 0)', 'ecl_negate': '(-{0})', 'ecl_abs': 'abs({0})',
         'ecl_oddp': '({0} % 2 != 0)', 'ecl_evenp': '({0} % 2 == 0)', 'ecl_length': 'len({0})',
         'ECL_FIXNUMP': '1', 'ecl_make_bool': '{0}'}
BOILER = re.compile(r'^\s*(const cl_env_ptr cl_env_copy = ecl_process_env\(\);|ecl_cs_check\(.*\);|'
                    r'cl_env_copy->nvalues = \d+;|cl_object env0 = ECL_NIL;)\s*$')


RUTILS_SHIM = '(defmacro rtl::with (bindings &body body) `(let* ,bindings ,@body))\n'


def top_forms(text: str):
    """Top-level forms of a Lisp source as text (strings, comments and #| |# respected)."""
    forms, depth, start, i, n = [], 0, None, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == ';':
            i = text.find('\n', i) if '\n' in text[i:] else n
            continue
        if text.startswith('#|', i):
            j = text.find('|#', i)
            i = n if j < 0 else j + 2
            continue
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif text.startswith('#\\', i):
            i += 2
        elif ch == '(':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ')' and depth:
            depth -= 1
            if depth == 0:
                forms.append(text[start:i + 1])
        i += 1
    return forms


def _compile(src_text: str, td: Path, tag: str, timeout: int) -> str:
    src, out = td / f'{tag}.lisp', td / f'{tag}.c'
    src.write_text(src_text, encoding='utf-8')
    form = (f'(progn (compile-file "{src}" :c-file "{out}" :h-file "{td}/{tag}.h" :data-file "{td}/{tag}.data" '
            f':output-file "{td}/{tag}.o" :system-p t) (quit))')
    subprocess.run(['ecl', '--norc', '-eval', form], capture_output=True, text=True, timeout=timeout,
                   stdin=subprocess.DEVNULL, check=False)
    return out.read_text(encoding='utf-8', errors='replace') if out.exists() else ''


def ecl_c(path: Path, timeout=120) -> str:
    """ECL C of every defun; each defun is compiled on its own, so a form ECL rejects loses only itself."""
    from lisp_sbcl_pnf import readable_source     # unloaded packages (rtl:) must not stop the reader
    text, pkgs = readable_source(path.read_text(encoding='utf-8', errors='replace'))
    prelude = ''.join(f'(eval-when (:compile-toplevel :load-toplevel :execute) (unless (find-package "{p.upper()}") '
                      f'(make-package "{p.upper()}" :use (list "CL"))))\n' for p in pkgs)
    if 'rtl' in pkgs:
        prelude += RUTILS_SHIM
    defuns = [f for f in top_forms(text) if re.match(r'\(defun\s', f, re.I)]
    with tempfile.TemporaryDirectory(prefix='v02_ecl_') as td:
        return '\n'.join(_compile(prelude + f + '\n', Path(td), f'f{k}', timeout) for k, f in enumerate(defuns))


def _args(text, start):
    """Split the argument list starting after '(' at text[start-1]; returns (args, end index)."""
    depth, cur, args, i = 0, '', [], start
    while i < len(text):
        ch = text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            if depth == 0:
                args.append(cur.strip())
                return args, i + 1
            depth -= 1
        elif ch == ',' and depth == 0:
            args.append(cur.strip())
            cur = ''
            i += 1
            continue
        cur += ch
        i += 1
    raise ValueError('unbalanced call')


CALL = re.compile(r'\b(' + '|'.join(sorted(BINARY | UNARY, key=len, reverse=True)) + r')\s*\(')


def rewrite_calls(text: str) -> str:
    """Innermost-first rewriting of the table's calls (repeat until none is left)."""
    for _ in range(200):
        m = None
        for m in CALL.finditer(text):  # noqa: B007 -- the last match: no table call inside its args
            pass
        if m is None:
            return text
        args, end = _args(text, m.end())
        name = m.group(1)
        if name in BINARY and len(args) == 2:
            new = f'(({args[0]}) {BINARY[name]} ({args[1]}))'
        elif name in UNARY and len(args) == 1:
            new = UNARY[name].format(f'({args[0]})')
        else:
            new = f'ecl_unsupported_{name}({", ".join(args)})'
        text = text[:m.start()] + new + text[end:]
    return text


def plain_values(text: str) -> str:
    # (ecl_floor2(a,b), cl_env_copy->values[1]) is the remainder (second value of floor)
    text = re.sub(r'\(ecl_floor2\(([^(),]+),([^(),]+)\),cl_env_copy->values\[1\]\)', r'((\1) % (\2))', text)
    text = re.sub(r'ecl_floor2\(([^(),]+),([^(),]+)\)', r'((\1) / (\2))', text)
    return text


def dispatcher(body: str) -> str:
    """Labels/gotos of one function body -> a dispatcher loop over the labelled segments."""
    lab = re.compile(r'^\s*(TTL|L\d+):;?\s*$', re.M)
    labels = lab.findall(body)
    if not labels:
        return body
    first = lab.search(body)
    head, rest = body[:first.start()], body[first.start():]
    # the labelled block ends with the closing brace that matches the block opened before TTL
    parts = lab.split(rest)                      # ['', 'TTL', seg, 'L2', seg, ...]
    segs = list(zip(parts[1::2], parts[2::2]))
    ids = {name: i for i, (name, _) in enumerate(segs)}
    tail = ''
    last_name, last_seg = segs[-1]
    depth = 0                                     # cut what closes the enclosing block off the last segment
    for k, ch in enumerate(last_seg):
        depth += ch == '{'
        depth -= ch == '}'
        if depth < 0:
            last_seg, tail = last_seg[:k], last_seg[k:]
            break
    segs[-1] = (last_name, last_seg)
    out = [head, 'long ecl_state = 0;\nwhile (1) {\n']
    for i, (_, seg) in enumerate(segs):
        seg = re.sub(r'goto\s+(TTL|L\d+)\s*;', lambda m: f'{{ ecl_state = {ids[m.group(1)]}; continue; }}', seg)
        nxt = f'ecl_state = {i + 1}; continue;' if i + 1 < len(segs) else 'break;'
        out.append(f'if (ecl_state == {i}) {{\n{seg}\n{nxt}\n}}\n')
    out.append('}\n')
    return ''.join(out) + tail


def functions(c_text: str):
    """Yield (start, end) of each `static cl_object Lnname(...) { ... }` definition."""
    for m in re.finditer(r'^static cl_object (L\d+[\w]*)\(([^)]*)\)\s*\{', c_text, re.M):
        depth, i = 1, m.end()
        while depth and i < len(c_text):
            depth += c_text[i] == '{'
            depth -= c_text[i] == '}'
            i += 1
        yield m, i


def plain_c(c_text: str) -> str:
    """ECL C -> plain C: only the compiled Lisp functions, renamed back to their Lisp names."""
    names = {m.group(1): re.sub(r'^L\d+', '', m.group(1)) for m, _ in functions(c_text)}
    out = []
    for m, end in functions(c_text):
        name, params = names[m.group(1)], m.group(2).replace('cl_object', 'long')
        body = c_text[m.end():end - 1]
        body = '\n'.join(line for line in body.splitlines() if not BOILER.match(line))
        body = plain_values(rewrite_calls(body))
        body = re.sub(r'\bcl_object\b', 'long', body).replace('ECL_NIL', '0').replace('ECL_T', '1')
        # `long T0, T1;` -> initialised (the identifier reads an uninitialised declaration as a use)
        body = re.sub(r'\blong\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*;',
                      lambda d: 'long ' + ', '.join(f'{v.strip()} = 0' for v in d.group(1).split(',')) + ';', body)
        body = dispatcher(body)
        for old, new in names.items():
            body = re.sub(rf'\b{old}\b', new, body)
        out.append(f'long {name}({params}) {{\n{body}\n}}\n')
    return '\n'.join(out)


def lisp_to_plain_c(path: Path) -> str:
    return plain_c(ecl_c(path))
