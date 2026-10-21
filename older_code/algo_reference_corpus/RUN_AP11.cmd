@echo off
setlocal
cd /d "%~dp0"
python -m ap11.cli %*
exit /b %ERRORLEVEL%
