@echo off
setlocal
cd /d "%~dp0"
where swipl >nul 2>&1 || (echo AP12_ERROR: swipl not on PATH & exit /b 2)
where semgrep >nul 2>&1 || (echo AP12_ERROR: semgrep not on PATH & exit /b 2)
python -m ap12.scan_auto %*
exit /b %ERRORLEVEL%
