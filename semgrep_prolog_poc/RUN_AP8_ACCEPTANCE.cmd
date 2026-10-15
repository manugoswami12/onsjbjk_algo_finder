@echo off
setlocal
call RUN_AP6_ACCEPTANCE.cmd
if errorlevel 1 exit /b %ERRORLEVEL%
python -m unittest discover -s tests -p test_audit_recognition.py -v
if errorlevel 1 exit /b %ERRORLEVEL%
call RUN_AUDIT.cmd examples\interleaved_sort_hash.py
if errorlevel 1 exit /b %ERRORLEVEL%
echo AP8 AUDIT EXECUTED. Review audited_structural for both and INTERLEAVED_AUDITED above.
exit /b 0
