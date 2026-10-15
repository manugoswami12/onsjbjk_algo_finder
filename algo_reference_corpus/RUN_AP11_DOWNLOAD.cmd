@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo AP11 ERROR: git is not on PATH.
  exit /b 2
)
if exist "TheAlgorithms_Python\.git" (
  echo AP11: Existing checkout kept unchanged. Never auto-pulling a pinned corpus.
) else (
  if exist "TheAlgorithms_Python" (
    echo AP11 ERROR: Directory exists but it is not a Git checkout.
    exit /b 2
  )
  git clone --depth 1 --single-branch https://github.com/TheAlgorithms/Python.git TheAlgorithms_Python
  if errorlevel 1 exit /b 2
)
git -C TheAlgorithms_Python rev-parse HEAD
if errorlevel 1 exit /b 2
if not exist "TheAlgorithms_Python\LICENSE.md" (
  echo AP11 ERROR: Upstream LICENSE.md missing.
  exit /b 2
)
echo AP11: Checkout available. Keep it unchanged for reproducible ingestion.
exit /b 0
