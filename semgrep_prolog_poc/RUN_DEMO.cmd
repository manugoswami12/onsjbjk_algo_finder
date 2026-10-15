@echo off
setlocal
python tools\run_demo.py %*
exit /b %ERRORLEVEL%
