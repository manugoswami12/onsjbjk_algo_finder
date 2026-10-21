@echo off
setlocal
cd /d "%~dp0"
where swipl >nul 2>&1 || (echo AP13_ERROR: swipl not on PATH & exit /b 2)
python -m unittest discover -s tests -v
exit /b %ERRORLEVEL%
