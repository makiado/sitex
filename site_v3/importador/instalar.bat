@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Criando ambiente virtual...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Nao foi possivel criar o ambiente virtual. Instale Python 3.11+ e marque Add Python to PATH.
    pause
    exit /b 1
  )
) else (
  echo [1/3] Ambiente virtual ja existe.
)
echo [2/3] Atualizando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r "importador\requirements.txt"
if errorlevel 1 (
  echo Falha ao instalar dependencias.
  pause
  exit /b 1
)
echo [3/3] Instalacao concluida.
pause
