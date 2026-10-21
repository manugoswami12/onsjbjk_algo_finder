@echo off
setlocal
cd /d "%~dp0"
python -m ap12.verify %*
exit /b %ERRORLEVEL%
