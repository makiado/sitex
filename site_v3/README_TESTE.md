# Teste rápido da versão 1.0

## Teste 1 — foto sem metadados

Coloque uma imagem sem GPS em `entrada/` e rode `importador\importar.bat`.

Resultado esperado:

`pendentes/localizacao/`

Isso é correto. O programa não deve adivinhar a localização.

## Teste 2 — foto real com GPS

Use uma foto tirada pelo celular com localização ativa.

Resultado esperado:

`biblioteca\País\Estado\Cidade\Ano\foto.jpg`

E `data/photos.json` deve registrar `location_source: exif`.

## Teste 3 — Google Takeout

Exporte as fotos/metadados pelo Google Takeout e coloque a pasta de metadados em `google_takeout/`.
A foto correspondente deve estar em `entrada/`.

Execute `importador\diagnosticar.bat` arrastando a foto para ele. O diagnóstico deve mostrar o JSON encontrado e as coordenadas. Depois execute `importador\importar.bat`.

## Teste 4 — duplicata

Copie novamente uma foto já importada para `entrada/` e rode o importador. Ela deve ir para `arquivadas\duplicadas\`.
