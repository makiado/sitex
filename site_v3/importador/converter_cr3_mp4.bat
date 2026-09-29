@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente nao instalado. Executando instalador...
  call "importador\instalar.bat"
)
echo.
echo Importando e convertendo CR3/MP4 da pasta entrada...
".venv\Scripts\python.exe" "importador\importar.py"
echo.
echo CR3 sera convertido para JPEG e MP4 para H.264/AAC.
pause
