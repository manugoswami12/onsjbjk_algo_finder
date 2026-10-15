@echo off
setlocal
if "%~5"=="" (
  echo Usage: RUN_AP9_REFERENCE.cmd ^<reference-ast.json^> ^<target-ast.json^> ^<label^> ^<reference-function^> ^<region^>
  echo Region: body, for, while, if, assign
  exit /b 2
)
python tools\run_reference.py "%~1" "%~2" --label "%~3" --function "%~4" --region "%~5"
exit /b %ERRORLEVEL%
