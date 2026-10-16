@echo off
rem AP13 prerequisites (run in the ons_ruleskg conda env; SWI-Prolog on PATH, e.g. set "PATH=A:\swipl\bin;%PATH%")
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python tools\cli.py prefetch || exit /b 1
if not exist store mkdir store
if not exist store\TheAlgorithms_Python git clone -q https://github.com/TheAlgorithms/Python.git store\TheAlgorithms_Python
git -C store\TheAlgorithms_Python checkout -q e1a2a8b0
python tools\rosetta_eval.py --store store --rosetta store\rosetta
echo AP13 setup done: corpus in store\TheAlgorithms_Python, Rosetta in store\rosetta
