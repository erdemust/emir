import streamlit as st
import geopandas as gpd
from shapely.geometry import Point, LineString
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import matplotlib.patheffects as path_effects
from matplotlib.lines import Line2D

st.set_page_config(page_title="Hazar ve Ogur - GeoPandas", page_icon="🗺️", layout="wide")

st.title("🗺️ Hazar ve Ogur - GeoPandas Implementation (EPSG:4326)")

MIGRATIONS = [
    ("1. Ujur / Uygur",   102.0, 47.0,  75.0, 45.0, "#2563eb", "Orkhon -> Jetisu", 1.5, 0.8),
    ("2. Tauris",          34.0, 45.0,  34.0, 45.0, "#059669", "Kirim (yerel)", 0.9, -1.7),
    ("3. Avar",            47.0, 42.0,  19.0, 47.0, "#dc2626", "Kafkasya -> Pannonia", 0.9, 0.6),
    ("4. Uauz / Oguz",     60.0, 43.0,  35.0, 39.0, "#d97706", "Aral/Hazar -> Anadolu", 0.9, -1.5),
    ("5. Bizal / Barsil",  42.0, 48.0,  42.0, 48.0, "#7c3aed", "Volga-Don / K. Kafkasya", 1.0, 1.2),
    ("6. Tarna",           47.5, 42.9,  47.5, 42.9, "#db2777", "Dagistan / Tarku", 1.0, -1.4),
    ("7. Khazar",          48.0, 46.0,  48.0, 46.0, "#4f46e5", "Asagi Volga / Itil", 1.6, 0.7),
    ("8. Janur / Zagur",   39.0, 45.2,  39.0, 45.2, "#0891b2", "Azak / Kuban", -7.2, 0.9),
    ("9. Bulgar",          39.0, 46.8,  49.0, 55.0, "#ea580c", "Kuban -> Volga", 1.0, 1.0),
    ("10. Sabir / Suvar",  75.0, 55.0,  47.0, 43.0, "#16a34a", "Bati Sibirya -> Kafkasya", 1.0, -1.4),
]

with st.sidebar:
    st.header("⚙️ GeoPandas Ayarlar")
    show_lines = st.checkbox("Goc Cizgileri (LineString)", True)
    show_points = st.checkbox("Noktalar (Point)", True)
    show_labels = st.checkbox("Etiketler", True)
    selected = {}
    for i, (name, *_ ) in enumerate(MIGRATIONS):
        selected[i] = st.checkbox(name, True, key=f"gpd_{i}")

@st.cache_data
def build_gdfs(selected_flags):
    recs = []
    for idx, (name, slon, slat, elon, elat, color, desc, dx, dy) in enumerate(MIGRATIONS):
        if not selected_flags[idx]:
            continue
        is_mig = (slon, slat) != (elon, elat)
        geom = LineString([(slon, slat), (elon, elat)]) if is_mig else Point(slon, slat)
        recs.append({"name": name, "desc": desc, "color": color, "is_migration": is_mig,
                     "slon": slon, "slat": slat, "elon": elon, "elat": elat,
                     "dx": dx, "dy": dy, "geometry": geom})
    gdf = gpd.GeoDataFrame(recs, crs="EPSG:4326")
    return gdf

selected_flags = tuple(selected[i] for i in range(len(MIGRATIONS)))
gdf = build_gdfs(selected_flags)

# Plot
fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
ax.set_xlim(15, 108)
ax.set_ylim(33, 61)
ax.set_aspect(1/np.cos(np.radians(47)))
ax.set_facecolor("#f8fafc")
ax.grid(True, linestyle=":", alpha=0.35)

if show_lines:
    for _, r in gdf[gdf["is_migration"]].iterrows():
        ax.plot([r["slon"], r["elon"]], [r["slat"], r["elat"]], color=r["color"], lw=2.5)
        ax.annotate("", xy=(r["elon"], r["elat"]), xytext=(r["slon"], r["slat"]),
                    arrowprops=dict(arrowstyle="-|>", color=r["color"], lw=2, mutation_scale=14, connectionstyle="arc3,rad=0.12"))

if show_points:
    gdf_stationary = gdf[~gdf["is_migration"]]
    gdf_mig = gdf[gdf["is_migration"]]
    if not gdf_stationary.empty:
        gdf_stationary.plot(ax=ax, color=gdf_stationary["color"], markersize=120, edgecolor="white", linewidth=1.5, zorder=5)
    if not gdf_mig.empty:
        for _, r in gdf_mig.iterrows():
            ax.scatter(r["slon"], r["slat"], s=80, color=r["color"], edgecolor="white", zorder=5)
            ax.scatter(r["elon"], r["elat"], s=180, marker="*", color=r["color"], edgecolor="white", zorder=6)

if show_labels:
    for _, r in gdf.iterrows():
        lon = r["elon"] if r["is_migration"] else r["slon"]
        lat = r["elat"] if r["is_migration"] else r["slat"]
        ax.text(lon+r["dx"], lat+r["dy"], f"{r['name']}\n({r['desc']})", fontsize=8.5, fontweight="bold", color=r["color"],
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=r["color"], alpha=0.9), zorder=7)

ax.set_title("GeoPandas GeoDataFrame - EPSG:4326", fontweight="bold")
st.pyplot(fig)

st.subheader("GeoDataFrame")
st.dataframe(gdf.drop(columns="geometry"))

# Download GeoJSON
buf = BytesIO()
gdf.to_file(buf, driver="GeoJSON")
st.download_button("📥 GeoJSON Indir", data=buf.getvalue(), file_name="hazar_ogur.geojson", mime="application/geo+json")