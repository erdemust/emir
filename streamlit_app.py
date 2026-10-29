
from __future__ import annotations

import html
import io
import json
import math
from typing import Any

import pandas as pd
import folium
import streamlit as st
from folium.plugins import Fullscreen, MiniMap, MousePosition
from shapely.geometry import shape, mapping, Point
from shapely import wkt
from streamlit_folium import st_folium


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hazar–Oğur Atlası",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Hazar–Oğur Atlası"
APP_SUBTITLE = "Tarihî coğrafya • Göç güzergâhları • Coğrafi veri laboratuvarı"


# ============================================================
# TASARIM
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --navy: #101c32;
        --navy2: #172944;
        --blue: #3978f6;
        --muted: #69778c;
        --line: #e4eaf2;
        --panel: #ffffff;
        --bg: #f4f7fb;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, sans-serif;
    }

    .stApp {
        background: var(--bg);
    }

    [data-testid="stHeader"] {
        background: rgba(244,247,251,.88);
    }

    .block-container {
        max-width: 1600px;
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
    }

    [data-testid="stSidebar"] {
        background: #fff;
        border-right: 1px solid var(--line);
    }

    .hero {
        background: linear-gradient(120deg, #101c32 0%, #1b3456 65%, #24518a 100%);
        border-radius: 22px;
        padding: 27px 30px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 30px rgba(16,28,50,.13);
        position: relative;
        overflow: hidden;
    }

    .hero:after {
        content: "◉";
        position: absolute;
        right: 28px;
        top: -53px;
        font-size: 190px;
        line-height: 1;
        color: rgba(255,255,255,.055);
    }

    .hero-kicker {
        color: #9fc3ff;
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-weight: 800;
        margin-bottom: 9px;
    }

    .hero h1 {
        color: #fff;
        font-size: clamp(25px, 3vw, 38px);
        line-height: 1.15;
        margin: 0 0 10px 0;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .hero p {
        color: #d3deed;
        font-size: 14px;
        margin: 0;
        max-width: 750px;
    }

    .metric {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 15px;
        padding: 17px 19px;
        min-height: 105px;
        box-shadow: 0 3px 12px rgba(30,50,80,.025);
    }

    .metric-label {
        font-size: 12px;
        color: var(--muted);
        font-weight: 600;
        margin-bottom: 9px;
    }

    .metric-value {
        font-size: 28px;
        line-height: 1.1;
        font-weight: 800;
        color: var(--navy);
    }

    .metric-note {
        color: #8a96a8;
        font-size: 11px;
        margin-top: 7px;
    }

    .section-heading {
        color: var(--navy);
        font-size: 18px;
        font-weight: 800;
        margin: 5px 0 4px 0;
    }

    .section-caption {
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 13px;
    }

    .panel {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 17px;
        padding: 16px;
    }

    .map-note {
        color: #68778b;
        font-size: 12px;
        margin-top: 8px;
    }

    div[data-testid="stTabs"] button {
        font-weight: 700;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 10px;
        font-weight: 700;
    }

    .footer {
        border-top: 1px solid var(--line);
        margin-top: 28px;
        padding-top: 14px;
        color: #8490a2;
        font-size: 11px;
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# YERLEŞİK ÖRNEK VERİ
# Koordinatlar GeoJSON standardına uygun olarak [boylam, enlem].
# Bu kayıtlar tarihî iddiaların kesin kanıtı değil, görselleştirme
# için başlangıç veri kümesidir.
# ============================================================

DEFAULT_FEATURES = [
    {
        "type": "Feature",
        "properties": {
            "name": "Ujur / Uygur",
            "description": "Orhun bölgesi → Jetisu",
            "color": "#2563eb",
            "label_dx": 1.5,
            "label_dy": 0.8,
            "group": "Sınıflandırılmamış",
            "label": "Ujur / Uygur",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[102, 47], [75, 45]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Tauris",
            "description": "Kırım (yerel)",
            "color": "#059669",
            "label_dx": 0.9,
            "label_dy": -1.7,
            "group": "Sınıflandırılmamış",
            "label": "Tauris",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [34, 45],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Avar",
            "description": "Kafkasya → Pannonia",
            "color": "#dc2626",
            "label_dx": 0.9,
            "label_dy": 0.6,
            "group": "Sınıflandırılmamış",
            "label": "Avar",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[47, 42], [19, 47]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Uauz / Oguz",
            "description": "Aral/Hazar → Anadolu",
            "color": "#d97706",
            "label_dx": 0.9,
            "label_dy": -1.5,
            "group": "Sınıflandırılmamış",
            "label": "Uauz / Oguz",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[60, 43], [35, 39]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Bizal / Barsil",
            "description": "Volga-Don / Kuzey Kafkasya",
            "color": "#7c3aed",
            "label_dx": 1.0,
            "label_dy": 1.2,
            "group": "Sınıflandırılmamış",
            "label": "Bizal / Barsil",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [42, 48],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Tarna",
            "description": "Dağıstan / Tarku",
            "color": "#db2777",
            "label_dx": 1.0,
            "label_dy": -1.4,
            "group": "Sınıflandırılmamış",
            "label": "Tarna",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [47.5, 42.9],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Khazar",
            "description": "Aşağı Volga / İtil",
            "color": "#4f46e5",
            "label_dx": 1.6,
            "label_dy": 0.7,
            "group": "Sınıflandırılmamış",
            "label": "Khazar",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [48, 46],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Janur / Zagur",
            "description": "Azak / Kuban",
            "color": "#0891b2",
            "label_dx": -7.2,
            "label_dy": 0.9,
            "group": "Sınıflandırılmamış",
            "label": "Janur / Zagur",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [39, 45.2],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Bulgar",
            "description": "Kuban → Volga",
            "color": "#ea580c",
            "label_dx": 1.0,
            "label_dy": 1.0,
            "group": "Sınıflandırılmamış",
            "label": "Bulgar",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[39, 46.8], [49, 55]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Sabir / Suvar",
            "description": "Batı Sibirya → Kafkasya",
            "color": "#16a34a",
            "label_dx": 1.0,
            "label_dy": -1.4,
            "group": "Sınıflandırılmamış",
            "label": "Sabir / Suvar",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[75, 55], [47, 43]],
        },
    },
]


# ============================================================
# VERİ NORMALİZASYONU VE DOĞRULAMA
# ============================================================

def safe_color(value: Any) -> str:
    value = str(value or "#3978f6").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass
    return "#3978f6"


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).replace(",", "."))
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def normalize_feature(feature: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(feature, dict):
        raise ValueError("Her özellik bir JSON nesnesi olmalıdır.")

    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError("Geometri bulunamadı.")

    geom = shape(geometry)
    if geom.is_empty:
        raise ValueError("Boş geometri kabul edilmez.")

    supported = {
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon",
    }
    if geom.geom_type not in supported:
        raise ValueError(f"Desteklenmeyen geometri: {geom.geom_type}")

    if not geom.is_valid:
        raise ValueError("Geometri geçerli değil.")

    if not all(math.isfinite(v) for v in geom.bounds):
        raise ValueError("Koordinatlar sonlu sayılar olmalıdır.")

    minx, miny, maxx, maxy = geom.bounds
    if minx < -180 or maxx > 180 or miny < -90 or maxy > 90:
        raise ValueError(
            "Koordinatlar GeoJSON standardına göre [boylam, enlem] olmalıdır."
        )

    props = dict(feature.get("properties") or {})

    name = (
        props.get("name")
        or props.get("label")
        or props.get("nombre")
        or props.get("ad")
        or "İsimsiz kayıt"
    )

    description = (
        props.get("description")
        or props.get("descripcion")
        or props.get("aciklama")
        or ""
    )

    group = props.get("group") or props.get("grupo") or "Sınıflandırılmamış"

    props["name"] = str(name)
    props["label"] = str(props.get("label") or name)
    props["description"] = str(description)
    props["group"] = str(group)
    props["color"] = safe_color(props.get("color"))
    props["label_dx"] = safe_number(props.get("label_dx"), 0.8)
    props["label_dy"] = safe_number(props.get("label_dy"), 0.8)
    props["geometry_type"] = geom.geom_type

    return {
        "type": "Feature",
        "properties": props,
        "geometry": mapping(geom),
    }


def normalize_collection(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif isinstance(data, dict) and data.get("type") == "Feature":
        features = [data]
    elif isinstance(data, list):
        features = data
    else:
        raise ValueError(
            "Dosya FeatureCollection, Feature veya özellik listesi olmalıdır."
        )

    normalized = []
    errors = []

    for index, feature in enumerate(features):
        try:
            normalized.append(normalize_feature(feature))
        except Exception as exc:
            errors.append(f"Kayıt {index + 1}: {exc}")

    if not normalized:
        detail = "\n".join(errors[:5])
        raise ValueError("Geçerli kayıt bulunamadı.\n" + detail)

    if errors:
        st.warning(
            f"{len(errors)} kayıt atlandı; {len(normalized)} kayıt yüklendi. "
            + " | ".join(errors[:3])
        )

    return normalized


def load_csv(uploaded_file) -> list[dict[str, Any]]:
    df = pd.read_csv(uploaded_file)
    df.columns = [
        str(column).strip().lstrip("*").lower()
        for column in df.columns
    ]

    # Yaygın eski sütun adlarını eşleştir.
    aliases = {
        "nombre": "name",
        "descripcion": "description",
        "grupo": "group",
        "tipo_geometria": "geometry_type",
        "label_dy": "label_dy",
    }
    df = df.rename(columns=aliases)

    features = []

    for _, row in df.iterrows():
        row_data = row.to_dict()

        if "geometry" in row_data and pd.notna(row_data["geometry"]):
            geom = wkt.loads(str(row_data["geometry"]))
        elif (
            pd.notna(row_data.get("start_lon"))
            and pd.notna(row_data.get("start_lat"))
        ):
            start = [
                safe_number(row_data["start_lon"]),
                safe_number(row_data["start_lat"]),
            ]

            if (
                pd.notna(row_data.get("end_lon"))
                and pd.notna(row_data.get("end_lat"))
            ):
                end = [
                    safe_number(row_data["end_lon"]),
                    safe_number(row_data["end_lat"]),
                ]
                from shapely.geometry import LineString
                geom = LineString([start, end])
            else:
                geom = Point(start)
        elif (
            pd.notna(row_data.get("lon"))
            and pd.notna(row_data.get("lat"))
        ):
            geom = Point(
                safe_number(row_data["lon"]),
                safe_number(row_data["lat"]),
            )
        else:
            continue

        properties = {
            key: value
            for key, value in row_data.items()
            if key not in {"geometry", "start_lon", "start_lat", "end_lon", "end_lat", "lon", "lat"}
            and pd.notna(value)
        }

        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": mapping(geom),
        })

    return normalize_collection(features)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 🌍 Atlas kontrolü")
    st.caption("Veri kümesini seç ve haritayı özelleştir.")

    uploaded = st.file_uploader(
        "GeoJSON, JSON veya CSV yükle",
        type=["geojson", "json", "csv"],
        help="CSV için geometry sütununda WKT veya lon/lat sütunları kullanabilirsin.",
    )

    if st.button("↺ Varsayılan verilere dön", use_container_width=True):
        st.session_state.pop("custom_features", None)
        st.rerun()

    st.divider()
    st.markdown("### Görünüm")

    show_labels = st.toggle("Harita etiketlerini göster", value=True)
    fit_bounds = st.toggle("Veri kümesini haritaya sığdır", value=True)
    show_minimap = st.toggle("Küçük genel bakış haritası", value=False)

    st.divider()
    st.markdown("### Filtreler")
    st.caption("Filtreler hem haritaya hem tabloya uygulanır.")


# ============================================================
# DOSYA YÜKLEME
# ============================================================

if "custom_features" not in st.session_state:
    st.session_state["custom_features"] = None

if uploaded is not None:
    try:
        uploaded.seek(0)
        if uploaded.name.lower().endswith(".csv"):
            features = load_csv(uploaded)
        else:
            features = normalize_collection(
                json.loads(uploaded.getvalue().decode("utf-8-sig"))
            )
        st.session_state["custom_features"] = features
    except Exception as exc:
        st.error(f"Dosya okunamadı: {exc}")

features_all = (
    st.session_state["custom_features"]
    if st.session_state["custom_features"] is not None
    else normalize_collection(DEFAULT_FEATURES)
)

groups = sorted({
    str(f["properties"].get("group", "Sınıflandırılmamış"))
    for f in features_all
})
geometry_types = sorted({
    f["geometry"]["type"] for f in features_all
})

with st.sidebar:
    selected_groups = st.multiselect(
        "Gruplar",
        options=groups,
        default=groups,
    )

    selected_types = st.multiselect(
        "Geometri türleri",
        options=geometry_types,
        default=geometry_types,
    )

    search_text = st.text_input(
        "Kayıt ara",
        placeholder="Örn. Khazar, Bulgar...",
    )


# ============================================================
# FİLTRELEME
# ============================================================

filtered = []

for feature in features_all:
    props = feature["properties"]
    geom_type = feature["geometry"]["type"]

    if props.get("group", "Sınıflandırılmamış") not in selected_groups:
        continue
    if geom_type not in selected_types:
        continue

    searchable = " ".join([
        str(props.get("name", "")),
        str(props.get("description", "")),
        str(props.get("group", "")),
    ]).casefold()

    if search_text.strip().casefold() not in searchable:
        continue

    filtered.append(feature)


# ============================================================
# BAŞLIK VE İSTATİSTİKLER
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">INTERACTIVE HISTORICAL GEOGRAPHY</div>
        <h1>🌍 {APP_NAME}</h1>
        <p>{APP_SUBTITLE}<br>
        Tarihî kayıtları harita üzerinde incele, filtrele ve dışa aktar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

point_count = sum(
    shape(f["geometry"]).geom_type in {"Point", "MultiPoint"}
    for f in filtered
)
line_count = sum(
    shape(f["geometry"]).geom_type in {"LineString", "MultiLineString"}
    for f in filtered
)
area_count = sum(
    shape(f["geometry"]).geom_type in {"Polygon", "MultiPolygon"}
    for f in filtered
)

c1, c2, c3, c4 = st.columns(4)

metrics = [
    (c1, "GÖSTERİLEN KAYIT", len(filtered), "Aktif filtrelerden sonra"),
    (c2, "NOKTA / ÇOKLU NOKTA", point_count, "Konum kayıtları"),
    (c3, "GÜZERGÂH", line_count, "Çizgi geometrileri"),
    (c4, "ALAN / BÖLGE", area_count, "Poligon geometrileri"),
]

for col, label, value, note in metrics:
    with col:
        st.markdown(
            f"""
            <div class="metric">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")


# ============================================================
# HARİTA ÜRETİMİ
# ============================================================

def feature_label_location(feature: dict[str, Any]) -> tuple[float, float]:
    geom = shape(feature["geometry"])
    props = feature["properties"]

    if geom.geom_type == "Point":
        lon, lat = geom.x, geom.y
    elif geom.geom_type == "MultiPoint":
        point = list(geom.geoms)[0]
        lon, lat = point.x, point.y
    elif geom.geom_type in {"LineString", "MultiLineString"}:
        line = geom if geom.geom_type == "LineString" else max(
            geom.geoms, key=lambda part: part.length
        )
        point = line.interpolate(0.5, normalized=True)
        lon, lat = point.x, point.y
    else:
        point = geom.representative_point()
        lon, lat = point.x, point.y

    lon += safe_number(props.get("label_dx"), 0.0)
    lat += safe_number(props.get("label_dy"), 0.0)

    # Leaflet haritasında geçersiz enlem oluşmasını engelle.
    lat = max(-85, min(85, lat))
    lon = max(-180, min(180, lon))
    return lat, lon


def build_map(data: list[dict[str, Any]]) -> folium.Map:
    # OpenStreetMap varsayılan ve ilk açılış katmanıdır.
    m = folium.Map(
        location=[45.0, 45.0],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=True,
    )

    # Alternatif taban katmanı.
    folium.TileLayer(
        "CartoDB Positron",
        name="Açık renkli harita",
        overlay=False,
        control=True,
    ).add_to(m)

    route_layer = folium.FeatureGroup(
        name="Güzergâhlar",
        show=True,
    ).add_to(m)

    point_layer = folium.FeatureGroup(
        name="Konum noktaları",
        show=True,
    ).add_to(m)

    area_layer = folium.FeatureGroup(
        name="Alanlar",
        show=True,
    ).add_to(m)

    label_layer = folium.FeatureGroup(
        name="İsim etiketleri",
        show=show_labels,
    ).add_to(m)

    all_bounds = []

    for feature in data:
        props = feature["properties"]
        geom = shape(feature["geometry"])
        color = safe_color(props.get("color"))
        name = html.escape(str(props.get("name", "İsimsiz")))
        description = html.escape(str(props.get("description", "")))
        group = html.escape(str(props.get("group", "")))
        geom_type = geom.geom_type

        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:190px;max-width:280px">
            <div style="font-size:16px;font-weight:800;color:#14233b;margin-bottom:8px">
                {name}
            </div>
            <div style="margin-bottom:8px;color:#526178">{description}</div>
            <div style="font-size:11px;color:#7a8798">
                <b>Geometri:</b> {html.escape(geom_type)}<br>
                <b>Grup:</b> {group}
            </div>
        </div>
        """

        tooltip = folium.Tooltip(
            f"<b>{name}</b><br>{description}",
            sticky=True,
        )

        if geom_type in {"Point", "MultiPoint"}:
            target_layer = point_layer
        elif geom_type in {"LineString", "MultiLineString"}:
            target_layer = route_layer
        else:
            target_layer = area_layer

        folium.GeoJson(
            feature,
            name=str(props.get("name", "Kayıt")),
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=320),
            style_function=lambda _f, c=color: {
                "color": c,
                "weight": 4,
                "opacity": 0.90,
                "fillColor": c,
                "fillOpacity": 0.20,
            },
            highlight_function=lambda _f: {
                "weight": 6,
                "opacity": 1.0,
                "fillOpacity": 0.35,
            },
            marker=folium.CircleMarker(
                radius=7,
                weight=2,
                color="#ffffff",
                fill=True,
                fill_opacity=1,
            ),
            zoom_on_click=True,
        ).add_to(target_layer)

        if show_labels:
            label_lat, label_lon = feature_label_location(feature)
            label_text = html.escape(
                str(props.get("label") or props.get("name") or "")
            )

            folium.Marker(
                location=[label_lat, label_lon],
                interactive=False,
                icon=folium.DivIcon(
                    icon_size=(180, 28),
                    icon_anchor=(0, 12),
                    html=f"""
                    <div style="
                        display:inline-block;
                        white-space:nowrap;
                        padding:4px 8px;
                        border-radius:6px;
                        background:rgba(255,255,255,.94);
                        border:1px solid {color};
                        box-shadow:0 2px 7px rgba(20,35,59,.16);
                        color:#172944;
                        font-size:11px;
                        font-weight:800;
                        font-family:Arial,sans-serif;
                    ">{label_text}</div>
                    """,
                ),
            ).add_to(label_layer)

        minx, miny, maxx, maxy = geom.bounds
        all_bounds.append((minx, miny, maxx, maxy))

    if fit_bounds and all_bounds:
        min_lon = min(b[0] for b in all_bounds)
        min_lat = min(b[1] for b in all_bounds)
        max_lon = max(b[2] for b in all_bounds)
        max_lat = max(b[3] for b in all_bounds)

        if min_lon == max_lon:
            min_lon -= 0.5
            max_lon += 0.5
        if min_lat == max_lat:
            min_lat -= 0.5
            max_lat += 0.5

        m.fit_bounds(
            [[min_lat, min_lon], [max_lat, max_lon]],
            padding=(35, 35),
        )

    if show_minimap:
        MiniMap(toggle_display=True, position="bottomleft").add_to(m)

    Fullscreen(
        position="topleft",
        title="Tam ekran",
        title_cancel="Tam ekrandan çık",
        force_separate_button=True,
    ).add_to(m)

    MousePosition(
        position="bottomright",
        separator=" | ",
        prefix="Koordinat:",
        num_digits=4,
    ).add_to(m)

    folium.LayerControl(
        collapsed=False,
        position="topright",
    ).add_to(m)

    return m


# ============================================================
# SEKME YAPISI
# ============================================================

tab_map, tab_data, tab_export, tab_about = st.tabs([
    "🗺️ Harita",
    "📋 Veri kayıtları",
    "⬇️ Dışa aktarma",
    "ⓘ Hakkında",
])

with tab_map:
    st.markdown(
        '<div class="section-heading">Coğrafi keşif alanı</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-caption">'
        'Yakınlaştır, haritayı sürükle, katmanları aç/kapat ve '
        'bir kayıt seçerek ayrıntılarını incele.'
        '</div>',
        unsafe_allow_html=True,
    )

    if not filtered:
        st.warning("Seçili filtrelerle eşleşen kayıt bulunamadı.")
    else:
        current_map = build_map(filtered)
        st_folium(
            current_map,
            width=None,
            height=680,
            returned_objects=[],
            key="hazar_ogur_map",
        )

    st.markdown(
        '<div class="map-note">'
        'Harita altyapısı: OpenStreetMap. Harita verileri internet bağlantısı '
        'gerektirir. Güzergâh çizgileri kaynak veri kümesindeki koordinatları '
        'gösterir; tek başına tarihî sınır veya kesin göç rotası kanıtı değildir.'
        '</div>',
        unsafe_allow_html=True,
    )

with tab_data:
    st.markdown("### 📋 Veri kayıtları")
    st.caption(f"{len(filtered)} kayıt görüntüleniyor.")

    rows = []
    for feature in filtered:
        props = feature["properties"]
        geom = shape(feature["geometry"])
        rows.append({
            "Ad": props.get("name", ""),
            "Açıklama": props.get("description", ""),
            "Grup": props.get("group", ""),
            "Geometri": geom.geom_type,
            "Boylam": round(geom.centroid.x, 5),
            "Enlem": round(geom.centroid.y, 5),
            "Renk": props.get("color", ""),
        })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=520,
        )
    else:
        st.info("Görüntülenecek kayıt yok.")

with tab_export:
    st.markdown("### ⬇️ Verilerini dışa aktar")
    st.caption("Mevcut filtrelerle eşleşen kayıtlar dışa aktarılır.")

    geojson_output = {
        "type": "FeatureCollection",
        "features": filtered,
    }

    geojson_bytes = json.dumps(
        geojson_output,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    export_rows = []
    for feature in filtered:
        props = feature["properties"]
        export_rows.append({
            "name": props.get("name", ""),
            "description": props.get("description", ""),
            "group": props.get("group", ""),
            "color": props.get("color", ""),
            "label": props.get("label", ""),
            "label_dx": props.get("label_dx", 0),
            "label_dy": props.get("label_dy", 0),
            "geometry": json.dumps(
                feature["geometry"],
                ensure_ascii=False,
            ),
        })

    csv_buffer = io.StringIO()
    pd.DataFrame(export_rows).to_csv(
        csv_buffer,
        index=False,
        encoding="utf-8",
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### GeoJSON")
        st.write("Geometri, özellikler ve renk bilgileri korunur.")
        st.download_button(
            "⬇️ GeoJSON indir",
            data=geojson_bytes,
            file_name="hazar_ogur_atlas.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )

    with col_b:
        st.markdown("#### CSV")
        st.write("Tablo verilerini elektronik tabloda aç.")
        st.download_button(
            "⬇️ CSV indir",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="hazar_ogur_atlas.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.info(
        "CSV dışa aktarımındaki geometry alanı GeoJSON geometri nesnesini "
        "JSON metni olarak içerir. CSV yüklemede ise WKT geometry veya "
        "lon/lat koordinat sütunları desteklenir."
    )

with tab_about:
    st.markdown("### ⓘ Atlas hakkında")
    st.markdown(
        """
        **Hazar–Oğur Atlası**, coğrafi özellikleri harita üzerinde incelemek
        için hazırlanmış etkileşimli bir prototiptir.

        **Özellikler**
        - OpenStreetMap taban haritası
        - Nokta, çizgi ve poligon geometrileri
        - Katman kontrolü, koordinat gösterimi ve tam ekran
        - GeoJSON, JSON ve CSV veri yükleme
        - CSV ve GeoJSON dışa aktarma

        **Bilimsel kullanım notu**

        Haritadaki isimler, açıklamalar ve güzergâhlar başlangıç veri
        kümesinden gelir. Tarihî doğruluk, tarihlendirme, kaynakça ve
        koordinat doğrulaması ayrı bir araştırma süreci gerektirir.
        Görselleştirme tek başına tarihî bir iddiayı doğrulamaz.
        """
    )

st.markdown(
    """
    <div class="footer">
        Hazar–Oğur Atlası · Streamlit + Folium · OpenStreetMap
        <br>OpenStreetMap harita verisi ve atıf koşulları:
        © OpenStreetMap contributors
    </div>
    """,
    unsafe_allow_html=True,
)
