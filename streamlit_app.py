from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import folium
import geopandas as gpd
import pandas as pd
import requests
import streamlit as st
from folium.plugins import Fullscreen, MousePosition
from streamlit_folium import st_folium

# ------------------------------------------------------------
# Streamlit Cloud / Hazar-Oğur şematik güzergâh haritası
# Bu çizimler tarihsel olarak doğrulanmış rotalar değildir.
# ------------------------------------------------------------

st.set_page_config(
    page_title="Hazar ve Oğur — Şematik Güzergâhlar",
    page_icon="🗺️",
    layout="wide",
)

DISCLAIMER = (
    "Bu güzergâhlar araştırma amaçlı şematik gösterimlerdir; "
    "tarihsel olarak doğrulanmış rotalar oldukları varsayılmamalıdır."
)

# Şematik örnek veriler. Koordinatlar güzergâh iddiası veya tarihsel kanıt değildir.
ROUTES: list[dict[str, Any]] = [
    {
        "id": "route_1",
        "name": "Karadeniz bozkır kuşağı (şematik)",
        "category": "Şematik güzergâh",
        "description": "Araştırma amaçlı temsili çizim; tarihsel rota doğrulaması değildir.",
        "color": "#d62728",
        "coordinates": [
            [48.0, 42.0],
            [46.5, 38.5],
            [45.0, 34.0],
            [43.5, 29.5],
        ],
    },
    {
        "id": "route_2",
        "name": "Hazar çevresi (şematik)",
        "category": "Şematik güzergâh",
        "description": "Araştırma amaçlı temsili çizim; tarihsel rota doğrulaması değildir.",
        "color": "#1f77b4",
        "coordinates": [
            [48.0, 52.0],
            [45.0, 49.0],
            [42.0, 46.0],
            [39.0, 43.0],
        ],
    },
    {
        "id": "route_3",
        "name": "Orta Asya–batı yönü (şematik)",
        "category": "Şematik güzergâh",
        "description": "Araştırma amaçlı temsili çizim; tarihsel rota doğrulaması değildir.",
        "color": "#2ca02c",
        "coordinates": [
            [43.0, 78.0],
            [44.0, 68.0],
            [45.0, 59.0],
            [46.0, 50.0],
        ],
    },
]

COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_country_boundaries() -> gpd.GeoDataFrame | None:
    """Ülke sınırlarını internetten yükler; ağ hatasında None döndürür."""
    try:
        response = requests.get(
            COUNTRIES_URL,
            timeout=(5, 15),
            headers={"User-Agent": "Hazar-Ogur-Research-Map/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features", [])
        if not features:
            return None

        countries = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
        if countries.empty or "geometry" not in countries:
            return None

        # Natural Earth sürümlerinde ülke alanının adı değişebilir.
        name_field = next(
            (field for field in ("ADMIN", "name", "NAME", "SOVEREIGNT")
             if field in countries.columns),
            None,
        )
        if name_field and name_field != "ADMIN":
            countries = countries.rename(columns={name_field: "ADMIN"})
        if "ADMIN" not in countries.columns:
            countries["ADMIN"] = "Ülke"

        return countries[["ADMIN", "geometry"]]
    except Exception:
        return None


def make_route_gdf(route_rows: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    """Seçilen şematik rotalardan WGS84 GeoDataFrame üretir."""
    from shapely.geometry import LineString, Point

    records: list[dict[str, Any]] = []
    for route in route_rows:
        coords = route.get("coordinates", [])
        if len(coords) < 2:
            continue
        # Kaynak koordinatlar [enlem, boylam]; Shapely x/y = [boylam, enlem].
        line = LineString([(lon, lat) for lat, lon in coords])
        records.append(
            {
                "id": route["id"],
                "name": route["name"],
                "category": route["category"],
                "description": route["description"],
                "color": route["color"],
                "geometry": line,
                "start_point": Point(coords[0][1], coords[0][0]),
                "end_point": Point(coords[-1][1], coords[-1][0]),
            }
        )

    if not records:
        return gpd.GeoDataFrame(
            {
                "id": pd.Series(dtype="str"),
                "name": pd.Series(dtype="str"),
                "category": pd.Series(dtype="str"),
                "description": pd.Series(dtype="str"),
                "color": pd.Series(dtype="str"),
                "geometry": gpd.GeoSeries([], crs="EPSG:4326"),
            },
            geometry="geometry",
            crs="EPSG:4326",
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")


def add_arrow_if_available(line: folium.PolyLine, color: str, target: folium.FeatureGroup) -> None:
    """Ok çizgisi eklemeyi dener; eklenti hatası ana haritayı bozmaz."""
    try:
        from folium.plugins import PolyLineTextPath

        PolyLineTextPath(
            line,
            "➤",
            repeat=True,
            offset=7,
            attributes={
                "fill": color,
                "font-weight": "bold",
                "font-size": "13",
            },
        ).add_to(target)
    except Exception:
        # Ok eklentisi/JS desteklenmese de temel rota çizgisi görünür.
        pass


def make_map(
    route_rows: list[dict[str, Any]],
    basemap: str,
    show_countries: bool,
    show_points: bool,
    show_labels: bool,
    show_arrows: bool,
) -> folium.Map:
    fmap = folium.Map(
        location=[43.5, 48.0],
        zoom_start=4,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )

    tile_choices = {
        "OpenStreetMap": {
            "tiles": "OpenStreetMap",
            "attr": None,
        },
        "CartoDB Positron": {
            "tiles": "CartoDB positron",
            "attr": None,
        },
        "CartoDB Dark Matter": {
            "tiles": "CartoDB dark_matter",
            "attr": None,
        },
    }
    tile = tile_choices.get(basemap, tile_choices["OpenStreetMap"])
    folium.TileLayer(
        tiles=tile["tiles"],
        name=basemap,
        overlay=False,
        control=True,
    ).add_to(fmap)

    if show_countries:
        countries = load_country_boundaries()
        if countries is not None and not countries.empty:
            folium.GeoJson(
                data=json.loads(countries.to_json(to_wgs84=True)),
                name="Ülke sınırları (Natural Earth)",
                style_function=lambda _feature: {
                    "fillColor": "#d8d8d8",
                    "color": "#666666",
                    "weight": 0.7,
                    "fillOpacity": 0.08,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["ADMIN"],
                    aliases=["Ülke:"],
                    sticky=True,
                ),
            ).add_to(fmap)
        else:
            st.warning(
                "Ülke sınırları kaynağına erişilemedi. Taban haritası ve seçili "
                "şematik rotalar yine kullanılabilir."
            )

    for route in route_rows:
        # Folium koordinatları [enlem, boylam] bekler.
        coordinates = route["coordinates"]
        group = folium.FeatureGroup(name=route["name"], show=True)

        line = folium.PolyLine(
            locations=coordinates,
            color=route["color"],
            weight=4,
            opacity=0.9,
            tooltip=route["name"],
        ).add_to(group)

        if show_arrows:
            add_arrow_if_available(line, route["color"], group)

        if show_points:
            for label, point in (
                ("Başlangıç", coordinates[0]),
                ("Bitiş", coordinates[-1]),
            ):
                folium.CircleMarker(
                    location=point,
                    radius=5,
                    color=route["color"],
                    fill=True,
                    fill_opacity=0.95,
                    tooltip=f'{route["name"]} — {label}',
                ).add_to(group)

        if show_labels:
            midpoint = coordinates[len(coordinates) // 2]
            folium.Marker(
                location=midpoint,
                icon=folium.DivIcon(
                    html=(
                        '<div style="font-size:11px;font-weight:600;'
                        'color:#222;background:rgba(255,255,255,.82);'
                        'padding:2px 4px;border-radius:3px;white-space:nowrap;">'
                        f'{route["name"]}</div>'
                    )
                ),
            ).add_to(group)

        group.add_to(fmap)

    Fullscreen(position="topleft", title="Tam ekran", title_cancel="Kapat").add_to(fmap)
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Koordinat",
        num_digits=4,
    ).add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    # Seçili rotalar varsa haritayı onların sınırlarına yaklaştır.
    if route_rows:
        all_points = [point for route in route_rows for point in route["coordinates"]]
        lats = [p[0] for p in all_points]
        lons = [p[1] for p in all_points]
        fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(25, 25))

    return fmap


def make_geojson(route_gdf: gpd.GeoDataFrame) -> bytes:
    """GeoJSON standardına uygun WGS84 çıktı; boş seçimde FeatureCollection boş olur."""
    if route_gdf.empty:
        payload = {"type": "FeatureCollection", "features": []}
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    safe = route_gdf[["id", "name", "category", "description", "color", "geometry"]].copy()
    safe = safe.set_crs("EPSG:4326", allow_override=True).to_crs("EPSG:4326")
    return safe.to_json(to_wgs84=True, drop_id=False).encode("utf-8")


def make_csv(route_rows: list[dict[str, Any]]) -> bytes:
    """CSV, rota koordinatlarını açıkça enlem/boylam çiftleri olarak taşır."""
    rows = []
    for route in route_rows:
        rows.append(
            {
                "id": route["id"],
                "name": route["name"],
                "category": route["category"],
                "description": route["description"],
                "color": route["color"],
                "coordinates_lat_lon_json": json.dumps(
                    route["coordinates"], ensure_ascii=False
                ),
            }
        )
    columns = [
        "id", "name", "category", "description", "color",
        "coordinates_lat_lon_json",
    ]
    return pd.DataFrame(rows, columns=columns).to_csv(index=False).encode("utf-8-sig")


st.title("🗺️ Hazar ve Oğur — Şematik Güzergâh Haritası")
st.warning(DISCLAIMER)

with st.sidebar:
    st.header("Harita ayarları")
    basemap = st.selectbox(
        "Taban haritası",
        ["OpenStreetMap", "CartoDB Positron", "CartoDB Dark Matter"],
        index=0,
    )
    show_countries = st.checkbox("Ülke sınırlarını göster", value=True)
    show_points = st.checkbox("Başlangıç/bitiş noktalarını göster", value=True)
    show_labels = st.checkbox("Rota etiketlerini göster", value=True)
    show_arrows = st.checkbox("Yön oklarını göster", value=True)

    st.divider()
    st.subheader("Güzergâh seçimi")
    select_all = st.button("Tümünü seç", use_container_width=True)
    deselect_all = st.button("Seçimi temizle", use_container_width=True)

    all_route_ids = [r["id"] for r in ROUTES]
    if "route_multiselect" not in st.session_state:
        st.session_state.route_multiselect = all_route_ids.copy()

    # Widget oluşturulmadan önce aynı widget anahtarını güncellemek güvenlidir.
    if select_all:
        st.session_state.route_multiselect = all_route_ids.copy()
    if deselect_all:
        st.session_state.route_multiselect = []

    selected_ids = st.multiselect(
        "Gösterilecek güzergâhlar",
        options=all_route_ids,
        format_func=lambda route_id: next(
            (r["name"] for r in ROUTES if r["id"] == route_id), route_id
        ),
        key="route_multiselect",
    )

selected_routes = [r for r in ROUTES if r["id"] in selected_ids]
gdf = make_route_gdf(selected_routes)

left, right = st.columns([3, 1], gap="large")
with left:
    if not selected_routes:
        st.info("Hiç güzergâh seçilmedi. Taban haritası açık kalır; dışa aktarımlar boş olur.")

    fmap = make_map(
        route_rows=selected_routes,
        basemap=basemap,
        show_countries=show_countries,
        show_points=show_points,
        show_labels=show_labels,
        show_arrows=show_arrows,
    )
    st_folium(
        fmap,
        height=650,
        use_container_width=True,
        returned_objects=[],
        key="hazar_ogur_map",
    )

with right:
    st.subheader("Seçim özeti")
    st.metric("Seçili güzergâh", len(selected_routes))
    st.metric("Çizgi geometrisi", len(gdf))
    st.caption("Bu kayıtlar şematik araştırma verileridir; doğrulanmış tarihsel rota verisi değildir.")

    st.download_button(
        "GeoJSON indir",
        data=make_geojson(gdf),
        file_name="hazar_ogur_routes.geojson",
        mime="application/geo+json",
        use_container_width=True,
    )
    st.download_button(
        "CSV indir",
        data=make_csv(selected_routes),
        file_name="hazar_ogur_routes.csv",
        mime="text/csv",
        use_container_width=True,
    )

with st.expander("Veri tablosu"):
    if selected_routes:
        table = pd.DataFrame(
            [
                {
                    "ID": r["id"],
                    "Güzergâh": r["name"],
                    "Kategori": r["category"],
                    "Açıklama": r["description"],
                }
                for r in selected_routes
            ]
        )
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.write("Seçili kayıt yok.")

st.caption("Taban haritası ve çevrim içi ülke sınırları için internet bağlantısı gerekir.")
