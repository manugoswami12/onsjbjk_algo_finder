@echo off
setlocal
rem v0.2 runner. Does not touch onsjbjk_algo_io_fallback_poc_v0_1 or any frozen AP files.
set "HERE=%~dp0"
where python >nul 2>nul || (echo ERROR: activate conda ons_ruleskg & exit /b 1)
where swipl >nul 2>nul || (echo ERROR: add A:\swipl\bin to PATH & exit /b 1)
if "%~1"=="" (
    python "%HERE%run_v2.py" --selftest
) else (
    python "%HERE%run_v2.py" "%~1"
)
exit /b %errorlevel%
