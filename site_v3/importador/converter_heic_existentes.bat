@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" call "importador\instalar.bat"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" "importador\converter_heic_existentes.py"
pause
