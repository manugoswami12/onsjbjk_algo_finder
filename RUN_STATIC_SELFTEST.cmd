@echo off
setlocal
python "%~dp0run_poc.py" --offline-tests
exit /b %errorlevel%
