import streamlit as st
import folium, json, base64
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from routing.ruta_maritima import calcular_ruta_maritima

st.set_page_config(page_title="Buscador Logístico CIIT", layout="wide")

# ---- Estilos y fondo ----
def set_bg(img_path="data/bg_mapa_medial.jpg"):
    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background: url("data:image/jpg;base64,{b64}") no-repeat center center fixed;
            background-size: cover;
        }}
        .glass {{
            background: rgba(0,0,0,0.45);
            padding: 1rem 1.2rem; border-radius: 16px; color: #f2f2f2;
        }}
        </style>
        """, unsafe_allow_html=True)
    except Exception:
        pass

set_bg()

# ---- Datos ----
with open("data/ports.json") as f: PORTS = json.load(f)
with open("data/nodes.json") as f: NODES = json.load(f)
with open("data/rail_network.geojson") as f: RAIL = json.load(f)

# Colores por modo
MAR_COLOR = "#1f77b4"     # azul
RAIL_COLOR = "#ff7f0e"    # naranja
ROAD_COLOR = "#2ca02c"    # verde
RAIL_BASE = "#B0B0B0"     # gris red general

def km(a_latlon, b_latlon):
    return geodesic(a_latlon, b_latlon).km

def geocode_point(query:str, fallback=None):
    """Devuelve (lat, lon). Si falla, usa fallback (lat, lon)."""
    try:
        geolocator = Nominatim(user_agent="ciit-logistica")
        loc = geolocator.geocode(query, timeout=10)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception:
        pass
    return fallback

st.markdown("<div class='glass'><h2>Buscador Logístico CIIT (Prototipo)</h2><p>Intermodal: Mar (SeaRoute), Tren CIIT (Línea Z) y Carretera. Rutas por color y red ferroviaria siempre visible.</p></div>", unsafe_allow_html=True)

c1, c2 = st.columns([1,2])

with c1:
    st.markdown("<div class='glass'><h4>1) Parámetros</h4></div>", unsafe_allow_html=True)

    # 1) Entrada a México (solo 2)
    entrada_mex = st.selectbox("Entrada a México (puerto)", ["Salina Cruz","Coatzacoalcos"], index=0)

    # 2) Puerto de origen (mundo) con buscador + lista rápida
    st.write("**Puerto de origen (mundo)**")
    origen_quick = st.selectbox("Rápido", list(PORTS.keys()), index=list(PORTS.keys()).index("Hong Kong"))
    origen_text = st.text_input("O escribe ciudad/puerto (global)", value="")
    # coordenadas origen (prioriza texto si lo dan)
    p_origen_latlon = None
    if origen_text.strip():
        p_origen_latlon = geocode_point(origen_text.strip(), fallback=tuple(PORTS[origen_quick]))
    else:
        p_origen_latlon = tuple(PORTS[origen_quick])

    # 3) Destino final
    dest_tipo = st.radio("Destino final", ["Puerto internacional","México (estado/ciudad)"], horizontal=True)
    p_dest_latlon = None
    if dest_tipo == "Puerto internacional":
        dest_quick = st.selectbox("Puerto destino (mundo)", list(PORTS.keys()), index=list(PORTS.keys()).index("Miami"))
        dest_text = st.text_input("O escribe ciudad/puerto", value="")
        if dest_text.strip():
            p_dest_latlon = geocode_point(dest_text.strip(), fallback=tuple(PORTS[dest_quick]))
        else:
            p_dest_latlon = tuple(PORTS[dest_quick])
    else:
        destino_mx_quick = st.selectbox("Ciudad/Estado en México", ["Veracruz","Puebla","Querétaro","Monterrey","Nuevo Laredo","Tijuana"])
        dest_text_mx = st.text_input("O escribe ciudad/estado de México", value="")
        base = tuple(NODES.get(destino_mx_quick, NODES["Veracruz"]))
        p_dest_latlon = geocode_point(dest_text_mx if dest_text_mx.strip() else destino_mx_quick, fallback=base)

    # 4) Nodo intermedio (opcional)
    nodo_intermedio = st.selectbox("Nodo intermedio (descarga opcional)", ["(ninguno)"] + list(NODES.keys()))

    # 5) Velocidades
    st.markdown("<div class='glass'><h4>Velocidades promedio</h4></div>", unsafe_allow_html=True)
    v_mar = st.slider("Mar (km/h)", 10, 45, 30)
    v_tren = st.slider("Tren (km/h)", 30, 100, 60)
    v_road = st.slider("Carretera (km/h)", 40, 110, 70)

with c2:
    # ---- Mapa base ----
    m = folium.Map(location=(19,-96), zoom_start=5, tiles="CartoDB positron")

    # Red ferroviaria en gris (siempre visible)
    folium.GeoJson(RAIL, name="Red Ferroviaria MX", style_function=lambda x: {"color": RAIL_BASE, "weight": 2, "opacity": 0.8}).add_to(m)

    segments = []

    # ---- 1) Mar: origen -> entrada_mex (SeaRoute) ----
    p_entrada_latlon = tuple(PORTS[entrada_mex])
    # SeaRoute usa [lon,lat]
    dist_mar_km, geojson_mar = calcular_ruta_maritima(
        [p_origen_latlon[1], p_origen_latlon[0]],
        [p_entrada_latlon[1], p_entrada_latlon[0]]
    )
    t_mar_h = dist_mar_km / v_mar
    segments.append({"Modo":"Mar", "Desde":"Origen", "Hacia":entrada_mex, "Dist_km": round(dist_mar_km,1), "Tiempo_h": round(t_mar_h,1)})
    folium.GeoJson(geojson_mar, name="Mar", style_function=lambda x: {"color": MAR_COLOR, "weight": 4, "opacity": 0.9}).add_to(m)

    # ---- 2) Tren (CIIT) dentro del Istmo ----
    points_rail = [p_entrada_latlon]
    if entrada_mex == "Salina Cruz":
        medias = tuple(NODES["Medias Aguas"])
        coatza = tuple(PORTS["Coatzacoalcos"])
        d1 = km(p_entrada_latlon, medias); t1 = d1/v_tren
        d2 = km(medias, coatza); t2 = d2/v_tren
        segments += [
            {"Modo":"Tren CIIT","Desde":"Salina Cruz","Hacia":"Medias Aguas","Dist_km":round(d1,1),"Tiempo_h":round(t1,1)},
            {"Modo":"Tren CIIT","Desde":"Medias Aguas","Hacia":"Coatzacoalcos","Dist_km":round(d2,1),"Tiempo_h":round(t2,1)}
        ]
        points_rail += [medias, coatza]
        last_node = coatza
    else:
        # Entró por Coatzacoalcos
        last_node = p_entrada_latlon

    # ---- Nodo intermedio (carretera) si aplica ----
    points_road = []
    if nodo_intermedio != "(ninguno)":
        nodo = tuple(NODES[nodo_intermedio])
        d = km(last_node, nodo); t = d/v_road
        segments.append({"Modo":"Carretera","Desde":"Previo","Hacia":nodo_intermedio,"Dist_km":round(d,1),"Tiempo_h":round(t,1)})
        points_road += [last_node, nodo]
        last_node = nodo

    # ---- 3) Tramo final (si es puerto, mar; si es México, carretera) ----
    if p_dest_latlon:
        if dest_tipo == "Puerto internacional":
            d_final = km(last_node, p_dest_latlon); t_final = d_final/v_mar
            segments.append({"Modo":"Mar","Desde":"Previo","Hacia":"Destino (Puerto)","Dist_km":round(d_final,1),"Tiempo_h":round(t_final,1)})
            # Para dibujo simple de ese tramo final (recta)
            folium.PolyLine([last_node, p_dest_latlon], color=MAR_COLOR, weight=4, opacity=0.9).add_to(m)
        else:
            d_final = km(last_node, p_dest_latlon); t_final = d_final/v_road
            segments.append({"Modo":"Carretera","Desde":"Previo","Hacia":"Destino (MX)","Dist_km":round(d_final,1),"Tiempo_h":round(t_final,1)})
            points_road += [last_node, p_dest_latlon]

    # Dibujos por modo (no marítimo)
    if len(points_rail) > 1:
        folium.PolyLine(points_rail, color=RAIL_COLOR, weight=5, opacity=0.9).add_to(m)
        for pt in points_rail: folium.CircleMarker(location=pt, radius=4, fill=True, color=RAIL_COLOR).add_to(m)
    if len(points_road) > 1:
        folium.PolyLine(points_road, color=ROAD_COLOR, weight=5, opacity=0.9).add_to(m)
        for pt in points_road: folium.CircleMarker(location=pt, radius=4, fill=True, color=ROAD_COLOR).add_to(m)

    st.markdown("<div class='glass'><h4>2) Mapa de ruta</h4></div>", unsafe_allow_html=True)
    st.components.v1.html(m._repr_html_(), height=620, scrolling=False)

    # ---- Tabla ----
    df = pd.DataFrame(segments)
    st.markdown("<div class='glass'><h4>3) Segmentos y totales</h4></div>", unsafe_allow_html=True)
    st.dataframe(df)

    total_km = round(df["Dist_km"].sum(),1) if not df.empty else 0
    total_h = round(df["Tiempo_h"].sum(),1) if not df.empty else 0
    total_d = round(total_h/24,1) if total_h else 0
    st.markdown(f"<div class='glass'><b>Total:</b> {total_km} km · {total_h} h (~{total_d} días)</div>", unsafe_allow_html=True)

    # ---- Comparativo: Istmo vs Carretera ----
    # Carretera directa: desde entrada_mex al destino final
    if p_dest_latlon:
        d_road_direct = km(p_entrada_latlon, p_dest_latlon); t_road_direct = d_road_direct / v_road
        # Istmo ya está calculado (lo que suman los segmentos tras llegar al Istmo)
        # Para una comparación simple: tiempo total actual (con CIIT) VS marítimo+carretera directa
        istmo_total_h = total_h
        road_total_h = round((dist_mar_km/v_mar) + t_road_direct, 1)
        comp = pd.DataFrame([
            {"Ruta":"Vía CIIT (mar+tren+carretera)","Horas": istmo_total_h},
            {"Ruta":"Mar + Carretera directa","Horas": road_total_h}
        ])
        st.bar_chart(comp.set_index("Ruta"))
        st.caption("Comparativo de horas estimadas (promedios configurables).")

