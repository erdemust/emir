
from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from modules.history_data import HISTORICAL_NOTES, SAMPLE_GEOJSON
from modules.data_loader import (
    load_default_data,
    validate_and_load_uploaded_file,
)
from modules.map_builder import create_map


st.set_page_config(
    page_title="Para, Hazar ve Ogur — Tarihsel Coğrafya",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Para, Hazar ve Ogur: Tarihsel-Coğrafi İnceleme")

st.warning(
    "Yöntem notu: Haritadaki örnek koordinatlar ve çizgiler tarihsel "
    "kanıt olarak değerlendirilmemelidir. Her güzergâh ve etimoloji "
    "iddiası birincil kaynaklar ve akademik literatür üzerinden "
    "ayrıca doğrulanmalıdır."
)

# --------------------------------------------------
# Varsayılan veriyi yükle
# --------------------------------------------------
if "gdf" not in st.session_state:
    st.session_state.gdf = load_default_data(SAMPLE_GEOJSON)

# --------------------------------------------------
# Kenar çubuğu
# --------------------------------------------------
with st.sidebar:
    st.header("⚙️ Harita ve veri ayarları")

    tile_choice = st.selectbox(
        "Altlık harita",
        [
            "CartoDB Positron (Recomendado)",
            "OpenStreetMap",
            "Sin Mapa de Fondo",
        ],
    )

    st.divider()
    st.subheader("📤 Veri yükle")

    uploaded_file = st.file_uploader(
        "GeoJSON, JSON veya CSV seç",
        type=["geojson", "json", "csv"],
    )

    if uploaded_file is not None:
        signature = (uploaded_file.name, uploaded_file.size)

        if st.session_state.get("uploaded_signature") != signature:
            new_gdf, message = validate_and_load_uploaded_file(
                uploaded_file
            )

            if new_gdf is not None:
                st.session_state.gdf = new_gdf
                st.session_state.uploaded_signature = signature
                st.success(message)
            else:
                st.error(message)

    if st.button("Varsayılan verilere dön"):
        st.session_state.gdf = load_default_data(SAMPLE_GEOJSON)
        st.session_state.pop("uploaded_signature", None)
        st.rerun()

    st.divider()
    st.subheader("🔎 Filtreler")

    search_query = st.text_input("Ada göre ara")

    gdf = st.session_state.gdf.copy()

    geometry_options = (
        sorted(gdf["tipo_geometria"].dropna().unique().tolist())
        if not gdf.empty and "tipo_geometria" in gdf.columns
        else []
    )

    selected_geometries = st.multiselect(
        "Geometri türü",
        options=geometry_options,
        default=geometry_options,
    )

    show_map = st.checkbox("Haritayı göster", value=True)

# --------------------------------------------------
# Veri alanlarını güvenli biçimde tamamla
# --------------------------------------------------
gdf = st.session_state.gdf.copy()

for column, default in [
    ("nombre", "Adsız kayıt"),
    ("grupo", "Genel"),
    ("descripcion", ""),
]:
    if column not in gdf.columns:
        gdf[column] = default
    else:
        gdf[column] = gdf[column].fillna(default).astype(str)

if "tipo_geometria" not in gdf.columns:
    gdf["tipo_geometria"] = gdf.geometry.geom_type

filtered_gdf = gdf.copy()

if search_query:
    filtered_gdf = filtered_gdf[
        filtered_gdf["nombre"].str.contains(
            search_query,
            case=False,
            na=False,
        )
    ]

if selected_geometries:
    filtered_gdf = filtered_gdf[
        filtered_gdf["tipo_geometria"].isin(selected_geometries)
    ]
else:
    filtered_gdf = filtered_gdf.iloc[0:0].copy()

# --------------------------------------------------
# Sekmeler
# --------------------------------------------------
tab_map, tab_history, tab_download = st.tabs(
    [
        "🗺️ Etkileşimli harita",
        "📚 Tarihsel notlar",
        "📥 Veri indirme",
    ]
)

with tab_map:
    st.caption(
        "Haritada yakınlaştırma yapabilir ve geometrilere tıklayarak "
        "öznitelikleri inceleyebilirsin."
    )

    if filtered_gdf.empty:
        st.info("Filtrelere uyan kayıt bulunamadı.")
    elif show_map:
        map_obj = create_map(
            filtered_gdf,
            selected_tile=tile_choice,
        )
        st_folium(map_obj, width=900, height=550)

    st.metric("Filtrelenen kayıt sayısı", len(filtered_gdf))

with tab_history:
    st.header("Tarihsel ve etimolojik notlar")

    st.info(
        "Bu notlar araştırmaya başlangıç içindir. Kaynaklarda "
        "doğrulanmamış etimolojiler kesin bilgi olarak sunulmamalıdır."
    )

    for group, info in HISTORICAL_NOTES.items():
        with st.expander(group):
            st.markdown(f"**Etimoloji:** {info['etymology']}")
            st.markdown(f"**Tarihsel bağlam:** {info['context']}")
            st.markdown("**Kaynakça:**")

            for source in info["sources"]:
                st.markdown(f"- {source}")

with tab_download:
    st.header("Filtrelenmiş veriyi indir")
    st.write(f"Kayıt sayısı: **{len(filtered_gdf)}**")

    st.dataframe(
        filtered_gdf.drop(columns="geometry", errors="ignore"),
        use_container_width=True,
    )

    geojson_data = filtered_gdf.to_json().encode("utf-8")
    csv_data = (
        filtered_gdf.drop(columns="geometry", errors="ignore")
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    col1, col2 = st.columns(2)

    col1.download_button(
        "📄 GeoJSON indir",
        data=geojson_data,
        file_name="para_hazar_ogur.geojson",
        mime="application/geo+json",
        use_container_width=True,
    )

    col2.download_button(
        "📊 CSV indir",
        data=csv_data,
        file_name="para_hazar_ogur.csv",
        mime="text/csv",
        use_container_width=True,
    )
