@echo off
setlocal
where swipl >nul 2>&1
if errorlevel 1 (
  echo ERROR: swipl is not on PATH. Set your portable SWI-Prolog bin PATH first.
  exit /b 2
)
where semgrep >nul 2>&1
if errorlevel 1 (
  echo ERROR: semgrep is not on PATH.
  exit /b 2
)
call RUN_SELFTESTS.cmd
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_DEMO.cmd examples\search_binary.py
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_DEMO.cmd examples\search_linear.py
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_MULTI.cmd examples\sort_then_search.py
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_MULTI.cmd examples\sort_only.py
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_MULTI.cmd examples\no_swap_then_search.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo AP3 ACCEPTANCE RUN COMPLETED. Verify expected labels above; automatic assertions ran in selftests.
exit /b 0
