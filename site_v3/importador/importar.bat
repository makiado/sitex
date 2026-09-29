@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" call "importador\instalar.bat"
if not exist ".venv\Scripts\python.exe" exit /b 1
echo [1/2] Verificando dependencias...
".venv\Scripts\python.exe" -c "import PIL" >nul 2>&1
if errorlevel 1 call "importador\instalar.bat"
echo [2/2] Importando fotos...
".venv\Scripts\python.exe" "importador\importar.py"
echo.
pause
