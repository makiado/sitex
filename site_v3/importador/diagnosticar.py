from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import *
ROOT=Path(__file__).resolve().parents[1]
CFG=load_json(ROOT/'config.json',{})

def main():
    if len(sys.argv)<2:
        print('Uso: diagnosticar.py "caminho\\foto.jpg"')
        return 2
    photo=Path(sys.argv[1]).expanduser().resolve()
    if not photo.exists():
        print('Arquivo não encontrado:',photo); return 2
    takeout=ROOT/CFG['folders']['takeout']
    idx=build_takeout_index(takeout)
    exif=exif_info(photo)
    tk=takeout_info(photo,idx)
    lat=exif.get('latitude') if exif.get('latitude') is not None else tk.get('latitude')
    lon=exif.get('longitude') if exif.get('longitude') is not None else tk.get('longitude')
    geocoder=Geocoder(CFG['geocoder'],ROOT)
    geo=geocoder.reverse(lat,lon) if lat is not None and lon is not None else None
    print('\n=== DIAGNÓSTICO ===')
    print('Arquivo :',photo)
    print('Tamanho :',photo.stat().st_size,'bytes')
    print('Extensão:',photo.suffix.lower())
    print('\nEXIF')
    print('  Data   :',exif.get('date'))
    print('  GPS    :',exif.get('latitude'),exif.get('longitude'))
    print('  Altitude:',exif.get('altitude'))
    print('  Câmera :',exif.get('camera'))
    print('  Erro   :',exif.get('error'))
    print('\nGOOGLE TAKEOUT')
    print('  JSON   :',tk.get('json_path'))
    print('  Título :',tk.get('title'))
    print('  Data   :',tk.get('date'))
    print('  GPS    :',tk.get('latitude'),tk.get('longitude'))
    print('  Fonte GPS:',tk.get('source'))
    print('  JSONs indexados:',idx.get('json_count'))
    print('  Registros indexados:',idx.get('record_count'))
    print('\nRESULTADO')
    print('  GPS final:',lat,lon)
    print('  Local final:',json.dumps(geo,ensure_ascii=False,indent=2) if geo else 'não resolvido')
    if lat is None or lon is None: print('  STATUS: PENDENTE — não há coordenadas no arquivo nem no Takeout associado.')
    elif not geo or geo.get('error'): print('  STATUS: COORDENADAS ENCONTRADAS — reverse geocoding não retornou endereço.')
    else: print('  STATUS: OK')
    return 0
if __name__=='__main__': raise SystemExit(main())
