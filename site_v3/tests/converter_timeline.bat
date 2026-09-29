@echo off
:: Força a codificação para UTF-8
chcp 65001 >nul

echo ======================================================
echo    Processador da Linha do Tempo do iPhone (Google Maps)
echo ======================================================
echo.

:: 1. Verifica se o Timeline.json está na pasta
if not exist "Timeline.json" (
    echo [ERRO] O arquivo Timeline.json nao foi encontrado nesta pasta.
    echo Coloque o Timeline.json junto deste arquivo .bat e tente novamente.
    echo.
    pause
    exit /b
)

:: 2. Cria o script auxiliar de conversão Python temporário
echo [*] Gerando script de conversao...
(
echo from __future__ import annotations
echo import json
echo.
echo def parse_geo^(geo_str^):
echo     if not geo_str or not geo_str.startswith^('geo:'^):
echo         return None, None
echo     parts = geo_str.replace^('geo:', ''^).split^(','^)
echo     return int^(float^(parts[0]^) * 1e7^), int^(float^(parts[1]^) * 1e7^)
echo.
echo with open^('Timeline.json', 'r', encoding='utf-8'^) as f:
echo     registros = json.load^(f^)
echo.
echo timeline_objects = []
echo for item in registros:
echo     start_t = item.get^('startTime'^)
echo     end_t = item.get^('endTime'^)
echo     if 'visit' in item:
echo         top = item['visit'].get^('topCandidate', {}^)
echo         lat_e7, lng_e7 = parse_geo^(top.get^('placeLocation', ''^)^)
echo         timeline_objects.append^({
echo             'placeVisit': {
echo                 'location': {
echo                     'latitudeE7': lat_e7,
echo                     'longitudeE7': lng_e7,
echo                     'placeId': top.get^('placeID'^),
echo                     'semanticType': top.get^('semanticType'^)
echo                 },
echo                 'duration': {'startTimestamp': start_t, 'endTimestamp': end_t}
echo             }
echo         }^)
echo     elif 'activity' in item:
echo         top = item['activity'].get^('topCandidate', {}^)
echo         s_lat, s_lng = parse_geo^(item['activity'].get^('start', ''^)^)
echo         e_lat, e_lng = parse_geo^(item['activity'].get^('end', ''^)^)
echo         dist = float^(item['activity'].get^('distanceMeters', 0^)^)
echo         timeline_objects.append^({
echo             'activitySegment': {
echo                 'startLocation': {'latitudeE7': s_lat, 'longitudeE7': s_lng},
echo                 'endLocation': {'latitudeE7': e_lat, 'longitudeE7': e_lng},
echo                 'duration': {'startTimestamp': start_t, 'endTimestamp': end_t},
echo                 'activityType': top.get^('type'^),
echo                 'distance': dist
echo             }
echo         }^)
echo.
echo with open^('takeout_convertido.json', 'w', encoding='utf-8'^) as f:
echo     json.dump^({'timelineObjects': timeline_objects}, f, ensure_ascii=False, indent=2^)
echo print^(f'[OK] Sucesso: {len^(timeline_objects^)} registros convertidos em takeout_convertido.json'^)
) > _conversor_temp.py

:: 3. Executa a conversão via Python
echo [*] Convertendo formato do iPhone para o formato padrao do Takeout...
python _conversor_temp.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERRO] Falha ao executar o Python. Verifique se o Python esta instalado e no PATH.
    del _conversor_temp.py 2>nul
    pause
    exit /b
)

:: 4. Remove o arquivo temporário
del _conversor_temp.py 2>nul

echo.
echo ======================================================
echo  Conversao concluida! Arquivo gerado: takeout_convertido.json
echo ======================================================
echo.
pause