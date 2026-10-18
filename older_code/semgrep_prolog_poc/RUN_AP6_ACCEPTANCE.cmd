@echo off
setlocal
where swipl >nul 2>&1
if errorlevel 1 (echo ERROR: swipl is not on PATH & exit /b 2)
where semgrep >nul 2>&1
if errorlevel 1 (echo ERROR: semgrep is not on PATH & exit /b 2)
call RUN_AP3_ACCEPTANCE.cmd
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_THREADS.cmd examples\interleaved_sort_hash.py
if errorlevel 1 exit /b %ERRORLEVEL%
python -m unittest discover -s tests -p test_thread_recognition.py -v
if errorlevel 1 exit /b %ERRORLEVEL%
echo AP6 commands completed. Verify 2 candidates and INTERLEAVED_WITH on positive example.
exit /b 0
