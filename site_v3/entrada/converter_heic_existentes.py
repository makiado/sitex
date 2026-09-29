from pathlib import Path
import shutil, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import *

ROOT = Path(__file__).resolve().parents[1]
CFG = load_json(ROOT/'config.json', {})
LIB = ROOT/CFG['folders']['library']
ARCH = ROOT/CFG['folders']['archive']
CATALOG_PATH = ROOT/CFG['catalog_file']


def rel_to_web(p):
    return make_web_path(p, ROOT)

catalog = load_json(CATALOG_PATH, {'version': 2, 'photos': []})
by_path = {str(r.get('path','')).lstrip('/'): r for r in catalog.get('photos', []) if r.get('path')}
count = 0
errors = 0

for src in LIB.rglob('*'):
    if not src.is_file() or src.suffix.lower() not in {'.heic', '.heif'}:
        continue
    try:
        rel = src.relative_to(ROOT).as_posix()
        rec = by_path.get(rel)
        # Fall back to filename if old catalog uses a slightly different web path.
        if rec is None:
            for r in catalog.get('photos', []):
                if r.get('filename') == src.name and str(r.get('path','')).endswith(src.name):
                    rec = r; break
        target = src.with_suffix('.jpg')
        if target.exists():
            target = src.with_name(src.stem + '_web.jpg')
        convert_heic_to_jpeg(src, target)
        archive = ARCH/'processadas_heic_antigos'/src.name
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists(): archive = ARCH/'processadas_heic_antigos'/(src.stem + '_old' + src.suffix)
        shutil.move(str(src), str(archive))
        if rec is not None:
            rec['path'] = rel_to_web(target)
            rec['extension'] = '.heic'
            rec['mime_type'] = 'image/jpeg'
            rec['converted_from'] = '.heic'
            rec.setdefault('notes', []).append('HEIC convertido para JPEG para compatibilidade do site.')
        count += 1
        print('OK:', target.relative_to(ROOT))
    except Exception as e:
        errors += 1
        print('ERRO:', src, e)

save_json(CATALOG_PATH, catalog)
print('\nConvertidas:', count)
print('Erros      :', errors)
