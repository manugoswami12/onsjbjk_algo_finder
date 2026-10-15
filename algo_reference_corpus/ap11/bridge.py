"""Only link to frozen AP9/AP10 public functions, without editing that tree."""
from __future__ import annotations

from pathlib import Path
import sys


def frozen_root() -> Path:
    return Path(__file__).resolve().parents[2] / 'semgrep_prolog_poc'


def api(root: Path | None = None):
    root = (root or frozen_root()).resolve()
    required = ('tools/reference_pattern.py', 'tools/ap10_cli.py',
                'tools/ap10_reference_bundle.py', 'prolog/ap10_threads.pl')
    if not all((root / name).is_file() for name in required):
        raise ValueError(f'AP10 interface not found at {root}; install as sibling')
    tools = str(root / 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    # Uses the EXISTING trusted compiler, Semgrep capture and matcher, unchanged.
    import reference_pattern
    import ap10_cli
    import ap10_reference_bundle
    from typed_ast_codec import strict_load
    return reference_pattern, ap10_cli, ap10_reference_bundle, strict_load
