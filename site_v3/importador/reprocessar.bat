@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" call "importador\instalar.bat"
".venv\Scripts\python.exe" "importador\reprocessar.py"
pause
