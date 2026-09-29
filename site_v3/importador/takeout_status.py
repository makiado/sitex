from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import *

ROOT = Path(__file__).resolve().parents[1]
CFG = load_json(ROOT/'config.json', {})
TAKEOUT = ROOT/CFG['folders']['takeout']
INPUT = ROOT/CFG['folders']['input']
PEND = ROOT/CFG['folders']['pending']

print('=== GOOGLE TAKEOUT — DIAGNÓSTICO ===')
idx = build_takeout_index(TAKEOUT)
print('JSON encontrados :', idx['json_count'])
print('registros lidos  :', idx['record_count'])
files = [p for base in (INPUT, PEND) for p in base.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
print('fotos para testar :', len(files))
matched = gps = 0
for p in files:
    tk = takeout_info(p, idx)
    if tk.get('json_path'):
        matched += 1
        if tk.get('latitude') is not None and tk.get('longitude') is not None:
            gps += 1
        print(f'OK  {p.name} -> GPS={tk.get("latitude")},{tk.get("longitude")} | {tk.get("json_path")}')
print('correspondências :', matched)
print('com GPS          :', gps)
