@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1 || (echo AP12_ERROR: python not on PATH & exit /b 2)
where git >nul 2>&1 || (echo AP12_ERROR: git not on PATH & exit /b 2)
where swipl >nul 2>&1 || (echo AP12_ERROR: swipl not on PATH & exit /b 2)
where semgrep >nul 2>&1 || (echo AP12_ERROR: semgrep not on PATH & exit /b 2)
python -m ap12.full_ingest %*
exit /b %ERRORLEVEL%
