from __future__ import annotations
from typing import Optional
from pathlib import Path
import sys, shutil
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import *
from google_timeline import Timeline

ROOT = Path(__file__).resolve().parents[1]
CFG = load_json(ROOT/'config.json', {})
CATALOG_PATH = ROOT/CFG['catalog_file']
LIB = ROOT/CFG['folders']['library']
PEND = ROOT/CFG['folders']['pending']
TAKEOUT = ROOT/CFG['folders']['takeout']


def actual_path_from_web(root: Path, web_path: Optional[str]):
    if not web_path:
        return None
    return root / web_path.lstrip('/').replace('/', root.anchor if root.anchor else '/') if False else web_path.lstrip('/')


def clean_rel(root: Path, web_path: Optional[str]):
    if not web_path:
        return None
    rel = web_path.lstrip('/').replace('/', '\\') if __import__('os').name == 'nt' else web_path.lstrip('/')
    return root / rel


def main():
    catalog = load_json(CATALOG_PATH, {'version': 2, 'photos': []})
    idx = build_takeout_index(TAKEOUT)
    geocoder = Geocoder(CFG['geocoder'], ROOT)
    tl_cfg = CFG.get('google_timeline', {})
    timeline = Timeline(ROOT / tl_cfg.get('file', 'google_takeout/Timeline.json'), tl_cfg.get('timezone_offset', '-03:00'))
    print(f'Google Takeout: {idx["json_count"]} JSON(s), {idx["record_count"]} registro(s) indexado(s)')
    matched = gps = resolved = moved = skipped = errors = 0
    for rec in catalog.get('photos', []):
        try:
            # We deliberately revisit every record so a later Takeout export can enrich an older catalog.
            fake = Path(rec.get('filename') or '')
            tk = takeout_info(fake, idx)
            if tk.get('json_path'):
                matched += 1
            if tk.get('date') and not rec.get('date'):
                rec['date'] = tk['date'].isoformat(); rec['year'] = tk['date'].year
            # Preserve reliable GPS already stored in the catalog.
            if rec.get('latitude') is not None and rec.get('longitude') is not None:
                continue
            tl = None
            if tk.get('latitude') is None or tk.get('longitude') is None:
                tl = timeline.resolve(rec.get('date') or tk.get('date'))
                if tl:
                    tk = {**tk, 'latitude': tl['latitude'], 'longitude': tl['longitude'], 'source': tl['source']}
            if tk.get('latitude') is None or tk.get('longitude') is None:
                continue
            if tl:
                rec['timeline_match'] = tl
            gps += 1
            rec['latitude'] = tk['latitude']; rec['longitude'] = tk['longitude']
            rec['location_source'] = tl['source'] if tl else f'takeout:{tk.get("source")}'
            rec['metadata_json'] = tk.get('json_path')
            geo = geocoder.reverse(tk['latitude'], tk['longitude'])
            if not geo:
                rec['status'] = 'coordinates_only'
                continue
            rec['country'] = geo.get('country'); rec['country_code'] = geo.get('country_code')
            rec['state'] = geo.get('state'); rec['state_code'] = geo.get('state_code'); rec['city'] = geo.get('city')
            if not (rec['country'] and rec['state'] and rec['city']):
                rec['status'] = 'coordinates_only'
                continue
            rec['status'] = 'resolved'; resolved += 1
            current = clean_rel(ROOT, rec.get('path'))
            if not current or not current.exists():
                # Nothing to move; catalog is still enriched.
                continue
            year = rec.get('year') or (int(rec['date'][:4]) if rec.get('date') else 'SemData')
            target = LIB/safe_path_part(rec['country'])/safe_path_part(rec['state'])/safe_path_part(rec['city'])/str(year)/current.name
            if target.resolve() != current.resolve():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target = target.with_name(current.stem + '_takeout' + current.suffix)
                shutil.move(str(current), str(target))
                rec['path'] = make_web_path(target, ROOT)
                moved += 1
        except Exception as e:
            errors += 1
            rec.setdefault('notes', []).append(f'Aplicar Takeout: {e}')
    rebuild_facets(catalog)
    save_json(CATALOG_PATH, catalog)
    print('\nRESULTADO')
    print('JSON correspondente:', matched)
    print('Segmentos Timeline :', len(timeline.items))
    print('com GPS            :', gps)
    print('resolvidas         :', resolved)
    print('arquivos movidos   :', moved)
    print('erros              :', errors)
    print('catálogo total     :', len(catalog.get('photos', [])))
    print('\nAgora abra/recarregue o site.')


if __name__ == '__main__':
    main()
