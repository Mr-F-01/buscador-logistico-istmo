import pandas as pd
import json
from pathlib import Path

DATA = Path("data")

def _norm(s: str) -> str:
    return " ".join(str(s).strip().split())

def _to_latlon(row, lat_key="Lat", lon_key="Lon"):
    return [float(row[lat_key]), float(row[lon_key])]

def load_mex_ports():
    """
    Lee data/Puertos_principales_de_carga_de_Mexico.csv
    y devuelve dict: {nombre: [lat, lon]}
    Ajusta aquí los nombres exactos de tus columnas si difieren.
    """
    f = DATA / "Puertos_principales_de_carga_de_Mexico.csv"
    df = pd.read_csv(f)
    # <-- Si tus encabezados son distintos, edítalos aquí:
    name_col, lat_col, lon_col = "Nombre", "Lat", "Lon"
    df[name_col] = df[name_col].map(_norm)
    return {row[name_col]: _to_latlon(row, lat_col, lon_col) for _, row in df.iterrows()}

def load_world_ports():
    """
    Lee data/Puertos_mundiales_con_fuerte_vinculo_con_America_WSC_2023.csv
    y devuelve dict: {nombre: [lat, lon]}
    """
    f = DATA / "Puertos_mundiales_con_fuerte_vinculo_con_America_WSC_2023.csv"
    df = pd.read_csv(f)
    name_col, lat_col, lon_col = "Nombre", "Lat", "Lon"
    df[name_col] = df[name_col].map(_norm)
    return {row[name_col]: _to_latlon(row, lat_col, lon_col) for _, row in df.iterrows()}

def merge_ports(base_json="data/ports.json"):
    """
    Combina ports.json (si existe) + puertos México + puertos mundo.
    """
    base = {}
    if Path(base_json).exists():
        with open(base_json) as f:
            base = json.load(f)
    pmx = load_mex_ports()
    pworld = load_world_ports()
    merged = dict(base)
    for d in (pmx, pworld):
        for k, v in d.items():
            if k not in merged:
                merged[k] = v
    return merged
