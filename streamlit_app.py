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
=======

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from shapely.geometry import LineString, Point, mapping


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Hazar ve Ogur",
    page_icon="🗺️",
    layout="wide",
)

CRS = "EPSG:4326"

# name, start_lon, start_lat, end_lon, end_lat,
# color, description, label_dx, label_dy
MIGRATIONS = [
    (
        "1. Ujur / Uygur",
        102.0, 47.0, 75.0, 45.0,
        "#2563eb", "Orkhon -> Jetisu", 1.5, 0.8,
    ),
    (
        "2. Tauris",
        34.0, 45.0, 34.0, 45.0,
        "#059669", "Kirim (yerel)", 0.9, -1.7,
    ),
    (
        "3. Avar",
        47.0, 42.0, 19.0, 47.0,
        "#dc2626", "Kafkasya -> Pannonia", 0.9, 0.6,
    ),
    (
        "4. Uauz / Oguz",
        60.0, 43.0, 35.0, 39.0,
        "#d97706", "Aral/Hazar -> Anadolu", 0.9, -1.5,
    ),
    (
        "5. Bizal / Barsil",
        42.0, 48.0, 42.0, 48.0,
        "#7c3aed", "Volga-Don / K. Kafkasya", 1.0, 1.2,
    ),
    (
        "6. Tarna",
        47.5, 42.9, 47.5, 42.9,
        "#db2777", "Dagistan / Tarku", 1.0, -1.4,
    ),
    (
        "7. Khazar",
        48.0, 46.0, 48.0, 46.0,
        "#4f46e5", "Asagi Volga / Itil", 1.6, 0.7,
    ),
    (
        "8. Janur / Zagur",
        39.0, 45.2, 39.0, 45.2,
        "#0891b2", "Azak / Kuban", -7.2, 0.9,
    ),
    (
        "9. Bulgar",
        39.0, 46.8, 49.0, 55.0,
        "#ea580c", "Kuban -> Volga", 1.0, 1.0,
    ),
    (
        "10. Sabir / Suvar",
        75.0, 55.0, 47.0, 43.0,
        "#16a34a", "Bati Sibirya -> Kafkasya", 1.0, -1.4,
    ),
]

COLUMNS = [
    "name",
    "start_lon",
    "start_lat",
    "end_lon",
    "end_lat",
    "color",
    "description",
    "label_dx",
    "label_dy",
    "geometry",
]


# ============================================================
# VERİ MODELİ VE DOĞRULAMA
# ============================================================

def build_gdf(selected_flags: list[bool]) -> gpd.GeoDataFrame:
    """Seçili kayıtları EPSG:4326 GeoDataFrame olarak oluşturur."""
    if len(selected_flags) != len(MIGRATIONS):
        raise ValueError(
            f"{len(MIGRATIONS)} seçim değeri gerekli; "
            f"{len(selected_flags)} değer verildi."
        )

    records: list[dict[str, Any]] = []

    for item, selected in zip(MIGRATIONS, selected_flags):
        if not selected:
            continue

        (
            name,
            start_lon, start_lat,
            end_lon, end_lat,
            color, description,
            label_dx, label_dy,
        ) = item

        start = (start_lon, start_lat)
        end = (end_lon, end_lat)

        # Aynı başlangıç ve bitiş koordinatı olan kayıtlar Point,
        # diğer kayıtlar LineString olarak dışa aktarılır.
        geometry = (
            Point(start)
            if start == end
            else LineString([start, end])
        )

        records.append({
            "name": name,
            "start_lon": start_lon,
            "start_lat": start_lat,
            "end_lon": end_lon,
            "end_lat": end_lat,
            "color": color,
            "description": description,
            "label_dx": label_dx,
            "label_dy": label_dy,
            "geometry": geometry,
        })

    if not records:
        # Geçerli, boş ve doğru CRS'ye sahip GeoDataFrame.
        empty_data = pd.DataFrame({
            column: pd.Series(dtype="object")
            for column in COLUMNS
            if column != "geometry"
        })
        empty_data["geometry"] = gpd.GeoSeries(
            [], crs=CRS, name="geometry"
        )
        return gpd.GeoDataFrame(
            empty_data,
            geometry="geometry",
            crs=CRS,
        )

    return gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=CRS,
    )


def export_geojson(gdf: gpd.GeoDataFrame) -> bytes:
    """GeoJSON FeatureCollection üretir; boş veri de desteklenir."""
    features = []

    for _, row in gdf.iterrows():
        properties = {
            column: (
                value.item()
                if hasattr(value, "item")
                else value
            )
            for column, value in row.drop(
                labels=["geometry"]
            ).to_dict().items()
        }

        geometry = row.geometry

        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": (
                mapping(geometry)
                if geometry is not None
                else None
            ),
        })

    collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    return json.dumps(
        collection,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """Öznitelikleri ve geometriyi WKT sütunuyla CSV olarak dışa aktarır."""
    data = pd.DataFrame(gdf.drop(columns="geometry").copy())

    data["geometry_wkt"] = [
        geometry.wkt if geometry is not None else ""
        for geometry in gdf.geometry
    ]

    buffer = StringIO()
    data.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


# ============================================================
# HARİTA
# ============================================================

def make_figure(
    gdf: gpd.GeoDataFrame,
    show_lines: bool,
    show_points: bool,
    show_labels: bool,
):
    """Matplotlib figürü üretir; boş GeoDataFrame'i destekler."""
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.set_title(
        "Hazar ve Ogur — şematik coğrafi gösterim",
        fontsize=15,
        pad=14,
    )
    ax.set_xlabel("Boylam (derece)")
    ax.set_ylabel("Enlem (derece)")
    ax.grid(True, linestyle=":", alpha=0.4)

    ax.set_xlim(10, 110)
    ax.set_ylim(30, 65)

    if gdf.empty:
        ax.text(
            0.5,
            0.5,
            "Gösterilecek kayıt seçilmedi.",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=13,
        )
        fig.tight_layout()
        return fig

    for _, row in gdf.iterrows():
        name = row["name"]
        color = row["color"]

        start_lon = float(row["start_lon"])
        start_lat = float(row["start_lat"])
        end_lon = float(row["end_lon"])
        end_lat = float(row["end_lat"])

        same_point = (
            start_lon == end_lon
            and start_lat == end_lat
        )

        if show_lines and not same_point:
            ax.annotate(
                "",
                xy=(end_lon, end_lat),
                xytext=(start_lon, start_lat),
                arrowprops={
                    "arrowstyle": "->",
                    "color": color,
                    "linewidth": 1.8,
                    "alpha": 0.85,
                },
            )

        if show_points:
            ax.scatter(
                [start_lon],
                [start_lat],
                color=color,
                marker="o",
                s=48,
                zorder=3,
            )

            if not same_point:
                ax.scatter(
                    [end_lon],
                    [end_lat],
                    color=color,
                    marker="X",
                    s=55,
                    zorder=3,
                )

        if show_labels:
            label_x = end_lon + float(row["label_dx"])
            label_y = end_lat + float(row["label_dy"])

            ax.annotate(
                name,
                (label_x, label_y),
                fontsize=8,
                color=color,
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": "white",
                    "alpha": 0.7,
                    "edgecolor": "none",
                },
            )

    fig.tight_layout()
    return fig


# ============================================================
# STREAMLIT ARAYÜZÜ
# ============================================================

st.title("🗺️ Hazar ve Ogur")
st.caption(
    "GeoPandas + Shapely + Matplotlib | Koordinat sistemi: EPSG:4326"
)

st.warning(
    "Tarihsel uyarı: Gösterilen koordinatlar ve çizgiler şematiktir. "
    "Bunlar, kaynaklarla doğrulanmış tarihsel göç güzergâhları "
    "olarak değerlendirilmemelidir."
)

# Widget'ların durumunu, ilgili checkbox'lar oluşturulmadan önce hazırla.
for i in range(len(MIGRATIONS)):
    key = f"route_{i}"
    if key not in st.session_state:
        st.session_state[key] = True

with st.sidebar:
    st.header("⚙️ Görüntüleme ayarları")

    show_lines = st.checkbox(
        "Göç çizgileri",
        value=True,
        key="show_lines",
    )
    show_points = st.checkbox(
        "Başlangıç ve bitiş noktaları",
        value=True,
        key="show_points",
    )
    show_labels = st.checkbox(
        "Etiketler",
        value=True,
        key="show_labels",
    )

    left, right = st.columns(2)

    if left.button("Tümünü seç", use_container_width=True):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"route_{i}"] = True

    if right.button("Temizle", use_container_width=True):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"route_{i}"] = False

    st.divider()
    st.subheader("Kayıtlar")

    for i, item in enumerate(MIGRATIONS):
        st.checkbox(
            item[0],
            key=f"route_{i}",
        )

selected_flags = [
    st.session_state[f"route_{i}"]
    for i in range(len(MIGRATIONS))
]

gdf = build_gdf(selected_flags)

col1, col2, col3 = st.columns(3)
col1.metric("Seçili kayıt", len(gdf))
col2.metric(
    "Çizgi geometrisi",
    sum(gdf.geometry.geom_type == "LineString"),
)
col3.metric(
    "Nokta geometrisi",
    sum(gdf.geometry.geom_type == "Point"),
)

if gdf.empty:
    st.info(
        "Hiçbir kayıt seçilmedi. Harita ve tabloda boş durum gösterilir; "
        "GeoJSON ve CSV indirme seçenekleri kullanılabilir."
    )

figure = make_figure(
    gdf,
    show_lines=show_lines,
    show_points=show_points,
    show_labels=show_labels,
)

try:
    st.pyplot(figure, clear_figure=False, use_container_width=True)
finally:
    plt.close(figure)

st.subheader("Seçili kayıtların öznitelikleri")

if gdf.empty:
    st.dataframe(
        pd.DataFrame(columns=[
            "name",
            "start_lon",
            "start_lat",
            "end_lon",
            "end_lat",
            "description",
        ]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.dataframe(
        pd.DataFrame(gdf.drop(columns="geometry")),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Verileri indir")

download_col1, download_col2 = st.columns(2)

with download_col1:
    st.download_button(
        "📥 GeoJSON indir",
        data=export_geojson(gdf),
        file_name="hazar_ogur.geojson",
        mime="application/geo+json",
        use_container_width=True,
    )

with download_col2:
    st.download_button(
        "📥 CSV indir",
        data=export_csv(gdf),
        file_name="hazar_ogur.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "CSV dosyasında geometri WKT biçiminde saklanır. "
    "GeoJSON dosyasında her seçili kayıt ayrı bir Feature'dır."
)

