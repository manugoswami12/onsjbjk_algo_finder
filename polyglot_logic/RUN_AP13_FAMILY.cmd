@echo off
rem AP13 v3: input-output family of every function in a source file (doc 08).
rem   RUN_AP13_FAMILY.cmd examples\v3\cases\c01_bubble.c
setlocal
cd /d "%~dp0"
where swipl >nul 2>&1 || (echo AP13_ERROR: swipl not on PATH. set "PATH=A:\swipl\bin;%%PATH%%" ^& exit /b 2)
python tools\family_scan.py families %*
exit /b %ERRORLEVEL%
