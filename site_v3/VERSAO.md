# Site Memórias — V1.0

## Objetivo
Base limpa e independente para o projeto de trajetória por fotografias.

## O que já existe

- Importador separado do site.
- Leitura de GPS/data EXIF.
- Leitura recursiva dos JSONs do Google Takeout.
- Associação por nome/título da fotografia.
- Detecção de duplicatas por SHA-256.
- Reverse geocoding com cache via OpenStreetMap/Nominatim.
- Catálogo central em `data/photos.json`.
- Organização física por país/estado/cidade/ano.
- Pasta de pendências para fotos sem localização.
- Diagnóstico individual de fotografias.
- Reprocessamento de pendências.
- Frontend com globo mundial selecionável.
- Visão de país com mapa, regiões, anos e feed vertical.
- Lightbox para fotos.
- Layout responsivo.

## Dependência externa de geografia

O mapa mundial e limites administrativos são carregados pelo navegador de serviços públicos/CDN. O catálogo e as fotografias continuam locais.
