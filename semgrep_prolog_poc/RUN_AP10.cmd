@echo off
setlocal
if "%~1"=="" (
    echo Usage: RUN_AP10.cmd learn LABEL SOURCE.py FUNCTION
    echo        RUN_AP10.cmd scan TARGET.py
    echo All AP9 commands continue to work unchanged.
    exit /b 2
)
python tools\ap10_cli.py %*
exit /b %ERRORLEVEL%
