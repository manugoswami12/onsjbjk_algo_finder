@echo off
setlocal
cd /d "%~dp0"
python -m unittest discover -s tests -p test_ap12.py -v
exit /b %ERRORLEVEL%
