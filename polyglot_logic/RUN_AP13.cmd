@echo off
rem AP13 multi-language logic tracing. Examples:
rem   RUN_AP13.cmd prefetch
rem   RUN_AP13.cmd learn ref_bubble_py examples\bubble\bubble.py bubble_sort
rem   RUN_AP13.cmd scan examples\bubble\bubble.hs
rem   RUN_AP13.cmd learn-corpus ..\algo_reference_corpus\TheAlgorithms_Python ..\algo_reference_corpus\store
setlocal
cd /d "%~dp0"
where swipl >nul 2>&1 || (echo AP13_ERROR: swipl not on PATH. set "PATH=A:\swipl\bin;%%PATH%%" & exit /b 2)
python tools\cli.py %*
exit /b %ERRORLEVEL%
