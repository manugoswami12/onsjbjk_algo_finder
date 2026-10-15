@echo off
setlocal
where swipl >nul 2>nul
if errorlevel 1 (
  echo ERROR: SWI-Prolog missing. Add A:\swipl\bin to PATH.
  exit /b 2
)
where semgrep >nul 2>nul
if errorlevel 1 (
  echo ERROR: Semgrep missing. Activate ons_ruleskg.
  exit /b 2
)
echo === AP9 protected baseline ===
call RUN_AP9_ACCEPTANCE.cmd
if errorlevel 1 exit /b 1
echo === AP10 static and Prolog tests ===
python -m unittest discover -s tests -p test_ap10_*.py -v
if errorlevel 1 exit /b 1
echo === AP10 generated references against real OCaml AST ===
REM Separate store avoids contaminating existing AP10 catalogs.
set "AP10_TEST_STORE=%TEMP%\onsjbjk_ap10_%RANDOM%%RANDOM%"
python tools\ap10_cli.py --store "%AP10_TEST_STORE%" learn ap10_sort examples\ap10_sort_reference.py sort_reference
if errorlevel 1 exit /b 1
python tools\ap10_cli.py --store "%AP10_TEST_STORE%" learn ap10_hash examples\ap10_hash_reference.py hash_reference
if errorlevel 1 exit /b 1
python tools\ap10_cli.py --store "%AP10_TEST_STORE%" scan examples\ap10_mixed.py > "%AP10_TEST_STORE%\scan.log"
if errorlevel 1 exit /b 1
type "%AP10_TEST_STORE%\scan.log"
findstr /C:"AP10_THREAD: ap10_sort" "%AP10_TEST_STORE%\scan.log" >nul
if errorlevel 1 exit /b 1
findstr /C:"AP10_THREAD: ap10_hash" "%AP10_TEST_STORE%\scan.log" >nul
if errorlevel 1 exit /b 1
findstr /C:"relation: shared_loop" "%AP10_TEST_STORE%\scan.log" >nul
if errorlevel 1 exit /b 1
echo AP10 END-TO-END PASS. Evidence in "%AP10_TEST_STORE%\scan.log"
exit /b 0
