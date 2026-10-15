@echo off
setlocal
cd /d "%~dp0"
where semgrep >nul 2>nul
if errorlevel 1 (
 echo AP11 ERROR: semgrep missing. Activate ons_ruleskg.
 exit /b 2
)
where swipl >nul 2>nul
if errorlevel 1 (
 echo AP11 ERROR: swipl missing. Add A:\swipl\bin to PATH.
 exit /b 2
)
echo === PROTECTED AP10 BASELINE BEFORE ===
pushd "..\semgrep_prolog_poc"
if errorlevel 1 exit /b 2
call RUN_AP10_ACCEPTANCE.cmd
set "AP10_RESULT=%ERRORLEVEL%"
popd
if not "%AP10_RESULT%"=="0" exit /b 2
echo === AP11 OFFLINE TESTS ===
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 2
if not exist "TheAlgorithms_Python\.git" (
 echo AP11 ERROR: Run RUN_AP11_DOWNLOAD.cmd first.
 exit /b 2
)
echo === AP11 REAL CORPUS INGESTION: UP TO 30 FUNCTIONS ===
call RUN_AP11.cmd ingest --limit 30
if errorlevel 1 exit /b 2
python -m ap11.live_smoke
if errorlevel 1 exit /b 2
echo === PROTECTED AP10 BASELINE AFTER ===
pushd "..\semgrep_prolog_poc"
if errorlevel 1 exit /b 2
call RUN_AP10_ACCEPTANCE.cmd
set "AP10_RESULT=%ERRORLEVEL%"
popd
if not "%AP10_RESULT%"=="0" exit /b 2
echo AP11 LIVE ACCEPTANCE PASS - independent generalization still needs held-out evaluation.
exit /b 0
