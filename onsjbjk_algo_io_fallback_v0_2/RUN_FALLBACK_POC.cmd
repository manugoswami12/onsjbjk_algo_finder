@echo off
setlocal
rem Standalone pilot. Does not touch any frozen AP9/AP10/AP11 files.
set "HERE=%~dp0"
where python >nul 2>nul || (echo ERROR: activate conda ons_ruleskg & exit /b 1)
where swipl >nul 2>nul || (echo ERROR: add A:\swipl\bin to PATH & exit /b 1)
if "%~1"=="" (
    python "%HERE%run_poc.py" --selftest
) else (
    python "%HERE%run_poc.py" "%~1"
)
exit /b %errorlevel%
