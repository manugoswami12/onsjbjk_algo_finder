#!/usr/bin/env python3
"""AP10-only assembly of immutable AP9-generated reference clauses.

Consult one source file containing all reference_pattern/4 clauses, instead of
consulting each generated reference separately. AP9 output is not modified.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from export_ast_facts import atom


def bundle_references(references: Iterable[tuple[str, Path]], output: Path) -> Path:
    """Produce a single Prolog source, rejecting altered or duplicate clauses."""
    result = ['% AP10 view of immutable AP9-generated references.']
    seen: set[str] = set()
    for label, source in references:
        if label in seen:
            raise ValueError(f'duplicate reference label in bundle: {label}')
        seen.add(label)
        text = Path(source).read_text(encoding='utf-8')
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.lstrip().startswith('%')]
        prefix = f'reference_pattern({atom(label)},'
        if len(lines) != 1 or not lines[0].startswith(prefix) or not lines[0].endswith(').'):
            raise ValueError(f'not a single AP9-generated reference clause for {label}: {source}')
        result.append(lines[0])
    if not seen:
        raise ValueError('cannot bundle an empty reference catalog')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    temporary.write_text('\n'.join(result) + '\n', encoding='utf-8')
    temporary.replace(output)
    return output
