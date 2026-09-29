# Google Maps Timeline — integração ao importador existente

O arquivo `google_takeout/Timeline.json` já está incluído neste pacote. É um **dado pessoal sensível**: não publique essa pasta no GitHub nem exponha o JSON pelo servidor web. O arquivo deve permanecer apenas no computador que importa as fotos.

1. Se necessário, ajuste `google_timeline.timezone_offset` no `config.json` para o fuso em que o relógio da câmera estava configurado (por exemplo `-03:00`). EXIF sem fuso é interpretado nesse horário; horários ISO com fuso explícito são preservados.
2. Coloque novas fotos em `entrada/` e execute `importador/importar.bat` normalmente.
3. Para fotos **já catalogadas** sem coordenadas, execute `importador/aplicar_timeline.bat` (que chama o aplicador de Takeout atualizado). Ele tenta encontrar os horários na Timeline, geocodificar e mover as imagens para a biblioteca por país/estado/cidade. Para fotos ainda em `pendentes/localizacao/`, execute também `reprocessar.bat` e depois `importar.bat`.
4. Ordem de prioridade: GPS EXIF > GPS de JSON individual Takeout > Google Timeline. Segmentos de visita usam o local registrado; segmentos de deslocamento usam **interpolação estimada** entre início e fim. Fotos sem data confiável ou sem intervalo correspondente continuam sem localização.
5. `location_source` e `timeline_match` registram a origem da estimativa em `data/photos.json`. A localização no mapa usa os campos existentes `latitude` e `longitude`.

**Privacidade:** o arquivo JSON da Timeline e o catálogo podem conter coordenadas residenciais. Antes de publicar, revise os dados e retire informações que não deseja compartilhar.
