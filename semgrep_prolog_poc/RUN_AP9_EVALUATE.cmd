@echo off
setlocal
python tools\evaluate_reference.py tests\fixtures\ap9_cases\manifest.json --backend prolog --out out\ap9\evaluation.json
exit /b %ERRORLEVEL%
