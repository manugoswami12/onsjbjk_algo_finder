@echo off
rem Held-out evaluation: sparse-clones Rosetta Code (GFDL, not committed) into store\rosetta.
setlocal
cd /d "%~dp0"
where swipl >nul 2>&1 || (echo AP13_ERROR: swipl not on PATH & exit /b 2)
where git >nul 2>&1 || (echo AP13_ERROR: git not on PATH & exit /b 2)
python tools\rosetta_eval.py %*
exit /b %ERRORLEVEL%
