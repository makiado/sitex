@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" call "importador\instalar.bat"
if "%~1"=="" (
  echo Arraste uma foto para este arquivo .bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "importador\diagnosticar.py" "%~1"
pause
