# app.py
import streamlit as st
from streamlit_folium import st_folium

from modules.history_data import HISTORICAL_NOTES, SAMPLE_GEOJSON
from modules.data_loader import load_default_data, validate_and_load_uploaded_file
from modules.map_builder import create_map

st.set_page_config(
    page_title="Mapa Interactivo: Para, Hazar y Ogur",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Mapa Geográfico e Histórico: Para, Hazar y Ogur")

# Inicialización de estado de datos
if "gdf" not in st.session_state:
    st.session_state.gdf = load_default_data(SAMPLE_GEOJSON)

# --- BARRA LATERAL: CONFIGURACIÓN Y FILTROS ---
st.sidebar.header("⚙️ Configuración y Filtros")

# 1. Selección de Mapa de Fondo
tile_choice = st.sidebar.selectbox(
    "Mapa de Fondo (Tile Layer):",
    ["CartoDB Positron (Recomendado)", "OpenStreetMap", "Sin Mapa de Fondo"]
)

st.sidebar.divider()

# 2. Carga de Archivos Propios
st.sidebar.subheader("📤 Cargar Datos Propios")
uploaded_file = st.sidebar.file_uploader(
    "Sube un archivo GeoJSON o CSV:",
    type=["geojson", "json", "csv"]
)

if uploaded_file is not None:
    new_gdf, message = validate_and_load_uploaded_file(uploaded_file)
    if new_gdf is not None:
        st.session_state.gdf = new_gdf
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)

st.sidebar.divider()

# 3. Filtros Avanzados
st.sidebar.subheader("🔍 Filtros de Visualización")

# Buscador por texto
search_query = st.sidebar.text_input("Buscar por nombre:", "")

# Filtro por tipo de geometría
available_geoms = list(st.session_state.gdf["tipo_geometria"].unique()) if not st.session_state.gdf.empty else []
selected_geoms = st.sidebar.multiselect(
    "Filtrar por Tipo de Geometría:",
    options=available_geoms,
    default=available_geoms
)

# Aplicar filtros
filtered_gdf = st.session_state.gdf.copy()

if search_query:
    filtered_gdf = filtered_gdf[filtered_gdf["nombre"].str.contains(search_query, case=False, na=False)]

if selected_geoms:
    filtered_gdf = filtered_gdf[filtered_gdf["tipo_geometria"].isin(selected_geoms)]

# --- NAVEGACIÓN POR PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Interactivo", "📚 Notas Históricas y Etimológicas", "📥 Descarga de Datos"])

# PESTAÑA 1: MAPA
with tab1:
    st.caption("Usa el zoom, desplazamiento y haz clic sobre las geometrías para abrir la ventana emergente.")
    map_obj = create_map(filtered_gdf, selected_tile=tile_choice)
    st_folium(map_obj, width="100%", height=550)

# PESTAÑA 2: NOTAS HISTÓRICAS Y ETIMOLÓGICAS
with tab2:
    st.header("📚 Contexto Histórico y Etimología")
    st.info("💡 Las siguientes notas documentan las fuentes y desacuerdos académicos para evitar presentar hipótesis como hechos definitivos.")

    for group, info in HISTORICAL_NOTES.items():
        with st.expander(f"📌 Grupo / Término: **{group}**"):
            st.markdown(f"**Etimología:** {info['etymology']}")
            st.markdown(f"**Contexto Histórico:** {info['context']}")
            st.markdown("**Fuentes Bibliográficas:**")
            for source in info["sources"]:
                st.markdown(f"- *{source}*")

# PESTAÑA 3: DESCARGAS
with tab3:
    st.header("📥 Descarga de Datos Filtrados")
    st.write(f"Total de registros filtrados: **{len(filtered_gdf)}**")
    
    st.dataframe(filtered_gdf.drop(columns="geometry", errors="ignore"))

    col1, col2 = st.columns(2)
    
    # Exportar a GeoJSON
    geojson_bytes = filtered_gdf.to_json().encode('utf-8')
    col1.download_button(
        label="📄 Descargar datos en GeoJSON",
        data=geojson_bytes,
        file_name="datos_para_hazar_ogur.geojson",
        mime="application/geo+json"
    )

    # Exportar a CSV (descartando temporalmente objetos de geometría complejos)
    csv_bytes = filtered_gdf.drop(columns="geometry", errors="ignore").to_csv(index=False).encode('utf-8')
    col2.download_button(
        label="📊 Descargar datos en CSV",
        data=csv_bytes,
        file_name="datos_para_hazar_ogur.csv",
        mime="text/csv"
    )