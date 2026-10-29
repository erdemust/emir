from __future__ import annotations
import json
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from shapely.geometry import LineString, Point

st.set_page_config(
    page_title="Hazar ve Ogur - GeoPandas",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Hazar ve Ogur - GeoPandas")
st.info(
    "Bu güzergâhlar araştırma amaçlı şematik gösterimlerdir; "
    "tarihsel olarak doğrulanmış rotalar oldukları varsayılmamalıdır."
)

MIGRATIONS = [
    ("1. Ujur / Uygur", 102.0, 47.0, 75.0, 45.0, "#2563eb", "Orkhon -> Jetisu", 1.5, 0.8),
    ("2. Tauris", 34.0, 45.0, 34.0, 45.0, "#059669", "Kirim (yerel)", 0.9, -1.7),
    ("3. Avar", 47.0, 42.0, 19.0, 47.0, "#dc2626", "Kafkasya -> Pannonia", 0.9, 0.6),
    ("4. Uauz / Oguz", 60.0, 43.0, 35.0, 39.0, "#d97706", "Aral/Hazar -> Anadolu", 0.9, -1.5),
    ("5. Bizal / Barsil", 42.0, 48.0, 42.0, 48.0, "#7c3aed", "Volga-Don / K. Kafkasya", 1.0, 1.2),
    ("6. Tarna", 47.5, 42.9, 47.5, 42.9, "#db2777", "Dagistan / Tarku", 1.0, -1.4),
    ("7. Khazar", 48.0, 46.0, 48.0, 46.0, "#4f46e5", "Asagi Volga / Itil", 1.6, 0.7),
    ("8. Janur / Zagur", 39.0, 45.2, 39.0, 45.2, "#0891b2", "Azak / Kuban", -7.2, 0.9),
    ("9. Bulgar", 39.0, 46.8, 49.0, 55.0, "#ea580c", "Kuban -> Volga", 1.0, 1.0),
    ("10. Sabir / Suvar", 75.0, 55.0, 47.0, 43.0, "#16a34a", "Bati Sibirya -> Kafkasya", 1.0, -1.4),
]

COLUMNS = [
    "name", "desc", "color", "is_migration",
    "slon", "slat", "elon", "elat", "dx", "dy",
]


@st.cache_data(show_spinner=False)
def build_gdf(selected_flags: tuple[bool, ...]) -> gpd.GeoDataFrame:
    records = []

    for i, item in enumerate(MIGRATIONS):
        if not selected_flags[i]:
            continue

        name, slon, slat, elon, elat, color, desc, dx, dy = item
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

    if not records:
        empty = pd.DataFrame({
            "name": pd.Series(dtype="str"),
            "desc": pd.Series(dtype="str"),
            "color": pd.Series(dtype="str"),
            "is_migration": pd.Series(dtype="bool"),
            "slon": pd.Series(dtype="float64"),
            "slat": pd.Series(dtype="float64"),
            "elon": pd.Series(dtype="float64"),
            "elat": pd.Series(dtype="float64"),
            "dx": pd.Series(dtype="float64"),
            "dy": pd.Series(dtype="float64"),
        })
        return gpd.GeoDataFrame(
            empty,
            geometry=gpd.GeoSeries([], crs="EPSG:4326"),
            crs="EPSG:4326",
        )

    return gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs="EPSG:4326",
    )


def export_geojson(gdf: gpd.GeoDataFrame) -> bytes:
    if gdf.empty:
        data = {"type": "FeatureCollection", "features": []}
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    export_gdf = gdf.to_crs("EPSG:4326")
    return export_gdf.to_json().encode("utf-8")


def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    if gdf.empty:
        return pd.DataFrame(
            columns=COLUMNS + ["geometry_wkt"]
        ).to_csv(index=False).encode("utf-8-sig")

    table = pd.DataFrame(gdf.drop(columns="geometry")).copy()
    table["geometry_wkt"] = gdf.geometry.to_wkt()
    return table.to_csv(index=False).encode("utf-8-sig")


with st.sidebar:
    st.header("⚙️ GeoPandas ayarları")

    show_lines = st.checkbox("Göç çizgileri", value=True)
    show_points = st.checkbox("Noktalar", value=True)
    show_labels = st.checkbox("Etiketler", value=True)

    st.subheader("Güzergâh seçimi")

    # Widget durumları oluşturulmadan önce başlatılır.
    for i in range(len(MIGRATIONS)):
        key = f"route_{i}"
        if key not in st.session_state:
            st.session_state[key] = True

    col1, col2 = st.columns(2)

    if col1.button("Tümünü seç", use_container_width=True):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"route_{i}"] = True

    if col2.button("Temizle", use_container_width=True):
        for i in range(len(MIGRATIONS)):
            st.session_state[f"route_{i}"] = False

    selected_flags_list = []

    for i, item in enumerate(MIGRATIONS):
        value = st.checkbox(item[0], key=f"route_{i}")
        selected_flags_list.append(value)

selected_flags = tuple(selected_flags_list)
gdf = build_gdf(selected_flags)

if gdf.empty:
    st.warning(
        "Hiçbir güzergâh seçilmedi. Sol menüden kayıt seçebilir "
        "veya boş veri dosyalarını indirebilirsiniz."
    )
else:
    fig, ax = plt.subplots(figsize=(14, 8), dpi=150)

    try:
        ax.set_xlim(15, 108)
        ax.set_ylim(33, 61)
        ax.set_aspect(1 / np.cos(np.radians(47)))
        ax.set_facecolor("#f8fafc")
        ax.grid(True, linestyle=":", alpha=0.35)

        if show_lines:
            for _, row in gdf[gdf["is_migration"]].iterrows():
                ax.plot(
                    [row["slon"], row["elon"]],
                    [row["slat"], row["elat"]],
                    color=row["color"],
                    linewidth=2.5,
                )
                ax.annotate(
                    "",
                    xy=(row["elon"], row["elat"]),
                    xytext=(row["slon"], row["slat"]),
                    arrowprops={
                        "arrowstyle": "-|>",
                        "color": row["color"],
                        "linewidth": 1.8,
                        "mutation_scale": 14,
                    },
                )

        if show_points:
            for _, row in gdf.iterrows():
                if row["is_migration"]:
                    ax.scatter(
                        row["slon"], row["slat"],
                        s=80, color=row["color"],
                        edgecolor="white", zorder=5,
                    )
                    ax.scatter(
                        row["elon"], row["elat"],
                        s=180, marker="*",
                        color=row["color"],
                        edgecolor="white", zorder=6,
                    )
                else:
                    ax.scatter(
                        row["slon"], row["slat"],
                        s=120, color=row["color"],
                        edgecolor="white", zorder=5,
                    )

        if show_labels:
            for _, row in gdf.iterrows():
                lon = row["elon"] if row["is_migration"] else row["slon"]
                lat = row["elat"] if row["is_migration"] else row["slat"]

                ax.text(
                    lon + row["dx"],
                    lat + row["dy"],
                    f'{row["name"]}\n({row["desc"]})',
                    fontsize=8,
                    fontweight="bold",
                    color=row["color"],
                    bbox={
                        "boxstyle": "round,pad=0.3",
                        "facecolor": "white",
                        "edgecolor": row["color"],
                        "alpha": 0.9,
                    },
                    zorder=7,
                )

        ax.set_title("GeoPandas GeoDataFrame — EPSG:4326")
        ax.set_xlabel("Boylam")
        ax.set_ylabel("Enlem")
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
    finally:
        plt.close(fig)

st.subheader("GeoDataFrame")

if gdf.empty:
    st.dataframe(
        pd.DataFrame(columns=COLUMNS),
        use_container_width=True,
    )
else:
    st.dataframe(
        gdf.drop(columns="geometry"),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Verileri indir")

st.download_button(
    "📥 GeoJSON indir",
    data=export_geojson(gdf),
    file_name="hazar_ogur.geojson",
    mime="application/geo+json",
    use_container_width=True,
)

st.download_button(
    "📥 CSV indir",
    data=export_csv(gdf),
    file_name="hazar_ogur.csv",
    mime="text/csv",
    use_container_width=True,
)
