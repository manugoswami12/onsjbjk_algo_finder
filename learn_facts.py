"""Learning (doc 04 section 14), environment step: the facts of a file as the normal process loads them, and
its tree nodes (prolog/tree_main.pl). Nothing is run."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import compare_learners
import ecl_compile
import ecl_facts

compare_learners._ap13()
import cli  # AP13: tree-sitter lowerers (Python, C, Haskell, ...)
import env_run

TREE_MAIN = Path(__file__).resolve().parent / 'prolog' / 'tree_main.pl'


def tree_facts(path: Path) -> tuple[str, str]:
    """(kind, facts): ECL facts for Lisp (tree_main normalises them as ecl_main.pl does), AP13 lowerer facts
    otherwise."""
    if path.suffix == '.lisp':
        units = ecl_compile.ecl_units(path)
        return 'lisp', ecl_facts.facts_of(units) if any(units) else ''
    if path.suffix == '.c':
        return 'ap13', c_facts(path)
    if path.suffix == '.py' and path.read_text(encoding='utf-8', errors='replace').lstrip().startswith('>>>'):
        return 'ap13', session_facts(path)
    if path.suffix == '.hs':                          # AP13's Haskell lowerer, subclassed (haskell_logic.py)
        import haskell_logic
        import haskell_ast_check                      # GHC's parser checks tree-sitter's functions (19.10)
        return 'ap13', haskell_ast_check.check(haskell_logic.lower(path), path)
    if path.suffix == '.py':                          # with what Python tells about its own program
        import pyast_facts
        return 'ap13', imperative_facts(path) + pyast_facts.facts(path)
    return 'ap13', imperative_facts(path)


def imperative_facts(path: Path) -> str:
    """AP13's imperative lowerer, subclassed (imperative_logic.py) for Python and C; AP13's own otherwise."""
    if path.suffix in ('.py', '.c'):
        import imperative_logic
        import returns_function                   # a function returning a function is lowered as a new one (19.8)
        returns_function.install()
        return imperative_logic.lower(path)
    return cli.facts_text(path)[1]


def session_facts(path: Path) -> str:
    """A Python file that is an interactive session (>>> def j(n, k): ...): its program is the session with the
    prompts (>>> and ...) removed. Sessions pasted without continuation prompts put a function's body on
    plain lines, so those are kept; the printed output left in is not Python and the parser's error recovery
    skips it."""
    lines = []
    for raw in path.read_text(encoding='utf-8', errors='replace').splitlines(keepends=True):
        lines.append(raw[4:] if raw.startswith(('>>> ', '... ')) else '' if raw.strip() in ('>>>', '...') else raw)
    with tempfile.TemporaryDirectory(prefix='v02_session_') as td:
        f = Path(td) / path.name
        f.write_text(''.join(lines), encoding='utf-8')
        return imperative_facts(f)


def c_facts(path: Path) -> str:
    """AP13 facts of a C file after its own macros are expanded by the C preprocessor (a function-like macro
    MAT_ELEM(r, c) is the expression it stands for); system headers are not read (#include lines dropped)."""
    text = ''.join(line for line in path.read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
                   if not line.lstrip().startswith('#include'))
    done = subprocess.run(['cpp', '-P', '-w', '-undef'], input=text, capture_output=True, text=True, check=False)
    if done.returncode != 0 or not done.stdout.strip():
        return imperative_facts(path)                # the preprocessor cannot read it: the file as it is
    with tempfile.TemporaryDirectory(prefix='v02_cpp_') as td:
        f = Path(td) / path.name
        f.write_text(done.stdout, encoding='utf-8')
        return imperative_facts(f)


def defines_code(path: Path) -> bool:
    """The source defines something (a function or a binding): a REPL transcript (*Main> f x) defines nothing.
    Haskell is read from its syntax tree (tree-sitter, AP13 parse_source), since AP13's lowerer gives no facts
    for some definitions too; the other languages' lowerers give a function for every definition."""
    if path.suffix == '.hs':
        from parse_source import parse
        stack = [parse(path)[2]]
        while stack:
            node = stack.pop()
            if node.type in ('function', 'bind'):
                return True
            stack.extend(node.children)
        return False
    return 'func(' in tree_facts(path)[1]


def swipl_facts(goal: str, program: Path, kind: str, text: str, *args: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='v02_tree_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(text, encoding='utf-8')
        return env_run.swipl(goal, [program], [str(f), kind, *args])


def nodes(path: Path) -> list[str]:
    """The deepest family paths 'a>b>c' of the file's functions (the normal process's tree)."""
    kind, text = tree_facts(path)
    if not text.strip():
        return []
    return sorted({line.split('|', 2)[2] for line in swipl_facts('tree_main', TREE_MAIN, kind, text)
                   if line.startswith('NODE|')})
