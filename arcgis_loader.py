import requests
import json
from functools import lru_cache

BASE = "https://services6.arcgis.com/ZP95JslokqLi5f3i/arcgis/rest/services/Vías_ferroviarias/FeatureServer/0/query"

COMMON = {
    "where": "1=1",
    "outFields": "*",           # puedes reducir a campos necesarios p.ej. "Nombre"
    "f": "geojson",
    "outSR": 4326,              # WGS84
    "returnGeometry": "true",
    "geometryPrecision": 5      # reduce tamaño (5 decimales ~ 1 m)
}

PAGE_SIZE = 2000  # típico límite de ArcGIS

def _page(offset: int):
    params = dict(COMMON)
    params["resultOffset"] = offset
    params["resultRecordCount"] = PAGE_SIZE
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

@lru_cache(maxsize=1)
def fetch_rail_geojson():
    """
    Descarga TODA la red ferroviaria paginada y devuelve un FeatureCollection.
    Cacheada en memoria para evitar re-llamadas constantes.
    """
    features = []
    offset = 0
    while True:
        data = _page(offset)
        batch = data.get("features", [])
        if not batch:
            break
        features.extend(batch)
        # Si el servicio indica que hay más:
        if not data.get("exceededTransferLimit") and len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return {
        "type": "FeatureCollection",
        "features": features
    }
