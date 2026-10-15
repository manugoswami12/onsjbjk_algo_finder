@echo off
setlocal
python tools\run_demo.py --audit %*
exit /b %ERRORLEVEL%
