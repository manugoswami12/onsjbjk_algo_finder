@echo off
setlocal
python "%~dp0run_v2.py" --offline-tests
exit /b %errorlevel%
