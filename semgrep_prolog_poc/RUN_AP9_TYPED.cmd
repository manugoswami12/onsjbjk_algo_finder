@echo off
setlocal
if "%~1"=="" (
  echo Usage: RUN_AP9_TYPED.cmd ^<captured-ocaml-ast.json^>
  exit /b 2
)
python tools\typed_ast_codec.py "%~1" out\ap9\typed_facts.pl --verify-roundtrip
exit /b %ERRORLEVEL%
