@echo off
setlocal
python tools\run_demo.py --threads %*
exit /b %ERRORLEVEL%
