"""Read-only, pinned Git source inventory. Never import or execute corpus modules."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess

REPOSITORY = 'https://github.com/TheAlgorithms/Python.git'
DEFAULT_CATEGORIES = ('sorts', 'searches', 'hashes', 'strings')


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            check=False, timeout=30)
    if result.returncode:
        raise ValueError(f'git {" ".join(args)} failed: '
                         + result.stderr.decode('utf-8', 'replace')[-500:])
    return result.stdout.decode('utf-8', 'replace').strip()


def revision(root: Path) -> str:
    root = root.resolve(strict=True)
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('corpus must be the Git worktree root')
    commit = git(root, 'rev-parse', 'HEAD')
    if not re.fullmatch(r'[a-f0-9]{40,64}', commit):
        raise ValueError('unexpected Git commit identifier')
    # The tracked worktree must match the recorded commit. Ignore harmless untracked files.
    if git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked corpus has edits; cannot claim pinned reproducibility')
    return commit


def verify_origin(root: Path) -> None:
    url = git(root, 'remote', 'get-url', 'origin').rstrip('/').lower()
    allowed = {'https://github.com/thealgorithms/python.git',
               'https://github.com/thealgorithms/python',
               'git@github.com:thealgorithms/python.git',
               'ssh://git@github.com/thealgorithms/python.git'}
    if url not in allowed:
        raise ValueError('origin is not the pinned TheAlgorithms/Python repository: ' + url)


def source_path(root: Path, relative: str) -> Path:
    """Reject traversals and symlinks in *all* path segments."""
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.suffix != '.py':
        raise ValueError('invalid repository-relative Python path')
    candidate = root
    for component in p.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise ValueError('symlink is not a trusted corpus input')
    if not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('file missing or outside corpus root')
    return candidate


def inventory(root: Path, categories: tuple[str, ...], max_bytes: int,
              exclusions: list | None = None) -> list[tuple[str, str]]:
    """Tracked .py files, fair round-robin across categories, stable ordering."""
    for cat in categories:
        if not re.fullmatch(r'[a-z][a-z0-9_]*', cat):
            raise ValueError(f'invalid category: {cat}')
    data = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--', *categories],
                          capture_output=True, check=False, timeout=30)
    if data.returncode:
        raise ValueError('git ls-files failed: ' + data.stderr.decode('utf8', 'replace')[-300:])
    grouped = {cat: [] for cat in categories}
    for part in data.stdout.split(b'\0'):
        if not part:
            continue
        rel = part.decode('utf-8', 'strict').replace('\\', '/')
        cat = rel.split('/', 1)[0]
        if cat not in grouped or not rel.endswith('.py'):
            continue
        try:
            path = source_path(root, rel)
            if path.stat().st_size > max_bytes:
                if exclusions is not None: exclusions.append({'path': rel, 'reason': 'source too large'})
                continue
        except (OSError, ValueError) as exc:
            if exclusions is not None: exclusions.append({'path': rel, 'reason': str(exc)})
            continue
        grouped[cat].append(rel)
    for paths in grouped.values():
        paths.sort()
    result = []
    depth = 0
    while any(len(v) > depth for v in grouped.values()):
        for cat in categories:
            if depth < len(grouped[cat]):
                result.append((cat, grouped[cat][depth]))
        depth += 1
    return result


def label_for(commit: str, relative: str, function: str) -> str:
    """AP10 label: stable across runs, distinct across revisions and paths."""
    slug = re.sub(r'[^a-z0-9_]', '_', f'{Path(relative).stem}_{function}'.lower())
    digest = hashlib.sha256(f'Python\0{commit}\0{relative}\0{function}'.encode()).hexdigest()[:16]
    return 'py_' + slug[:41].rstrip('_') + '_' + digest  # max 61 chars


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
