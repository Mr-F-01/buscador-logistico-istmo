import streamlit as st
import folium
import json
import base64
import pandas as pd
from geopy.distance import geodesic
from routing.ruta_maritima import calcular_ruta_maritima

st.set_page_config(page_title="Buscador Logístico CIIT", layout="wide")

# ---------- Fondo con imagen ----------
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
            padding: 1rem 1.2rem;
            border-radius: 16px;
            color: #f2f2f2;
        }}
        </style>
        """, unsafe_allow_html=True)
    except Exception:
        pass

set_bg()

# ---------- Datos ----------
with open("data/ports.json") as f:
    PORTS = json.load(f)
with open("data/nodes.json") as f:
    NODES = json.load(f)

def km(a_latlon, b_latlon):
    return geodesic(a_latlon, b_latlon).km

st.markdown("<div class='glass'><h2>Buscador Logístico CIIT (Prototipo)</h2><p>Intermodal: mar (SeaRoute), tren CIIT y carretera. Traza línea de color de punto a punto.</p></div>", unsafe_allow_html=True)

col1, col2 = st.columns([1,2])

with col1:
    st.markdown("<div class='glass'><h4>1) Selecciones</h4></div>", unsafe_allow_html=True)
    origen = st.selectbox("Puerto origen (mar)", list(PORTS.keys()), index=list(PORTS.keys()).index("Hong Kong") if "Hong Kong" in PORTS else 0)
    entrada_mex = st.selectbox("Entrada a México (puerto)", ["Salina Cruz", "Coatzacoalcos"], index=0)
    usar_ciit = st.checkbox("Usar Tren CIIT (Salina Cruz → Medias Aguas → Coatzacoalcos)", value=True)
    nodo_intermedio = st.selectbox("Nodo intermedio (opcional)", ["(ninguno)"] + list(NODES.keys()), index=1)
    destino_final = st.selectbox("Destino final (puerto/ciudad)", list(PORTS.keys()), index=list(PORTS.keys()).index("Miami") if "Miami" in PORTS else 0)

    color_linea = st.color_picker("Color de la línea de ruta", "#00FF9D")

    st.markdown("<div class='glass'><h4>Velocidades promedio</h4></div>", unsafe_allow_html=True)
    v_mar = st.slider("Mar (km/h)", 10, 45, 30)
    v_tren = st.slider("Tren (km/h)", 30, 100, 60)
    v_road = st.slider("Carretera (km/h)", 40, 110, 70)

with col2:
    # ---------- MAPA ----------
    m = folium.Map(location=(18, -95), zoom_start=5, tiles="CartoDB positron")

    # Puntos en lat,lon
    p_origen_latlon = tuple(PORTS[origen])
    p_entrada_latlon = tuple(PORTS[entrada_mex])
    p_dest_latlon = tuple(PORTS[destino_final])

    # ---------- Segmentos ----------
    segments = []

    # 1) MAR (SeaRoute usa [lon, lat])
    distancia_mar_km, geojson_mar = calcular_ruta_maritima(
        [p_origen_latlon[1], p_origen_latlon[0]],
        [p_entrada_latlon[1], p_entrada_latlon[0]]
    )
    tiempo_mar_h = distancia_mar_km / v_mar
    segments.append({"Modo":"Mar", "Desde": origen, "Hacia": entrada_mex, "Dist_km": round(distancia_mar_km,1), "Tiempo_h": round(tiempo_mar_h,1)})
    folium.GeoJson(geojson_mar, name="Mar", style_function=lambda x: {"color": color_linea, "weight": 5, "opacity": 0.9}).add_to(m)

    # 2) TREN CIIT (si aplica desde Salina)
    last_point = p_entrada_latlon
    points_poly = [p_entrada_latlon]

    if usar_ciit and entrada_mex == "Salina Cruz":
        medias = tuple(NODES["Medias Aguas"])
        coatza = tuple(PORTS["Coatzacoalcos"])

        d1 = km(last_point, medias); t1 = d1 / v_tren
        segments.append({"Modo":"Tren CIIT", "Desde":"Salina Cruz", "Hacia":"Medias Aguas", "Dist_km": round(d1,1), "Tiempo_h": round(t1,1)})

        d2 = km(medias, coatza); t2 = d2 / v_tren
        segments.append({"Modo":"Tren CIIT", "Desde":"Medias Aguas", "Hacia":"Coatzacoalcos", "Dist_km": round(d2,1), "Tiempo_h": round(t2,1)})

        points_poly += [medias, coatza]
        last_point = coatza

    # 3) Nodo intermedio (carretera)
    if nodo_intermedio != "(ninguno)":
        nodo = tuple(NODES[nodo_intermedio])
        d = km(last_point, nodo); t = d / v_road
        segments.append({"Modo":"Carretera", "Desde":"Previo", "Hacia": nodo_intermedio, "Dist_km": round(d,1), "Tiempo_h": round(t,1)})
        points_poly += [nodo]
        last_point = nodo

    # 4) Tramo final (para demo lo tratamos como mar puerto-puerto)
    d_final = km(last_point, p_dest_latlon)
    t_final = d_final / v_mar
    segments.append({"Modo":"Mar", "Desde":"Previo", "Hacia": destino_final, "Dist_km": round(d_final,1), "Tiempo_h": round(t_final,1)})
    points_poly += [p_dest_latlon]

    # Dibujo polilínea para tramos NO marítimos (tren/carretera)
    if len(points_poly) >= 2:
        folium.PolyLine(points_poly, color=color_linea, weight=5, opacity=0.9).add_to(m)

    # Marcadores
    for pt in points_poly:
        folium.CircleMarker(location=pt, radius=5, fill=True).add_to(m)

    st.markdown("<div class='glass'><h4>2) Mapa de ruta</h4></div>", unsafe_allow_html=True)
    st.components.v1.html(m._repr_html_(), height=600, scrolling=False)

    # ---------- Tabla y totales ----------
    st.markdown("<div class='glass'><h4>3) Tiempos y distancias por segmento</h4></div>", unsafe_allow_html=True)
    df = pd.DataFrame(segments)
    st.dataframe(df)

    total_km = round(df["Dist_km"].sum(), 1)
    total_h = round(df["Tiempo_h"].sum(), 1)
    total_d = round(total_h/24, 1)
    st.markdown(f"<div class='glass'><h4>Total</h4><p><b>{total_km} km</b> · <b>{total_h} h</b> (~{total_d} días)</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'><small>Nota: Prototipo. Para operación real: integrar tarifas y horarios oficiales (navieras/ferrocarril/carretera) y modelar costos por segmento.</small></div>", unsafe_allow_html=True)
