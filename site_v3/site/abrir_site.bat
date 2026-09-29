@echo off
cd /d "%~dp0.."
echo Iniciando servidor local em http://localhost:8000/site/
start "Site Memorias" cmd /k "py -3 -m http.server 8000"
timeout /t 2 >nul
start "" "http://localhost:8000/site/"
