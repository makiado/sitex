# Memórias — V3

Esta versão corrige três pontos da V2:

1. **HEIC/HEIF:** o importador converte os arquivos para JPEG dentro da biblioteca do site, preservando o original em `arquivadas/processadas/`. Assim Firefox, Brave, Chrome e outros navegadores não dependem de suporte nativo a HEIC para exibir as fotos.
2. **Google Takeout tardio:** `importador\aplicar_takeout.bat` varre o catálogo já existente e tenta enriquecer novamente fotos antigas com os JSONs do Takeout. `takeout_status.bat` mostra quantos JSONs foram lidos e quantas fotos encontraram correspondência/GPS.
3. **Compatibilidade de navegadores:** o site tenta múltiplos CDNs para D3/TopoJSON/Leaflet e possui fallback local de interface. O mapa mundial deixa de ser um ponto único de falha: mesmo sem as bibliotecas geográficas, os países com fotos aparecem como botões e o restante do site continua funcionando.

## Fluxo recomendado

### Primeiro uso
`importador\instalar.bat`

### Fotos novas
Coloque-as em `entrada\` e rode `importador\importar.bat`.

### Depois de exportar Google Takeout
Coloque os JSONs em `google_takeout\` e rode primeiro `importador\takeout_status.bat`.
Depois rode `importador\aplicar_takeout.bat` para enriquecer o catálogo antigo.

### HEIC
O original fica em `arquivadas\processadas\` e a cópia que o site usa fica como `.jpg` em `biblioteca\...`.

## Importante
Mantenha estas pastas do seu projeto atual ao atualizar os arquivos da V3:
- `biblioteca\`
- `arquivadas\`
- `entrada\`
- `google_takeout\`
- `pendentes\`
- `data\photos.json`
- `data\geocache.json`

Se estiver começando do zero, basta extrair o ZIP e usar as pastas vazias que já vêm na estrutura.
