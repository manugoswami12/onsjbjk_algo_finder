@echo off
setlocal
call RUN_AP8_ACCEPTANCE.cmd
if errorlevel 1 exit /b %ERRORLEVEL%
python -m unittest discover -s tests -p test_ap9_*.py -v
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_AP9_TYPED.cmd tests\fixtures\semgrep_binary_ast.json
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_AP9_EVALUATE.cmd
if errorlevel 1 exit /b %ERRORLEVEL%
echo AP9 COMPLETE. Inspect out\ap9\evaluation.json; these are bounded structural results, NOT semantic proof.
exit /b 0
