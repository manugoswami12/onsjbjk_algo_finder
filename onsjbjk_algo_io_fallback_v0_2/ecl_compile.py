"""Environment step: Common Lisp file -> one ECL C unit per defun (compile only, never run).

Reuses ecl_filter's reader (top_forms), package prelude, RUTILS shim and _compile; ecl_filter.ecl_c
joins the units, which tree-sitter cannot parse as one file (each unit ends with ECL's module
initialiser), so here the units stay separate. A top-level form that defines nothing (a script:
`(loop ... do (print x))`) is compiled as the function ecl-toplevel, AP13's <toplevel>.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from ecl_filter import RUTILS_SHIM, _compile, top_forms
from lisp_sbcl_pnf import readable_source

# forms that define or configure instead of compute (defvar, defmacro, in-package, declaim, ...)
DECLARATION = re.compile(r'\(\s*([\w-]+:{1,2})?(def|in-package|eval-when|declaim|proclaim|require|provide|'
                         r'use-package|export|import|shadow|load|quickload)', re.IGNORECASE)


def ecl_units(path: Path, timeout=120) -> list[str]:
    """ECL C of every top-level defun of the file, one unit each ('' where ECL rejected the form)."""
    text, pkgs = readable_source(path.read_text(encoding='utf-8', errors='replace'))
    prelude = ''.join(f'(eval-when (:compile-toplevel :load-toplevel :execute) (unless (find-package "{p.upper()}") '
                      f'(make-package "{p.upper()}" :use (list "CL"))))\n' for p in pkgs)
    if 'rtl' in pkgs:
        prelude += f'(eval-when (:compile-toplevel) {RUTILS_SHIM})\n'   # a macro: no C function
    forms = []
    for f in top_forms(text):
        if re.match(r'\(defun\s', f, re.IGNORECASE):
            forms.append(f)
        elif not DECLARATION.match(f):
            forms.append(f'(defun ecl-toplevel () {f})')
    with tempfile.TemporaryDirectory(prefix='v02_eclu_') as td:
        return [_compile(prelude + f + '\n', Path(td), f'f{k}', timeout) for k, f in enumerate(forms)]
