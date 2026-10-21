@echo off
rem Name the algorithm of a source file: analyze.cmd path\to\program.py   (also .c, .lisp, .hs; several files allowed)
rem Runs the whole pipeline (analyze.py). The first run learns TheAlgorithms once and keeps it in .cache\.
setlocal
if "%~1"=="" (
  echo usage: analyze.cmd FILE [FILE ...]   ^(Python .py, C .c, Common Lisp .lisp, Haskell .hs^)
  exit /b 2
)
where python >nul 2>nul || (echo Python is not installed or not on PATH ^(see README section 1^) & exit /b 1)
where swipl >nul 2>nul || (echo SWI-Prolog ^(swipl^) is not installed or not on PATH ^(see README section 1^) & exit /b 1)
set "ARGS="
:collect
if "%~1"=="" goto run
set ARGS=%ARGS% "%~f1"
shift
goto collect
:run
pushd "%~dp0"
set PYTHONPATH=.
python analyze.py %ARGS%
set RC=%ERRORLEVEL%
popd
exit /b %RC%
