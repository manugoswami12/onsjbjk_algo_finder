"""Language front ends that reuse each language's own tooling, plugged into the AP13 behaviour
pipeline (polyglot_logic/tools/io_trace.py) at run time; polyglot_logic itself is not edited.

  .hs    GHC Core (haskell_core_pnf.py)
  .lisp  SBCL macro-expansion of standard macros, then the AP13 Lisp translator (lisp_sbcl_pnf.py)
"""
from __future__ import annotations

from pathlib import Path

_installed = False


def install():
    global _installed
    if _installed:
        return
    import compare_learners
    compare_learners._ap13()
    import io_trace
    original = io_trace.normal_form

    def normal_form(path: Path):
        suffix = Path(path).suffix.lower()
        if suffix == '.hs':
            from haskell_core_pnf import haskell_normal_form
            return 'haskell', haskell_normal_form(Path(path))
        if suffix in ('.lisp', '.cl', '.lsp'):
            from lisp_sbcl_pnf import lisp_normal_form_sbcl
            return 'commonlisp', lisp_normal_form_sbcl(Path(path))
        return original(path)
    io_trace.normal_form = normal_form
    _installed = True
