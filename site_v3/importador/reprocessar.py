from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'pendentes/localizacao'
ENTRY=ROOT/'entrada'
files=[p for p in P.iterdir() if p.is_file()]
if not files:
 print('Nenhuma foto pendente para reprocessar.')
 raise SystemExit(0)
for p in files:
    dest=ENTRY/p.name
    if dest.exists(): dest=ENTRY/(p.stem+'_reprocessada'+p.suffix)
    dest.parent.mkdir(parents=True,exist_ok=True)
    p.replace(dest)
print(f'{len(files)} foto(s) movida(s) para entrada/. Execute importar.bat para tentar novamente.')
