"""Resolve photo capture times against Google Maps Timeline (on-device export)."""
from __future__ import annotations
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import re

GEO = re.compile(r'^geo:([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)$')


def coords(value):
    if isinstance(value, str):
        m = GEO.fullmatch(value.strip())
        if m:
            lat, lon = map(float, m.groups())
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat or lon):
                return lat, lon
    return None


def utc_seconds(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError('Datetime sem fuso horario')
        return value.timestamp()
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()


class Timeline:
    def __init__(self, path: Path, timezone_offset='-03:00'):
        self.path = Path(path)
        self.items = []
        self.starts = []
        self.offset = timezone_offset
        if not self.path.is_file():
            return
        with self.path.open(encoding='utf-8-sig') as stream:
            raw = json.load(stream)
        if isinstance(raw, dict):
            raw = raw.get('semanticSegments', raw.get('timelineObjects', []))
        if not isinstance(raw, list):
            raise ValueError('Timeline.json nao contem lista de segmentos')
        for obj in raw:
            if not isinstance(obj, dict):
                continue
            try:
                start, end = utc_seconds(obj['startTime']), utc_seconds(obj['endTime'])
                if end < start:
                    continue
                visit = obj.get('visit') or {}
                activity = obj.get('activity') or {}
                candidate = visit.get('topCandidate') or {}
                place = coords(candidate.get('placeLocation'))
                begin = coords(activity.get('start'))
                finish = coords(activity.get('end'))
                if place:
                    kind = 'visit'
                elif begin or finish:
                    kind = 'activity'
                else:
                    continue
                self.items.append((start, end, kind, place, begin, finish))
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        self.items.sort(key=lambda x: (x[0], x[1]))
        self.starts = [x[0] for x in self.items]
        # Handle overlapping segments without scanning the whole timeline for each photo.
        self.prefix_end = []
        latest = float('-inf')
        for item in self.items:
            latest = max(latest, item[1])
            self.prefix_end.append(latest)

    def _as_utc(self, dt):
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            sign = -1 if self.offset.startswith('-') else 1
            hh, mm = map(int, self.offset.lstrip('+-').split(':'))
            dt = dt.replace(tzinfo=timezone(sign * timedelta(hours=hh, minutes=mm)))
        return dt.timestamp()

    def resolve(self, date):
        if not date or not self.items:
            return None
        t = self._as_utc(date)
        i = bisect_right(self.starts, t) - 1
        matches = []
        while i >= 0 and self.prefix_end[i] >= t:
            start, end, kind, place, begin, finish = self.items[i]
            if start <= t <= end:
                if kind == 'visit':
                    lat, lon = place
                elif begin and finish and end > start:
                    ratio = max(0., min(1., (t-start)/(end-start)))
                    lat = begin[0] + ratio*(finish[0]-begin[0])
                    lon = begin[1] + ratio*(finish[1]-begin[1])
                else:
                    lat, lon = begin or finish
                matches.append((kind == 'visit', -(end-start), lat, lon, kind, start, end))
            i -= 1
        if not matches:
            return None
        # A stationary visit is more meaningful than an overlapping journey.
        best = max(matches)
        return {'latitude': best[2], 'longitude': best[3],
                'source': 'google_timeline:' + best[4],
                'interval_start': datetime.fromtimestamp(best[5], timezone.utc).isoformat(),
                'interval_end': datetime.fromtimestamp(best[6], timezone.utc).isoformat(),
                'estimated': best[4] == 'activity'}
