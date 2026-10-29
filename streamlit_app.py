from __future__ import annotations
import json
from io import BytesIO
import folium
import geopandas as gpd
import pandas as pd
import requests
import streamlit as st
from folium.plugins import Fullscreen, MousePosition
from shapely.geometry import LineString, Point
from streamlit_folium import st_folium


# ============================================================
# UYGULAMA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hazar ve Ogur - Coğrafi Analiz",
    page_icon="🗺️",
    layout="wide",
)

CRS = "EPSG:4326"

# Natural Earth kamuya açık coğrafi veri deposu.
COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/"
    "natural-earth-vector/master/geojson/"
    "ne_110m_admin_0_countries.geojson"
)

MIGRATIONS = [
    ("1. Ujur / Uygur", 102.0, 47.0, 75.0, 45.0,
     "#2563eb", "Orkhon -> Jetisu", 1.5, 0.8),
    ("2. Tauris", 34.0, 45.0, 34.0, 45.0,
     "#059669", "Kirim (yerel)", 0.9, -1.7),
    ("3. Avar", 47.0, 42.0, 19.0, 47.0,
     "#dc2626", "Kafkasya -> Pannonia", 0.9, 0.6),
    ("4. Uauz / Oguz", 60.0, 43.0, 35.0, 39.0,
     "#d97706", "Aral/Hazar -> Anadolu", 0.9, -1.5),
    ("5. Bizal / Barsil", 42.0, 48.0, 42.0, 48.0,
     "#7c3aed", "Volga-Don / K. Kafkasya", 1.0, 1.2),
    ("6. Tarna", 47.5, 42.9, 47.5, 42.9,
     "#db2777", "Dagistan / Tarku", 1.0, -1.4),
    ("7. Khazar", 48.0, 46.0, 48.0, 46.0,
     "#4f46e5", "Asagi Volga / Itil", 1.6, 0.7),
    ("8. Janur / Zagur", 39.0, 45.2, 39.0, 45.2,
     "#0891b2", "Azak / Kuban", -7.2, 0.9),
    ("9. Bulgar", 39.0, 46.8, 49.0, 55.0,
     "#ea580c", "Kuban -> Volga", 1.0, 1.0),
    ("10. Sabir / Suvar", 75.0, 55.0, 47.0, 43.0,
     "#16a34a", "Bati Sibirya -> Kafkasya", 1.0, -1.4),
]

COLUMNS = [
    "name", "desc", "color", "is_migration",
    "slon", "slat", "elon", "elat", "dx", "dy",
    "geometry",
]


# ============================================================
# VERİ HAZIRLAMA
# ============================================================

@st.cache_data
def build_gdf(selected_flags: tuple[bool, ...]) -> gpd.GeoDataFrame:
    records = []

    for index, item in enumerate(MIGRATIONS):
        if not selected_flags[index]:
            continue

        (
            name, slon, slat, elon, elat,
            color, desc, dx, dy,
        ) = item

        is_migration = (slon, slat) != (elon, elat)

        geometry = (
            LineString([(slon, slat), (elon, elat)])
            if is_migration
            else Point(slon, slat)
        )

        records.append({
            "name": name,
            "desc": desc,
            "color": color,
            "is_migration": is_migration,
            "slon": slon,
            "slat": slat,
            "elon": elon,
            "elat": elat,
            "dx": dx,
            "dy": dy,
            "geometry": geometry,
        })

    # Boş GeoDataFrame de doğru CRS ve geometri tipine sahip olur.
    if not records:
        return gpd.GeoDataFrame(
            {
                column: pd.Series(dtype="object")
                for column in COLUMNS
                if column != "geometry"
            },
            geometry=gpd.GeoSeries([], crs=CRS),
            crs=CRS,
        )

    return gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=CRS,
    )


@st.cache_data(ttl=86400, show_spinner=False)
def load_countries() -> tuple[str | None, str | None]:
    """Ülke sınırlarını indir; hata olursa hata mesajını döndür."""
    try:
        response = requests.get(
            COUNTRIES_URL,
            timeout=25,
            headers={"User-Agent": "HazarOgurGeoApp/1.0"},
        )
        response.raise_for_status()

        # Yanıtın gerçekten GeoJSON olup olmadığını kontrol et.
        data = response.json()
        if data.get("type") != "FeatureCollection":
            return None, "Ülke sınırı kaynağı geçerli GeoJSON döndürmedi."

        return json.dumps(data), None

    except (requests.RequestException, ValueError) as exc:
        return None, f"Ülke sınırları yüklenemedi: {exc}"


def make_map(
    gdf: gpd.GeoDataFrame,
    show_countries: bool,
    show_lines: bool,
    show_points: bool,
    show_labels: bool,
    show_basemap: bool,
) -> folium.Map:
    """Haritayı katmanlarla oluştur."""

    fmap = folium.Map(
        location=[47, 55],
        zoom_start=4,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )

    if show_basemap:
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="OpenStreetMap taban haritası",
            overlay=False,
            control=True,
            show=True,
        ).add_to(fmap)

    # Alternatif bir sade harita katmanı.
    folium.TileLayer(
        tiles="CartoDB positron",
        name="Sade taban haritası",
        overlay=False,
        control=True,
        show=False,
    ).add_to(fmap)

    if show_countries:
        countries_json, error = load_countries()

        if countries_json:
            folium.GeoJson(
                data=countries_json,
                name="Ülke sınırları (Natural Earth)",
                style_function=lambda feature: {
                    "color": "#475569",
                    "weight": 0.8,
                    "fillColor": "#cbd5e1",
                    "fillOpacity": 0.10,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["ADMIN"],
                    aliases=["Ülke:"],
                    sticky=True,
                ),
            ).add_to(fmap)
        elif error:
            st.warning(error)

    lines_layer = folium.FeatureGroup(
        name="Göç çizgileri", show=show_lines
    )
    points_layer = folium.FeatureGroup(
        name="Başlangıç ve bitiş noktaları", show=show_points
    )
    labels_layer = folium.FeatureGroup(
        name="Etiketler", show=show_labels
    )

    for _, row in gdf.iterrows():
        name = str(row["name"])
        desc = str(row["desc"])
        color = str(row["color"])

        start = [float(row["slat"]), float(row["slon"])]
        end = [float(row["elat"]), float(row["elon"])]

        popup_html = (
            f"<b>{name}</b><br>"
            f"{desc}<br>"
            f"Başlangıç: {row['slon']}, {row['slat']}<br>"
            f"Bitiş: {row['elon']}, {row['elat']}<br>"
            f"Geometri: "
            f"{'Çizgi' if row['is_migration'] else 'Nokta'}"
        )

        if bool(row["is_migration"]) and show_lines:
            folium.PolyLine(
                locations=[start, end],
                color=color,
                weight=3,
                opacity=0.9,
                tooltip=name,
                popup=folium.Popup(popup_html, max_width=320),
            ).add_to(lines_layer)

            # Başlangıç -> bitiş yönünü gösteren ok.
            folium.PolyLineTextPath(
                # Bu eklenti yoksa ana çizgi yine görünür.
                folium.PolyLine(
                    locations=[start, end],
                    color=color,
                    weight=0,
                    opacity=0,
                ),
                "  ▶  ",
                repeat=True,
                offset=7,
                attributes={"fill": color, "font-weight": "bold"},
            ).add_to(lines_layer)

        if show_points:
            if bool(row["is_migration"]):
                folium.CircleMarker(
                    location=start,
                    radius=5,
                    color="white",
                    weight=2,
                    fill=True,
                    fill_color=color,
                    fill_opacity=1,
                    tooltip=f"{name} — başlangıç",
                ).add_to(points_layer)

                folium.Marker(
                    location=end,
                    tooltip=f"{name} — bitiş",
                    popup=folium.Popup(popup_html, max_width=320),
                    icon=folium.Icon(
                        color="blue",
                        icon="flag",
                        prefix="fa",
                    ),
                ).add_to(points_layer)
            else:
                folium.CircleMarker(
                    location=start,
                    radius=7,
                    color="white",
                    weight=2,
                    fill=True,
                    fill_color=color,
                    fill_opacity=1,
                    tooltip=name,
                    popup=folium.Popup(popup_html, max_width=320),
                ).add_to(points_layer)

        if show_labels:
            label_location = (
                end if bool(row["is_migration"]) else start
            )
            folium.Marker(
                location=label_location,
                tooltip=name,
                icon=folium.DivIcon(
                    html=(
                        '<div style="'
                        f'color:{color};'
                        'font-size:11px;'
                        'font-weight:bold;'
                        'white-space:nowrap;'
                        'background:rgba(255,255,255,0.88);'
                        'border:1px solid #cbd5e1;'
                        'border-radius:4px;'
                        'padding:3px 5px;'
                        '">'
                        f'{name}<br><small>{desc}</small>'
                        '</div>'
                    )
                ),
            ).add_to(labels_layer)

    if show_lines:
        lines_layer.add_to(fmap)

    if show_points:
        points_layer.add_to(fmap)

    if show_labels:
        labels_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    Fullscreen(position="topleft").add_to(fmap)
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Koordinat:",
        num_digits=4,
    ).add_to(fmap)

    return fmap


# ============================================================
# STREAMLIT ARAYÜZÜ
# ============================================================

st.title("🗺️ Hazar ve Ogur — Coğrafi Analiz")
st.caption(
    "GeoPandas · EPSG:4326 · Folium · Natural Earth · OpenStreetMap"
)

with st.sidebar:
    st.header("⚙️ Harita katmanları")

    show_basemap = st.checkbox("OpenStreetMap tabanı", value=True)
    show_countries = st.checkbox("Ülke sınırları", value=True)
    show_lines = st.checkbox("Göç çizgileri", value=True)
    show_points = st.checkbox("Başlangıç / bitiş noktaları", value=True)
    show_labels = st.checkbox("Etiketler", value=True)

    st.divider()
    st.subheader("Kayıt seçimi")

    selected_flags = tuple(
        st.checkbox(item[0], value=True, key=f"record_{i}")
        for i, item in enumerate(MIGRATIONS)
    )

    if st.button("Tüm kayıtları seç"):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"record_{i}"] = True
        st.rerun()

    if st.button("Tüm seçimleri kaldır"):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"record_{i}"] = False
        st.rerun()

    # Rerun sonrasında güncel seçimleri oku.
    selected_flags = tuple(
        bool(st.session_state.get(f"record_{i}", True))
        for i in range(len(MIGRATIONS))
    )

gdf = build_gdf(selected_flags)

col1, col2, col3 = st.columns(3)
col1.metric("Seçili kayıt", len(gdf))
col2.metric("Göç çizgisi", int(gdf["is_migration"].sum()))
col3.metric("Yerleşim noktası", int((~gdf["is_migration"]).sum()))

if gdf.empty:
    st.warning(
        "Hiçbir kayıt seçilmedi. Harita üzerinde göç verisi gösterilmiyor. "
        "Sol menüden kayıt seçebilir veya tüm kayıtları yeniden açabilirsin."
    )
else:
    st.info(
        "Bu güzergâhlar araştırma amaçlı şematik gösterimlerdir; "
        "tarihsel olarak doğrulanmış rotalar oldukları varsayılmamalıdır."
    )

# Boş seçimde de taban haritası ve sınır katmanı gösterilebilir.
fmap = make_map(
    gdf=gdf,
    show_countries=show_countries,
    show_lines=show_lines and not gdf.empty,
    show_points=show_points and not gdf.empty,
    show_labels=show_labels and not gdf.empty,
    show_basemap=show_basemap,
)

st_folium(
    fmap,
    use_container_width=True,
    height=680,
    key="hazar_ogur_map",
)

# ============================================================
# TABLO VE İNDİRMELER
# ============================================================

st.subheader("📋 GeoDataFrame")

if gdf.empty:
    st.dataframe(
        pd.DataFrame(columns=[c for c in COLUMNS if c != "geometry"]),
        use_container_width=True,
    )
else:
    st.dataframe(
        gdf.drop(columns="geometry"),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("📥 Verileri dışa aktar")

if gdf.empty:
    st.info(
        "İndirme için en az bir kayıt seç. Boş GeoJSON indirme düğmesi "
        "oluşturulmadı."
    )
else:
    # to_file(BytesIO) yerine doğrudan GeoJSON metni üret.
    # to_wgs84=True, dışa aktarılan koordinatları WGS84'e dönüştürür.
    geojson_text = gdf.to_json(
        na="null",
        drop_id=True,
        to_wgs84=True,
    )

    # Geçerli JSON olduğunu indirme düğmesini göstermeden önce doğrula.
    json.loads(geojson_text)

    st.download_button(
        label="🌍 GeoJSON indir",
        data=geojson_text.encode("utf-8"),
        file_name="hazar_ogur.geojson",
        mime="application/geo+json",
    )

    # CSV'de Shapely geometrisi yerine WKT kullan.
    csv_df = gdf.drop(columns="geometry").copy()
    csv_df["geometry_wkt"] = gdf.geometry.to_wkt()

    csv_bytes = csv_df.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    st.download_button(
        label="📄 CSV indir",
        data=csv_bytes,
        file_name="hazar_ogur.csv",
        mime="text/csv",
    )

st.caption(
    "Harita verileri ve çizimler şematik araştırma katmanlarıdır. "
    "Ülke sınırları tarihsel dönemlerin siyasi sınırlarını temsil etmez."
)
