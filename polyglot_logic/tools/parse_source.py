"""AP13 source input: language detection and tree-sitter parsing. Never executes source."""
from __future__ import annotations

from pathlib import Path

from env_run import ToolError
from lang_tables import EXTENSIONS, TREE_SITTER_LANGUAGES

MAX_BYTES = 1_000_000


def language_of(path: Path) -> str:
    lang = EXTENSIONS.get(path.suffix.lower())
    if not lang:
        raise ToolError(f'unsupported source extension: {path.suffix}')
    return lang


def read(path: Path) -> bytes:
    if not path.is_file():
        raise ToolError(f'source not found: {path}')
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ToolError('source exceeds 1 MB bounded limit')
    return data


def parser_for(lang: str):
    try:
        import tree_sitter_language_pack as pack
    except ImportError as exc:
        raise ToolError('tree-sitter-language-pack missing: python -m pip install tree-sitter-language-pack') from exc
    try:
        return pack.get_parser(lang)
    except Exception as exc:  # download/cache failures surface as many types
        raise ToolError(f'tree-sitter grammar {lang} unavailable (run RUN_AP13 prefetch while online): {exc}') from exc


def parse(path: Path):
    """Return (language, source bytes, root node or None for Prolog)."""
    lang = language_of(path)
    data = read(path)
    if lang not in TREE_SITTER_LANGUAGES:
        return lang, data, None  # Prolog is read by SWI-Prolog's own read_term/3
    return lang, data, parser_for(lang).parse(data).root_node


def prefetch() -> list[str]:
    for lang in TREE_SITTER_LANGUAGES:
        parser_for(lang)
    return list(TREE_SITTER_LANGUAGES)
