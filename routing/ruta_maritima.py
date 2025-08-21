import searoute as sr

def calcular_ruta_maritima(origen_lonlat, destino_lonlat):
    """
    Usa SeaRoute para calcular la ruta marítima real.
    Parámetros:
      - origen_lonlat = [lon, lat]
      - destino_lonlat = [lon, lat]
    Retorna:
      - (distancia_km: float, geojson: dict)
    """
    ruta = sr.searoute(origen_lonlat, destino_lonlat)
    distancia_km = ruta["properties"]["length"]
    return distancia_km, ruta
