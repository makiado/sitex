from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from PIL import Image, ImageOps, ExifTags

IMAGE_EXTS = {'.jpg','.jpeg','.png','.webp','.tif','.tiff','.heic','.heif','.bmp','.gif'}


def ensure_heif_support():
    """Register HEIF/HEIC support when pillow-heif is installed."""
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        return True
    except Exception:
        return False


ensure_heif_support()


def load_json(path: Path, default):
    try:
        with path.open('r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def sha256(path: Path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def normalize_name(name: str) -> str:
    s = Path(name).name.casefold().strip()
    s = re.sub(r'\s+\(\d+\)(?=\.[^.]+$)', '', s)
    return s


def normalize_stem(name: str) -> str:
    """Normalize a filename without extension, tolerant of Takeout suffixes."""
    s = normalize_name(name)
    s = re.sub(r'\.[^.]+$', '', s)
    s = re.sub(r'\s+\(\d+\)$', '', s).strip()
    return s


def parse_timestamp_value(value: Any):
    if value is None:
        return None
    try:
        if isinstance(value, dict):
            for k in ('timestamp', 'formatted', 'value'):
                if k in value:
                    return parse_timestamp_value(value[k])
        if isinstance(value, (int, float)):
            if value > 10_000_000_000:
                value = value / 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        s = str(value).strip()
        if not s:
            return None
        if s.isdigit():
            return parse_timestamp_value(int(s))
        s2 = s.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(s2)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            pass
        for fmt in (
            '%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'
        ):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
    except Exception:
        return None
    return None


def _rational_to_float(x):
    try:
        if isinstance(x, tuple) and len(x) == 2:
            return float(x[0]) / float(x[1]) if x[1] else 0.0
        if hasattr(x, 'numerator') and hasattr(x, 'denominator'):
            return float(x.numerator) / float(x.denominator) if x.denominator else 0.0
        return float(x)
    except Exception:
        return None


def gps_to_decimal(raw):
    try:
        if isinstance(raw, (tuple, list)) and len(raw) >= 3:
            vals = [_rational_to_float(v) for v in raw[:3]]
            if None in vals:
                return None
            return vals[0] + vals[1] / 60 + vals[2] / 3600
    except Exception:
        pass
    return None


def exif_info(path: Path):
    result = {
        'date': None, 'latitude': None, 'longitude': None, 'altitude': None,
        'camera': None, 'raw_exif': {}, 'error': None
    }
    try:
        ensure_heif_support()
        with Image.open(path) as im:
            exif = im.getexif()
            if not exif:
                return result
            decoded = {}
            for k, v in exif.items():
                decoded[ExifTags.TAGS.get(k, str(k))] = v
            result['raw_exif'] = {
                k: str(v)[:500] for k, v in decoded.items()
                if k in {'DateTimeOriginal', 'DateTime', 'DateTimeDigitized', 'Make', 'Model', 'GPSInfo', 'Software', 'ImageDescription', 'Artist', 'XPTitle'}
            }
            for key in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                if key in decoded and not result['date']:
                    result['date'] = parse_timestamp_value(decoded[key])
            if 'Make' in decoded or 'Model' in decoded:
                result['camera'] = ' '.join(str(x) for x in (decoded.get('Make'), decoded.get('Model')) if x)
            gps = None
            try:
                gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
            except Exception:
                gps = None
            if gps:
                gps_dec = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
                lat = gps_to_decimal(gps_dec.get('GPSLatitude'))
                lon = gps_to_decimal(gps_dec.get('GPSLongitude'))
                if lat is not None and lon is not None:
                    if str(gps_dec.get('GPSLatitudeRef', 'N')).upper() == 'S':
                        lat = -abs(lat)
                    if str(gps_dec.get('GPSLongitudeRef', 'E')).upper() == 'W':
                        lon = -abs(lon)
                    if -90 <= lat <= 90 and -180 <= lon <= 180 and (abs(lat) > 1e-9 or abs(lon) > 1e-9):
                        result['latitude'], result['longitude'] = lat, lon
                alt = _rational_to_float(gps_dec.get('GPSAltitude'))
                if alt is not None:
                    result['altitude'] = alt
    except Exception as e:
        result['error'] = str(e)
    return result


def convert_heic_to_jpeg(src: Path, dest: Path):
    """Convert HEIC/HEIF to web-compatible JPEG for the website."""
    ensure_heif_support()
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, 'JPEG', quality=95, optimize=True, progressive=True)
    return dest


def walk_jsons(root: Path):
    if not root.exists():
        return
    for p in root.rglob('*.json'):
        if p.is_file():
            yield p


def recursively_find_coords(obj: Any):
    if isinstance(obj, dict):
        for key in ('geoDataExif', 'geoData', 'location', 'geoDataList', 'geoDataFromExif'):
            if key in obj:
                yield from _extract_coord_container(obj[key], key)
        lat = obj.get('latitude', obj.get('lat'))
        lon = obj.get('longitude', obj.get('lon', obj.get('lng')))
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if abs(lat) <= 90 and abs(lon) <= 180 and (abs(lat) > 1e-9 or abs(lon) > 1e-9):
                yield float(lat), float(lon), 'generic'
        for v in obj.values():
            if isinstance(v, (dict, list)):
                yield from recursively_find_coords(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from recursively_find_coords(v)


def _extract_coord_container(v, source):
    if isinstance(v, dict):
        lat = v.get('latitude', v.get('lat'))
        lon = v.get('longitude', v.get('lon', v.get('lng')))
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if abs(lat) <= 90 and abs(lon) <= 180 and (abs(lat) > 1e-9 or abs(lon) > 1e-9):
                yield float(lat), float(lon), source
        for vv in v.values():
            if isinstance(vv, (dict, list)):
                yield from _extract_coord_container(vv, source)
    elif isinstance(v, list):
        for item in v:
            yield from _extract_coord_container(item, source)


def _metadata_objects(obj: Any):
    """Yield every dict that looks like a photo metadata record, even if nested."""
    if isinstance(obj, dict):
        keys = set(obj)
        looks_like_photo = bool(keys & {
            'title', 'filename', 'fileName', 'photoTakenTime', 'creationTime',
            'geoDataExif', 'geoData', 'description'
        })
        if looks_like_photo:
            yield obj
        for value in obj.values():
            if isinstance(value, (dict, list)):
                yield from _metadata_objects(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _metadata_objects(value)


def _metadata_names(obj: dict, json_path: Path):
    names = []
    for k in ('title', 'filename', 'fileName', 'name'):
        if isinstance(obj.get(k), str) and obj[k].strip():
            names.append(obj[k])
    # Takeout commonly creates FILE.jpg.json without a useful top-level title.
    stem = json_path.stem
    if stem.lower().endswith(tuple(IMAGE_EXTS)):
        names.append(stem)
    return names


def build_takeout_index(root: Path, limit=500000):
    """Build exact-name and stem indexes for Google Takeout metadata.

    Returns {"by_name": ..., "json_count": ..., "record_count": ...}.
    """
    by_name = {}
    json_count = 0
    record_count = 0
    for p in walk_jsons(root):
        json_count += 1
        try:
            obj = load_json(p, None)
            if not isinstance(obj, (dict, list)):
                continue
            for rec in _metadata_objects(obj):
                names = _metadata_names(rec, p)
                if not names:
                    continue
                for n in names:
                    by_name.setdefault(normalize_name(n), []).append((p, rec))
                    by_name.setdefault('stem:' + normalize_stem(n), []).append((p, rec))
                    record_count += 1
                    if record_count >= limit:
                        return {'by_name': by_name, 'json_count': json_count, 'record_count': record_count}
        except Exception:
            continue
        # If this is a per-photo JSON with no recognizable record, still make it searchable by filename.
        if p.stem.lower().endswith(tuple(IMAGE_EXTS)):
            by_name.setdefault(normalize_name(p.stem), []).append((p, {}))
            by_name.setdefault('stem:' + normalize_stem(p.stem), []).append((p, {}))
    return {'by_name': by_name, 'json_count': json_count, 'record_count': record_count}


def _takeout_candidates(photo_path: Path, index: dict):
    idx = index.get('by_name', index)
    seen = set()
    keys = [normalize_name(photo_path.name), 'stem:' + normalize_stem(photo_path.name)]
    # Edited Takeout files can gain a suffix; try normalized variants as well.
    alt_stem = re.sub(r'([_-](edited|original|copy))$', '', normalize_stem(photo_path.name))
    if alt_stem and alt_stem != normalize_stem(photo_path.name):
        keys.append('stem:' + alt_stem)
    for key in keys:
        for item in idx.get(key, []):
            ident = (str(item[0]), id(item[1]))
            if ident not in seen:
                seen.add(ident)
                yield item


def find_json_metadata(photo_path: Path, index: dict):
    best = None
    best_score = -1
    target_name = normalize_name(photo_path.name)
    target_stem = normalize_stem(photo_path.name)
    for p, obj in _takeout_candidates(photo_path, index):
        score = 0
        names = _metadata_names(obj, p) if isinstance(obj, dict) else []
        normalized_names = {normalize_name(n) for n in names}
        normalized_stems = {normalize_stem(n) for n in names}
        if target_name in normalized_names:
            score += 50
        if target_stem in normalized_stems:
            score += 30
        if p.parent == photo_path.parent:
            score += 3
        coords = list(recursively_find_coords(obj)) if isinstance(obj, (dict, list)) else []
        if coords:
            score += 10
        if isinstance(obj, dict) and any(k in obj for k in ('photoTakenTime', 'creationTime')):
            score += 3
        if score > best_score:
            best_score = score
            best = (p, obj)
    return best


def takeout_info(photo_path: Path, index):
    match = find_json_metadata(photo_path, index)
    result = {'json_path': None, 'date': None, 'latitude': None, 'longitude': None, 'source': None, 'title': None}
    if not match:
        return result
    p, obj = match
    result['json_path'] = str(p)
    if isinstance(obj, dict):
        result['title'] = obj.get('title') or obj.get('filename') or obj.get('fileName')
        for k in ('photoTakenTime', 'creationTime', 'creation', 'date'):
            if k in obj:
                dt = parse_timestamp_value(obj[k])
                if dt:
                    result['date'] = dt
                    break
        found = list(recursively_find_coords(obj))
    else:
        found = []
    if found:
        priority = {'geoDataExif': 4, 'geoDataFromExif': 4, 'geoData': 3, 'generic': 2, 'location': 1, 'geoDataList': 1}
        found.sort(key=lambda t: priority.get(t[2], 0), reverse=True)
        lat, lon, src = found[0]
        result['latitude'], result['longitude'], result['source'] = lat, lon, src
    return result


def safe_path_part(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(s)).strip().strip('.')
    return s[:120] or 'Desconhecido'


def make_web_path(path: Path, root: Path):
    rel = path.relative_to(root).as_posix()
    return '/' + quote(rel, safe='/@-_.~()')


def infer_year(dt):
    return dt.year if dt else None


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class Geocoder:
    def __init__(self, cfg: dict, root: Path):
        self.cfg = cfg
        self.cache_path = root / cfg['cache_file']
        self.cache = load_json(self.cache_path, {})
        self.last_call = 0.0

    def save(self):
        save_json(self.cache_path, self.cache)

    def reverse(self, lat, lon):
        if not self.cfg.get('enabled', True):
            return None
        key = f'{lat:.5f},{lon:.5f}'
        if key in self.cache and isinstance(self.cache[key], dict) and 'error' not in self.cache[key]:
            return self.cache[key]
        wait = self.cfg.get('delay_seconds', 1.05) - (time.time() - self.last_call)
        if wait > 0:
            time.sleep(wait)
        params = f'?lat={lat}&lon={lon}&format=jsonv2&addressdetails=1&accept-language={quote(self.cfg.get("language", "pt-BR"))}'
        url = self.cfg.get('url') + params
        req = Request(url, headers={'User-Agent': self.cfg.get('user_agent', 'site-memorias/1.0')})
        try:
            with urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode('utf-8'))
            self.last_call = time.time()
            addr = data.get('address', {})
            result = {
                'display_name': data.get('display_name'),
                'country': addr.get('country'),
                'country_code': (addr.get('country_code') or '').upper(),
                'state': addr.get('state') or addr.get('region') or addr.get('province'),
                'state_code': addr.get('ISO3166-2-lvl4'),
                'city': addr.get('city') or addr.get('town') or addr.get('municipality') or addr.get('village') or addr.get('suburb'),
                'postcode': addr.get('postcode')
            }
            self.cache[key] = result
            self.save()
            return result
        except (HTTPError, URLError, TimeoutError, ConnectionError, ValueError) as e:
            self.last_call = time.time()
            self.cache[key] = {'error': str(e)}
            self.save()
            return None
        except Exception as e:
            self.last_call = time.time()
            self.cache[key] = {'error': str(e)}
            self.save()
            return None


def create_record(img_path, root, exif, tk, geo, sha, stored_path=None, converted_from=None):
    dt = exif.get('date') or tk.get('date')
    lat = exif.get('latitude') if exif.get('latitude') is not None else tk.get('latitude')
    lon = exif.get('longitude') if exif.get('longitude') is not None else tk.get('longitude')
    if exif.get('latitude') is not None:
        locsrc = 'exif'
    elif tk.get('latitude') is not None:
        locsrc = f'takeout:{tk.get("source")}'
    else:
        locsrc = None
    country = state = city = cc = sc = None
    if geo:
        country = geo.get('country')
        cc = geo.get('country_code')
        state = geo.get('state')
        sc = geo.get('state_code')
        city = geo.get('city')
    return {
        'id': sha[:20], 'filename': img_path.name,
        'path': stored_path, 'original_path': str(img_path.relative_to(root)),
        'sha256': sha, 'extension': img_path.suffix.lower(),
        'mime_type': mimetypes.guess_type(stored_path or img_path.name)[0],
        'date': dt.isoformat() if dt else None, 'year': infer_year(dt),
        'latitude': lat, 'longitude': lon, 'altitude': exif.get('altitude'),
        'country': country, 'country_code': cc, 'state': state, 'state_code': sc, 'city': city,
        'location_source': locsrc, 'metadata_json': tk.get('json_path'),
        'camera': exif.get('camera'), 'converted_from': converted_from,
        'status': 'resolved' if lat is not None and lon is not None and country and state and city else ('coordinates_only' if lat is not None and lon is not None else 'pending'),
        'imported_at': utc_now_iso(), 'notes': []
    }


def rebuild_facets(catalog):
    photos = catalog.get('photos', [])
    catalog['countries'] = sorted({p.get('country') for p in photos if p.get('country')})
    catalog['states'] = sorted({p.get('state') for p in photos if p.get('state')})
    catalog['years'] = sorted({p.get('year') for p in photos if p.get('year')}, reverse=True)
    catalog['cities'] = sorted({p.get('city') for p in photos if p.get('city')})
    catalog['generated_at'] = utc_now_iso()
    return catalog
