"""AP13 environment interface: tool lookup and bounded subprocess calls only."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
PROLOG_DIR = ROOT / 'prolog'
# Frozen AP12 router, loaded unchanged.
AP12_ROUTER = REPO / 'algo_reference_corpus' / 'ap12' / 'prolog' / 'route_extended.pl'


class ToolError(RuntimeError):
    """A required external program is missing or failed: never reported as UNKNOWN."""


def need(program: str) -> str:
    path = shutil.which(program)
    if not path:
        raise ToolError(f'{program} not found on PATH (Windows: set "PATH=A:\\swipl\\bin;%PATH%")')
    return path


def run(argv: list[str], timeout: int = 60, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run without stdin so a toplevel can never wait for keyboard input."""
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=timeout, cwd=cwd, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f'{Path(argv[0]).name} timed out after {timeout}s') from exc


def swipl(goal: str, files: list[Path], args: list[str], timeout: int = 120) -> list[str]:
    """Load files, run goal, halt. Any stderr output is a failure, not data."""
    if not AP12_ROUTER.is_file():
        raise ToolError(f'frozen AP12 router missing: {AP12_ROUTER}')
    # Some SWI-Prolog versions honour only one -s flag, so every file is loaded
    # by one goal; paths are quoted Prolog atoms, never spliced as code.
    quoted = ','.join("'" + str(f).replace('\\', '/').replace("'", "\\'") + "'" for f in files)
    argv = [need('swipl'), '-q', '-g', f'load_files([{quoted}],[silent(true)]),{goal}',
            '-t', 'halt', '--', *args]
    done = run(argv, timeout)
    if done.returncode or done.stderr.strip():
        raise ToolError('SWI-Prolog failure: ' + (done.stderr or done.stdout)[-800:])
    return done.stdout.splitlines()
