"""Ingest pinned TheAlgorithms/Python with frozen AP9 deterministic compiler."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import tempfile
import subprocess

from .bridge import api
from .database import add, connect, get, summary
from .source import REPOSITORY, inventory, label_for, revision, sha256, source_path, verify_origin


class IntegrityError(ValueError):
    """An immutable artifact changed: do not disguise corruption as a parse error."""


def record(*, label, commit, category, relative, function, function_path='',
           source_hash='', ast_hash='', pattern_hash='', structural_hash='',
           clause_path='', status='error', reason='') -> dict:
    return dict(label=label, language='Python', repository=REPOSITORY,
                git_commit=commit, category=category, relative_path=relative,
                function_name=function, function_path=function_path, region='body',
                ordinal=0, source_sha256=source_hash, ast_sha256=ast_hash,
                pattern_sha256=pattern_hash, structural_sha256=structural_hash,
                clause_path=clause_path, status=status, review_status='unreviewed',
                reason=reason[:600])


def ingest(corpus: Path, store: Path, categories: tuple[str, ...], limit: int,
           max_source_kib: int = 128, capture_fn=None, frozen: Path | None = None,
           require_origin: bool = True) -> dict:
    if limit < 1 or limit > 2000:
        raise ValueError('limit must be 1..2000; begin with 30')
    corpus = corpus.resolve(strict=True)
    commit = revision(corpus)
    if require_origin:
        verify_origin(corpus)
    exclusions = []
    files = inventory(corpus, categories, max_source_kib * 1024, exclusions)
    reference, ap10, _, strict_load = api(frozen)
    store = store.resolve()
    if store == corpus or corpus in store.parents:
        raise ValueError('store must not be inside read-only Git checkout')
    (store / 'refs').mkdir(parents=True, exist_ok=True)
    (store / 'temp').mkdir(parents=True, exist_ok=True)
    count = Counter()
    with connect(store) as db:
        for cat, rel in files:
            if count['attempted'] >= limit:
                break
            path = source_path(corpus, rel)
            file_hash = sha256(path.read_bytes())
            try:
                # Delete temporary captured AST after each source; source itself is not executed.
                with tempfile.TemporaryDirectory(prefix='capture_', dir=store / 'temp') as tmp:
                    ast_file = Path(tmp) / 'ast.json'
                    capture = capture_fn or ap10.capture
                    capture(path, ast_file)
                    if not ast_file.is_file():
                        raise ValueError('Semgrep AST capture not created')
                    if ast_file.stat().st_size > 16 * 1024 * 1024:
                        raise ValueError('Semgrep AST exceeds 16 MiB pilot limit')
                    ast_hash = sha256(ast_file.read_bytes())
                    tree = strict_load(ast_file)
                    occurrences = list(reference.functions(tree))
                    names = Counter(name for _, name, _, _ in occurrences)
                    if not occurrences:
                        raise ValueError('Semgrep AST did not expose any supported function')
                    for fpath, fname, _, _ in occurrences:
                        if count['attempted'] >= limit:
                            break
                        label = label_for(commit, rel, fname)
                        previous = get(db, label)
                        if previous:
                            if (previous['source_sha256'] != file_hash
                                    or previous['ast_sha256'] != ast_hash):
                                raise IntegrityError('pinned reference changed unexpectedly: ' + label)
                            if previous['status'] == 'generated':
                                clause = store / previous['clause_path']
                                if not clause.is_file() or sha256(clause.read_bytes()) != previous['pattern_sha256']:
                                    raise IntegrityError('missing/corrupted immutable clause: ' + label)
                            count['already_present'] += 1
                            count['attempted'] += 1
                            continue
                        count['attempted'] += 1
                        base = record(label=label, commit=commit, category=cat,
                                      relative=rel, function=fname,
                                      function_path=reference.path_string(fpath),
                                      source_hash=file_hash, ast_hash=ast_hash)
                        if names[fname] != 1:
                            base.update(status='skipped', reason='duplicate function name in same AST')
                            add(db, base)
                            count['skipped'] += 1
                            continue
                        try:
                            draft = Path(tmp) / (label + '.pl')
                            reference.compile_reference(ast_file, label, fname, 'body', 0, draft)
                            clause = draft.read_bytes()
                            # The clause differs by label; stripping the label gives a rough
                            # duplicate-structure fingerprint, not a semantic identity.
                            line = next(x for x in draft.read_text(encoding='utf8').splitlines()
                                        if x.startswith('reference_pattern('))
                            structure = line.split(',', 1)[1]
                            target = store / 'refs' / (label + '.pl')
                            if target.exists() and target.read_bytes() != clause:
                                raise IntegrityError('conflicting orphan clause: ' + label)
                            if not target.exists():
                                draft.replace(target)  # same-volume atomic rename
                            base.update(status='generated', clause_path='refs/' + target.name,
                                        pattern_sha256=sha256(clause),
                                        structural_sha256=sha256(structure.encode('utf8')))
                            add(db, base)
                            count['generated'] += 1
                        except (OSError, ValueError, TypeError) as exc:
                            base.update(status='error', reason=str(exc))
                            add(db, base)
                            count['error'] += 1
            except IntegrityError:
                raise
            except (OSError, ValueError, TypeError, RecursionError, TimeoutError, subprocess.TimeoutExpired) as exc:
                # Parsing a file failed: keep a traceable, nonrecognizable per-file row.
                label = label_for(commit, rel, '@file')
                if not get(db, label):
                    base = record(label=label, commit=commit, category=cat,
                                  relative=rel, function='@file', source_hash=file_hash,
                                  status='error', reason=str(exc))
                    add(db, base)
                count['parse_errors'] += 1
                count['attempted'] += 1
            print(f'AP11_PROGRESS: {rel}; generated={count["generated"]}; '
                  f'processed={count["attempted"]}/{limit}', flush=True)
        result = {'repository': REPOSITORY, 'git_commit': commit,
                  'categories': list(categories), 'limit': limit,
                  'files_available': len(files), 'excluded_sources': exclusions,
                  'run_counts': dict(count),
                  'database_summary': summary(db),
                  'disclaimer': 'unreviewed structural templates, not algorithm proofs'}
        output = store / 'ingest_summary.json'
        temp = output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
        temp.replace(output)
        return result
