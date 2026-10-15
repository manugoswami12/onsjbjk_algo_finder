"""Create disposable AP10-compatible view from approved (or explicitly unreviewed) references."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile

from .bridge import api
from .database import connect
from .source import sha256


def scan(store: Path, source: Path, category: str | None = None,
         include_unreviewed: bool = False, limit: int = 30,
         frozen: Path | None = None, label: str | None = None) -> str:
    if not 1 <= limit <= 100:
        raise ValueError('scan reference limit must be 1..100; measure before enlarging')
    store = store.resolve()
    _, ap10, _, _ = api(frozen)
    with connect(store) as conn:
        sql = "SELECT * FROM reference WHERE status='generated' AND review_status != 'rejected'"
        params: list = []
        if not include_unreviewed:
            sql += " AND review_status='approved'"
        if category:
            sql += ' AND category=?'
            params.append(category)
        if label:
            sql += ' AND label=?'
            params.append(label)
        sql += ' ORDER BY category, relative_path, function_name, label LIMIT ?'
        refs = conn.execute(sql, [*params, limit + 1]).fetchall()
        truncated = len(refs) > limit
        refs = refs[:limit]
        if not refs:
            return ('AP11_UNKNOWN: no eligible references. Approve labels with review command '
                    'or use --include-unreviewed for experimental scanning.\n')
        # The disposable catalog is deliberately outside the default AP10 store.
        (store / 'temp').mkdir(exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory(prefix='scan_', dir=store / 'temp') as d:
            temporary = Path(d)
            catalog = []
            for ref in refs:
                p = store / ref['clause_path']
                if not p.resolve().is_relative_to((store / 'refs').resolve()):
                    raise ValueError('untrusted clause location in database')
                data = p.read_bytes()
                if sha256(data) != ref['pattern_sha256']:
                    raise ValueError('stored Prolog clause checksum mismatch: ' + ref['label'])
                target = temporary / (ref['label'] + '.pl')
                target.write_bytes(data)
                catalog.append({'label': ref['label'], 'clause': target.name,
                                'reference_function': ref['function_name'],
                                'region': 'body', 'ordinal': 0,
                                'source': ref['relative_path']})
            (temporary / 'catalog.json').write_text(json.dumps(catalog), encoding='utf8')
            out = io.StringIO()
            with redirect_stdout(out):
                result = ap10.scan(temporary, source)
            if result:
                raise ValueError('frozen AP10 scanner failed')
    return ('AP11_SCAN: references=' + str(len(refs))
            + '; scope=' + ('approved+unreviewed' if include_unreviewed else 'approved')
            + '; truncated=' + str(truncated) + '\n'
            + 'AP11_NOTICE: matched labels are structural candidates, not verified semantics.\n'
            + out.getvalue())
