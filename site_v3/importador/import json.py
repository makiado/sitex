import json


def parse_geo(geo_str: str):
  """Converte 'geo:lat,lng' para inteiros latitudeE7 e longitudeE7."""
  if not geo_str or not geo_str.startswith('geo:'):
    return None, None
  parts = geo_str.replace('geo:', '').split(',')
  lat = float(parts[0])
  lng = float(parts[1])
  return int(lat * 1e7), int(lng * 1e7)


def converter_ios_para_takeout(
    caminho_entrada='Timeline.json', caminho_saida='takeout_convertido.json'
):
  with open(caminho_entrada, 'r', encoding='utf-8') as f:
    registros = json.load(f)

  timeline_objects = []

  for item in registros:
    start_time = item.get('startTime')
    end_time = item.get('endTime')

    if 'visit' in item:
      visit = item['visit']
      top = visit.get('topCandidate', {})
      lat_e7, lng_e7 = parse_geo(top.get('placeLocation', ''))

      timeline_objects.append({
          'placeVisit': {
              'location': {
                  'latitudeE7': lat_e7,
                  'longitudeE7': lng_e7,
                  'placeId': top.get('placeID'),
                  'semanticType': top.get('semanticType'),
              },
              'duration': {
                  'startTimestamp': start_time,
                  'endTimestamp': end_time,
              },
          }
      })

    elif 'activity' in item:
      activity = item['activity']
      top = activity.get('topCandidate', {})
      start_lat_e7, start_lng_e7 = parse_geo(activity.get('start', ''))
      end_lat_e7, end_lng_e7 = parse_geo(activity.get('end', ''))
      dist = float(activity.get('distanceMeters', 0))

      timeline_objects.append({
          'activitySegment': {
              'startLocation': {
                  'latitudeE7': start_lat_e7,
                  'longitudeE7': start_lng_e7,
              },
              'endLocation': {
                  'latitudeE7': end_lat_e7,
                  'longitudeE7': end_lng_e7,
              },
              'duration': {
                  'startTimestamp': start_time,
                  'endTimestamp': end_time,
              },
              'activityType': top.get('type'),
              'distance': dist,
          }
      })

  with open(caminho_saida, 'w', encoding='utf-8') as f:
    json.dump({'timelineObjects': timeline_objects}, f, ensure_ascii=False)

  print(
      f'Sucesso: {len(timeline_objects)} itens convertidos em {caminho_saida}'
  )


if __name__ == '__main__':
  converter_ios_para_takeout()