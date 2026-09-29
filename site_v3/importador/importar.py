from pathlib import Path
import shutil, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import *

ROOT = Path(__file__).resolve().parents[1]
CFG = load_json(ROOT/'config.json', {})
INPUT = ROOT/CFG['folders']['input']
TAKEOUT = ROOT/CFG['folders']['takeout']
LIB = ROOT/CFG['folders']['library']
ARCH = ROOT/CFG['folders']['archive']
PEND = ROOT/CFG['folders']['pending']
CATALOG_PATH = ROOT/CFG['catalog_file']

for p in (INPUT, TAKEOUT, LIB, ARCH, PEND, ROOT/'logs'):
    p.mkdir(parents=True, exist_ok=True)


def archive_original(src: Path, original_name: str, root: Path, kind='processadas'):
    dest = ARCH / kind / original_name
    if dest.exists():
        dest = ARCH / kind / f'{src.stem}_{int(src.stat().st_mtime)}{src.suffix}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


def unique_target(target: Path):
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 2
    while True:
        candidate = target.with_name(f'{stem} ({i}){suffix}')
        if not candidate.exists():
            return candidate
        i += 1


def process_one(path, catalog, existing_by_hash, takeout_index, geocoder):
    sha = sha256(path)
    if sha in existing_by_hash:
        dest = unique_target(ARCH/'duplicadas'/path.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        return 'duplicate', None

    exif = exif_info(path)
    tk = takeout_info(path, takeout_index)
    lat = exif.get('latitude') if exif.get('latitude') is not None else tk.get('latitude')
    lon = exif.get('longitude') if exif.get('longitude') is not None else tk.get('longitude')
    geo = geocoder.reverse(lat, lon) if lat is not None and lon is not None else None

    dt = exif.get('date') or tk.get('date')
    year = dt.year if dt else 'SemData'
    country = geo.get('country') if geo else None
    state = geo.get('state') if geo else None
    city = geo.get('city') if geo else None
    resolved = bool(country and state and city and lat is not None and lon is not None)

    is_heic = path.suffix.lower() in {'.heic', '.heif'}
    if resolved:
        stored_name = path.stem + '.jpg' if is_heic else path.name
        target = unique_target(LIB/safe_path_part(country)/safe_path_part(state)/safe_path_part(city)/str(year)/stored_name)
    elif lat is not None and lon is not None:
        stored_name = path.stem + '.jpg' if is_heic else path.name
        target = unique_target(LIB/'_sem_geocoding'/str(year)/stored_name)
    else:
        # Keep unresolved files in their original format for later reprocessing.
        target = unique_target(PEND/path.name)

    target.parent.mkdir(parents=True, exist_ok=True)
    converted_from = None
    if resolved or (lat is not None and lon is not None):
        if is_heic:
            convert_heic_to_jpeg(path, target)
            converted_from = path.suffix.lower()
            archive_original(path, path.name, ROOT, 'processadas')
        else:
            shutil.copy2(str(path), str(target))
            archive_original(path, path.name, ROOT, 'processadas')
    else:
        shutil.move(str(path), str(target))

    rec = create_record(path, ROOT, exif, tk, geo, sha, make_web_path(target, ROOT), converted_from)
    if resolved:
        rec['status'] = 'resolved'
    elif lat is not None and lon is not None:
        rec['status'] = 'coordinates_only'
        rec['notes'].append('GPS encontrado, mas reverse geocoding não retornou país/estado/cidade.')
    else:
        rec['status'] = 'pending'
        rec['notes'].append('Nenhuma coordenada encontrada no EXIF nem no Google Takeout correspondente.')
    catalog['photos'].append(rec)
    existing_by_hash[sha] = rec
    return rec['status'], rec


def main():
    catalog = load_json(CATALOG_PATH, {'version': 2, 'photos': []})
    catalog.setdefault('photos', [])
    existing_by_hash = {p.get('sha256'): p for p in catalog.get('photos', []) if p.get('sha256')}
    takeout_index = build_takeout_index(TAKEOUT)
    geocoder = Geocoder(CFG['geocoder'], ROOT)
    files = [p for p in INPUT.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    print(f'Fotos encontradas: {len(files)}')
    print(f'Google Takeout: {takeout_index["json_count"]} JSON(s), {takeout_index["record_count"]} registro(s) indexado(s)')
    added = dupes = pending = coordinates_only = errors = 0
    for i, path in enumerate(files, 1):
        print(f'[{i}/{len(files)}] {path.name}')
        try:
            status, rec = process_one(path, catalog, existing_by_hash, takeout_index, geocoder)
            if status == 'duplicate':
                dupes += 1
                print('  DUPLICATA -> arquivada')
            else:
                added += 1
                pending += status == 'pending'
                coordinates_only += status == 'coordinates_only'
                print(f'  {status} | local: {(rec or {}).get("country") or "-"} / {(rec or {}).get("state") or "-"} / {(rec or {}).get("city") or "-"}')
        except Exception as e:
            errors += 1
            print('  ERRO:', e)
    rebuild_facets(catalog)
    save_json(CATALOG_PATH, catalog)
    print('\nRESUMO')
    print('adicionadas       :', added)
    print('duplicadas        :', dupes)
    print('pendentes         :', pending)
    print('somente coordenadas:', coordinates_only)
    print('erros             :', errors)
    print('total catálogo    :', len(catalog.get('photos', [])))


if __name__ == '__main__':
    main()
