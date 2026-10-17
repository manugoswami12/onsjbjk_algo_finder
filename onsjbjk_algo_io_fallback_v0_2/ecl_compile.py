"""Environment step: Common Lisp file -> one ECL C unit per defun (compile only, never run).

Reuses ecl_filter's reader (top_forms), package prelude, RUTILS shim and _compile; ecl_filter.ecl_c
joins the units, which tree-sitter cannot parse as one file (each unit ends with ECL's module
initialiser), so here the units stay separate.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from ecl_filter import RUTILS_SHIM, _compile, top_forms
from lisp_sbcl_pnf import readable_source


def ecl_units(path: Path, timeout=120) -> list[str]:
    """ECL C of every top-level defun of the file, one unit each ('' where ECL rejected the form)."""
    text, pkgs = readable_source(path.read_text(encoding='utf-8', errors='replace'))
    prelude = ''.join(f'(eval-when (:compile-toplevel :load-toplevel :execute) (unless (find-package "{p.upper()}") '
                      f'(make-package "{p.upper()}" :use (list "CL"))))\n' for p in pkgs)
    if 'rtl' in pkgs:
        prelude += RUTILS_SHIM
    defuns = [f for f in top_forms(text) if re.match(r'\(defun\s', f, re.IGNORECASE)]
    with tempfile.TemporaryDirectory(prefix='v02_eclu_') as td:
        return [_compile(prelude + f + '\n', Path(td), f'f{k}', timeout) for k, f in enumerate(defuns)]
