@echo off
setlocal
python tools\run_demo.py --multi %*
exit /b %ERRORLEVEL%
