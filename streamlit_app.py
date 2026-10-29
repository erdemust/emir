
from __future__ import annotations

import html
import io
import json
import math
from typing import Any

import folium
import pandas as pd
import streamlit as st
from shapely import wkt
from shapely.geometry import Point, LineString, mapping, shape
from streamlit_folium import st_folium


# ============================================================
# 1. SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hazar–Oğur Atlası",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Hazar–Oğur Atlası"
APP_VERSION = "2.0.0"


# ============================================================
# 2. KOYU TEMA TASARIMI
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg: #0b1120;
        --panel: #111b2e;
        --panel2: #17243a;
        --border: #263650;
        --text: #e8eef8;
        --muted: #94a3b8;
        --blue: #60a5fa;
        --cyan: #22d3ee;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, sans-serif;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 10% 0%, rgba(37,99,235,.12), transparent 35%),
            #0b1120;
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(11,17,32,.90);
    }

    .block-container {
        max-width: 1700px;
        padding-top: 1.3rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background: #0e1728;
        border-right: 1px solid #263650;
    }

    [data-testid="stSidebar"] * {
        color: #e8eef8;
    }

    [data-testid="stSidebar"] hr {
        border-color: #263650;
    }

    h1, h2, h3 {
        color: #f1f5f9;
        letter-spacing: -.4px;
    }

    p, label, .stCaption {
        color: #c1cddd;
    }

    .hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(115deg, #111b2e 0%, #172b49 58%, #123c58 100%);
        border: 1px solid #2c4565;
        border-radius: 22px;
        padding: 27px 30px;
        margin-bottom: 20px;
        box-shadow: 0 14px 40px rgba(0,0,0,.22);
    }

    .hero:after {
        content: "◉";
        position: absolute;
        right: 24px;
        top: -72px;
        font-size: 230px;
        line-height: 1;
        color: rgba(125,211,252,.06);
        pointer-events: none;
    }

    .hero-kicker {
        color: #7dd3fc;
        text-transform: uppercase;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2.2px;
        margin-bottom: 10px;
    }

    .hero h1 {
        font-size: clamp(27px, 3vw, 40px);
        line-height: 1.15;
        font-weight: 800;
        color: #f8fafc;
        margin: 0 0 10px 0;
    }

    .hero p {
        max-width: 850px;
        font-size: 14px;
        line-height: 1.7;
        color: #c7d6e8;
        margin: 0;
    }

    .hero-chip {
        display: inline-block;
        border: 1px solid rgba(125,211,252,.30);
        background: rgba(8,145,178,.15);
        color: #a5f3fc;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
        margin-top: 15px;
        margin-right: 6px;
    }

    .metric {
        background: linear-gradient(145deg, #111b2e, #131f34);
        border: 1px solid #263650;
        border-radius: 16px;
        padding: 17px 19px;
        min-height: 112px;
        box-shadow: 0 5px 18px rgba(0,0,0,.10);
    }

    .metric-label {
        font-size: 11px;
        letter-spacing: .8px;
        font-weight: 700;
        color: #94a3b8;
        margin-bottom: 10px;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 30px;
        font-weight: 800;
        line-height: 1.1;
    }

    .metric-note {
        color: #8495ad;
        font-size: 11px;
        margin-top: 8px;
    }

    .section-title {
        color: #f1f5f9;
        font-size: 19px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .section-subtitle {
        color: #94a3b8;
        font-size: 12px;
        margin-bottom: 15px;
    }

    div[data-testid="stTabs"] button {
        color: #b7c5d9;
        font-weight: 700;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #7dd3fc;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background: #38bdf8;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stMultiSelect"] > div > div {
        background: #111b2e;
        color: #e8eef8;
        border-color: #334761;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {
        background: #173d66;
        color: #f8fafc;
        border: 1px solid #2e6595;
        border-radius: 10px;
        font-weight: 700;
        transition: all .15s ease;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        background: #205482;
        border-color: #60a5fa;
        color: white;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263650;
        border-radius: 12px;
        overflow: hidden;
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
    }

    .footer {
        border-top: 1px solid #263650;
        padding-top: 15px;
        margin-top: 28px;
        font-size: 11px;
        line-height: 1.8;
        color: #8495ad;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. BAŞLANGIÇ VERİSİ
# Koordinatlar GeoJSON standardına göre [boylam, enlem].
# Örnek veri; tarihî doğruluğun ayrıca kaynaklarla doğrulanması gerekir.
# ============================================================

DEFAULT_FEATURES = [
    {
        "type": "Feature",
        "properties": {
            "name": "Ujur / Uygur",
            "description": "Orhun bölgesi → Jetisu",
            "color": "#3b82f6",
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
            "color": "#10b981",
            "label_dx": 0.9,
            "label_dy": -1.7,
            "group": "Sınıflandırılmamış",
            "label": "Tauris",
        },
        "geometry": {"type": "Point", "coordinates": [34, 45]},
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Avar",
            "description": "Kafkasya → Pannonia",
            "color": "#ef4444",
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
            "color": "#f59e0b",
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
            "color": "#a78bfa",
            "label_dx": 1.0,
            "label_dy": 1.2,
            "group": "Sınıflandırılmamış",
            "label": "Bizal / Barsil",
        },
        "geometry": {"type": "Point", "coordinates": [42, 48]},
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Tarna",
            "description": "Dağıstan / Tarku",
            "color": "#f472b6",
            "label_dx": 1.0,
            "label_dy": -1.4,
            "group": "Sınıflandırılmamış",
            "label": "Tarna",
        },
        "geometry": {"type": "Point", "coordinates": [47.5, 42.9]},
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Khazar",
            "description": "Aşağı Volga / İtil",
            "color": "#818cf8",
            "label_dx": 1.6,
            "label_dy": 0.7,
            "group": "Sınıflandırılmamış",
            "label": "Khazar",
        },
        "geometry": {"type": "Point", "coordinates": [48, 46]},
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Janur / Zagur",
            "description": "Azak / Kuban",
            "color": "#22d3ee",
            "label_dx": -7.2,
            "label_dy": 0.9,
            "group": "Sınıflandırılmamış",
            "label": "Janur / Zagur",
        },
        "geometry": {"type": "Point", "coordinates": [39, 45.2]},
    },
    {
        "type": "Feature",
        "properties": {
            "name": "Bulgar",
            "description": "Kuban → Volga",
            "color": "#fb923c",
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
            "color": "#4ade80",
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
# 4. VERİ DOĞRULAMA VE DÖNÜŞÜM
# ============================================================

def safe_color(value: Any) -> str:
    value = str(value or "#60a5fa").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass
    return "#60a5fa"


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip().replace(",", "."))
        if math.isfinite(number):
            return number
    except (ValueError, TypeError):
        pass
    return default


def normalize_feature(feature: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(feature, dict):
        raise ValueError("Özellik bir JSON nesnesi olmalıdır.")

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

    if not all(math.isfinite(value) for value in geom.bounds):
        raise ValueError("Koordinatlar geçerli sayılar olmalıdır.")

    minx, miny, maxx, maxy = geom.bounds
    if minx < -180 or maxx > 180 or miny < -90 or maxy > 90:
        raise ValueError(
            "Koordinatlar [boylam, enlem] sırasıyla ve geçerli aralıkta olmalıdır."
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

    group = (
        props.get("group")
        or props.get("grupo")
        or "Sınıflandırılmamış"
    )

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
        items = data.get("features", [])
    elif isinstance(data, dict) and data.get("type") == "Feature":
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(
            "Dosya FeatureCollection, Feature veya özellik listesi olmalıdır."
        )

    valid_features = []
    errors = []

    for index, feature in enumerate(items):
        try:
            valid_features.append(normalize_feature(feature))
        except Exception as exc:
            errors.append(f"Kayıt {index + 1}: {exc}")

    if not valid_features:
        raise ValueError(
            "Dosyada geçerli kayıt bulunamadı. "
            + " | ".join(errors[:4])
        )

    if errors:
        st.warning(
            f"{len(errors)} kayıt atlandı. "
            f"{len(valid_features)} geçerli kayıt yüklendi. "
            + " | ".join(errors[:3])
        )

    return valid_features


def load_uploaded_file(uploaded_file) -> list[dict[str, Any]]:
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df.columns = [
            str(col).strip().lstrip("*").lower()
            for col in df.columns
        ]

        aliases = {
            "nombre": "name",
            "descripcion": "description",
            "grupo": "group",
        }
        df = df.rename(columns=aliases)

        features = []

        for _, row in df.iterrows():
            data = row.to_dict()

            if "geometry" in data and pd.notna(data["geometry"]):
                geom_text = str(data["geometry"]).strip()

                try:
                    geom = wkt.loads(geom_text)
                except Exception:
                    try:
                        geom = shape(json.loads(geom_text))
                    except Exception as exc:
                        raise ValueError(
                            "CSV geometry sütunu WKT veya GeoJSON geometri "
                            "metni içermelidir."
                        ) from exc

            elif (
                pd.notna(data.get("start_lon"))
                and pd.notna(data.get("start_lat"))
            ):
                start = [
                    safe_number(data["start_lon"]),
                    safe_number(data["start_lat"]),
                ]

                if (
                    pd.notna(data.get("end_lon"))
                    and pd.notna(data.get("end_lat"))
                ):
                    end = [
                        safe_number(data["end_lon"]),
                        safe_number(data["end_lat"]),
                    ]
                    geom = LineString([start, end])
                else:
                    geom = Point(start)

            elif (
                pd.notna(data.get("lon"))
                and pd.notna(data.get("lat"))
            ):
                geom = Point(
                    safe_number(data["lon"]),
                    safe_number(data["lat"]),
                )
            else:
                continue

            props = {
                key: value
                for key, value in data.items()
                if key not in {
                    "geometry",
                    "start_lon", "start_lat",
                    "end_lon", "end_lat",
                    "lon", "lat",
                }
                and not pd.isna(value)
            }

            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": mapping(geom),
            })

        return normalize_collection(features)

    try:
        data = json.loads(uploaded_file.getvalue().decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Dosya geçerli UTF-8 JSON/GeoJSON değil.") from exc

    return normalize_collection(data)


# ============================================================
# 5. SIDEBAR VE DOSYA YÜKLEME
# ============================================================

if "custom_features" not in st.session_state:
    st.session_state["custom_features"] = None

with st.sidebar:
    st.markdown("## 🌍 Atlas kontrolü")
    st.caption(f"Bağımsız uygulama · v{APP_VERSION}")

    uploaded_file = st.file_uploader(
        "Veri dosyası yükle",
        type=["geojson", "json", "csv"],
        help=(
            "GeoJSON/JSON FeatureCollection veya CSV yükleyebilirsin. "
            "CSV için WKT geometry ya da lon/lat sütunları desteklenir."
        ),
    )

    if uploaded_file is not None:
        try:
            new_features = load_uploaded_file(uploaded_file)
            st.session_state["custom_features"] = new_features
            st.success(f"{len(new_features)} kayıt yüklendi.")
        except Exception as exc:
            st.error(f"Dosya yüklenemedi: {exc}")

    if st.button("↺ Varsayılan verilere dön", use_container_width=True):
        st.session_state["custom_features"] = None
        st.rerun()

    st.divider()
    st.markdown("### Görünüm")

    basemap = st.selectbox(
        "Taban harita",
        options=[
            "OpenStreetMap",
            "CartoDB dark_matter",
            "CartoDB positron",
        ],
        index=0,
        help="Uygulama varsayılan olarak OpenStreetMap ile açılır.",
    )

    show_labels = st.toggle("İsim etiketleri", value=True)
    show_minimap = st.toggle("Küçük genel bakış haritası", value=False)
    fit_bounds = st.toggle("Verileri haritaya sığdır", value=True)

    st.divider()
    st.markdown("### Filtreler")

all_features = (
    st.session_state["custom_features"]
    if st.session_state["custom_features"] is not None
    else normalize_collection(DEFAULT_FEATURES)
)

available_groups = sorted({
    str(f["properties"].get("group", "Sınıflandırılmamış"))
    for f in all_features
})

available_types = sorted({
    str(f["geometry"]["type"])
    for f in all_features
})

with st.sidebar:
    selected_groups = st.multiselect(
        "Grup",
        options=available_groups,
        default=available_groups,
    )

    selected_types = st.multiselect(
        "Geometri",
        options=available_types,
        default=available_types,
    )

    search_query = st.text_input(
        "Kayıt ara",
        placeholder="Örn. Khazar, Bulgar...",
    )


# ============================================================
# 6. FİLTRELEME
# ============================================================

visible_features = []

for feature in all_features:
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

    if search_query.strip().casefold() not in searchable:
        continue

    visible_features.append(feature)


# ============================================================
# 7. ÜST BANNER VE İSTATİSTİKLER
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">HISTORICAL GEOGRAPHY · INTERACTIVE ATLAS</div>
        <h1>🌍 {APP_TITLE}</h1>
        <p>
            Tarihî coğrafya kayıtlarını keşfet, güzergâhları karşılaştır,
            verileri filtrele ve dışa aktar.
        </p>
        <span class="hero-chip">● OpenStreetMap</span>
        <span class="hero-chip">● GeoJSON</span>
        <span class="hero-chip">● CSV</span>
        <span class="hero-chip">● Dark interface</span>
    </div>
    """,
    unsafe_allow_html=True,
)

point_count = 0
line_count = 0
area_count = 0

for feature in visible_features:
    geom_type = shape(feature["geometry"]).geom_type

    if geom_type in {"Point", "MultiPoint"}:
        point_count += 1
    elif geom_type in {"LineString", "MultiLineString"}:
        line_count += 1
    elif geom_type in {"Polygon", "MultiPolygon"}:
        area_count += 1

metric_data = [
    ("GÖSTERİLEN KAYIT", len(visible_features), "Aktif filtrelerden sonra"),
    ("NOKTA", point_count, "Konum kayıtları"),
    ("GÜZERGÂH", line_count, "Çizgi geometrileri"),
    ("ALAN", area_count, "Poligon geometrileri"),
]

cols = st.columns(4)

for col, (label, value, note) in zip(cols, metric_data):
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
# 8. HARİTA YARDIMCILARI
# ============================================================

def label_position(feature: dict[str, Any]) -> tuple[float, float]:
    geom = shape(feature["geometry"])
    props = feature["properties"]

    if geom.geom_type == "Point":
        point = geom
    elif geom.geom_type == "MultiPoint":
        point = list(geom.geoms)[0]
    elif geom.geom_type == "LineString":
        point = geom.interpolate(0.5, normalized=True)
    elif geom.geom_type == "MultiLineString":
        longest = max(geom.geoms, key=lambda part: part.length)
        point = longest.interpolate(0.5, normalized=True)
    else:
        point = geom.representative_point()

    lon = point.x + safe_number(props.get("label_dx"), 0.0)
    lat = point.y + safe_number(props.get("label_dy"), 0.0)

    return (
        max(-85.0, min(85.0, lat)),
        max(-180.0, min(180.0, lon)),
    )


def make_map(features: list[dict[str, Any]]) -> folium.Map:
    # İlk ve varsayılan katman OpenStreetMap'tir.
    map_object = folium.Map(
        location=[45.0, 45.0],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=True,
    )

    # Alternatif taban katmanları.
    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="Koyu harita",
        overlay=False,
        control=True,
    ).add_to(map_object)

    folium.TileLayer(
        tiles="CartoDB positron",
        name="Açık harita",
        overlay=False,
        control=True,
    ).add_to(map_object)

    # Kullanıcı seçimini varsayılan OSM katmanından sonra uygula.
    if basemap != "OpenStreetMap":
        map_object.options["layers"] = []

    # Katmanlar.
    route_layer = folium.FeatureGroup(
        name="Güzergâhlar",
        show=True,
    ).add_to(map_object)

    point_layer = folium.FeatureGroup(
        name="Konum noktaları",
        show=True,
    ).add_to(map_object)

    area_layer = folium.FeatureGroup(
        name="Alanlar",
        show=True,
    ).add_to(map_object)

    label_layer = folium.FeatureGroup(
        name="İsim etiketleri",
        show=show_labels,
    ).add_to(map_object)

    bounds = []
    legend_entries: dict[str, str] = {}

    for feature in features:
        props = feature["properties"]
        geom = shape(feature["geometry"])

        name_raw = str(props.get("name", "İsimsiz"))
        description_raw = str(props.get("description", ""))
        group_raw = str(props.get("group", ""))
        color = safe_color(props.get("color"))

        name = html.escape(name_raw)
        description = html.escape(description_raw)
        group = html.escape(group_raw)

        geom_type = geom.geom_type

        popup_html = f"""
        <div style="
            font-family:Arial,sans-serif;
            background:#111b2e;
            color:#e8eef8;
            padding:10px;
            min-width:190px;
            border-radius:8px;
        ">
            <div style="font-size:16px;font-weight:800;margin-bottom:8px">
                {name}
            </div>
            <div style="font-size:12px;margin-bottom:8px">
                {description}
            </div>
            <div style="font-size:11px;color:#a9bad0">
                Geometri: {html.escape(geom_type)}<br>
                Grup: {group}
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
            name=name_raw,
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=320),
            style_function=lambda _feature, c=color: {
                "color": c,
                "weight": 4,
                "opacity": 0.95,
                "fillColor": c,
                "fillOpacity": 0.22,
            },
            highlight_function=lambda _feature: {
                "weight": 6,
                "opacity": 1.0,
                "fillOpacity": 0.35,
            },
            marker=folium.CircleMarker(
                radius=7,
                color="#f8fafc",
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=1.0,
            ),
            zoom_on_click=True,
        ).add_to(target_layer)

        legend_entries[name] = color

        if show_labels:
            label_lat, label_lon = label_position(feature)
            label_text = html.escape(
                str(props.get("label") or props.get("name") or "")
            )

            folium.Marker(
                location=[label_lat, label_lon],
                interactive=False,
                icon=folium.DivIcon(
                    icon_size=(190, 28),
                    icon_anchor=(0, 12),
                    html=f"""
                    <div style="
                        display:inline-block;
                        white-space:nowrap;
                        padding:4px 8px;
                        border-radius:6px;
                        background:rgba(11,17,32,.94);
                        border:1px solid {color};
                        box-shadow:0 3px 10px rgba(0,0,0,.28);
                        color:#f1f5f9;
                        font-size:11px;
                        font-weight:800;
                        font-family:Arial,sans-serif;
                    ">{label_text}</div>
                    """,
                ),
            ).add_to(label_layer)

        minx, miny, maxx, maxy = geom.bounds
        bounds.append((minx, miny, maxx, maxy))

    # Tekilleştirilmiş harita lejandı.
    if legend_entries:
        legend_rows = "".join(
            f"""
            <div style="display:flex;align-items:center;gap:7px;margin:5px 0">
                <span style="
                    width:10px;height:10px;border-radius:50%;
                    display:inline-block;background:{color};
                    border:1px solid rgba(255,255,255,.5);
                "></span>
                <span>{label}</span>
            </div>
            """
            for label, color in legend_entries.items()
        )

        legend_html = f"""
        <div style="
            position:fixed;
            left:16px;
            bottom:28px;
            z-index:9999;
            max-width:210px;
            max-height:250px;
            overflow-y:auto;
            background:rgba(11,17,32,.95);
            color:#e8eef8;
            border:1px solid #334761;
            border-radius:10px;
            padding:10px 12px;
            font-family:Arial,sans-serif;
            font-size:11px;
            box-shadow:0 5px 20px rgba(0,0,0,.3);
        ">
            <div style="
                font-size:12px;font-weight:800;
                color:#7dd3fc;margin-bottom:8px;
            ">HARİTA LEJANDI</div>
            {legend_rows}
        </div>
        """

        map_object.get_root().html.add_child(folium.Element(legend_html))

    if fit_bounds and bounds:
        min_lon = min(item[0] for item in bounds)
        min_lat = min(item[1] for item in bounds)
        max_lon = max(item[2] for item in bounds)
        max_lat = max(item[3] for item in bounds)

        if min_lon == max_lon:
            min_lon -= 0.5
            max_lon += 0.5

        if min_lat == max_lat:
            min_lat -= 0.5
            max_lat += 0.5

        map_object.fit_bounds(
            [[min_lat, min_lon], [max_lat, max_lon]],
            padding=(35, 35),
        )

    if show_minimap:
        from folium.plugins import MiniMap
        MiniMap(
            tile_layer="OpenStreetMap",
            toggle_display=True,
            position="bottomright",
        ).add_to(map_object)

    from folium.plugins import Fullscreen, MousePosition

    Fullscreen(
        position="topleft",
        title="Tam ekran",
        title_cancel="Tam ekrandan çık",
        force_separate_button=True,
    ).add_to(map_object)

    MousePosition(
        position="bottomright",
        separator=" | ",
        prefix="Koordinat:",
        num_digits=4,
    ).add_to(map_object)

    folium.LayerControl(
        collapsed=False,
        position="topright",
    ).add_to(map_object)

    return map_object


# ============================================================
# 9. SEKME DÜZENİ
# ============================================================

tab_map, tab_data, tab_export, tab_about = st.tabs([
    "🗺️ Harita",
    "📋 Veri kayıtları",
    "⬇️ Dışa aktarma",
    "ⓘ Hakkında",
])


# ------------------------------------------------------------
# HARİTA
# ------------------------------------------------------------

with tab_map:
    st.markdown(
        '<div class="section-title">Coğrafi keşif alanı</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">'
        'Haritayı sürükle, yakınlaştır, katmanları değiştir ve kayıtların '
        'üzerine tıklayarak ayrıntılarını görüntüle.'
        '</div>',
        unsafe_allow_html=True,
    )

    if not visible_features:
        st.warning("Aktif filtrelerle eşleşen kayıt bulunamadı.")
    else:
        map_object = make_map(visible_features)

        st_folium(
            map_object,
            width=None,
            height=690,
            returned_objects=[],
            key="hazar_ogur_map",
        )

    st.caption(
        "Harita döşemeleri internet bağlantısı gerektirir. "
        "© OpenStreetMap contributors. Gösterilen güzergâhlar, "
        "girdi verilerindeki koordinatları temsil eder."
    )


# ------------------------------------------------------------
# VERİ TABLOSU
# ------------------------------------------------------------

with tab_data:
    st.markdown("### 📋 Veri kayıtları")
    st.caption(f"{len(visible_features)} kayıt gösteriliyor.")

    rows = []

    for feature in visible_features:
        props = feature["properties"]
        geom = shape(feature["geometry"])

        representative_point = geom.representative_point()

        rows.append({
            "Ad": props.get("name", ""),
            "Açıklama": props.get("description", ""),
            "Grup": props.get("group", ""),
            "Geometri": geom.geom_type,
            "Boylam": round(representative_point.x, 5),
            "Enlem": round(representative_point.y, 5),
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
        st.info("Gösterilecek kayıt bulunmuyor.")


# ------------------------------------------------------------
# DIŞA AKTARMA
# ------------------------------------------------------------

with tab_export:
    st.markdown("### ⬇️ Verileri dışa aktar")
    st.caption("Yalnızca mevcut filtrelerle eşleşen kayıtlar dışa aktarılır.")

    geojson_document = {
        "type": "FeatureCollection",
        "features": visible_features,
    }

    geojson_bytes = json.dumps(
        geojson_document,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    csv_rows = []

    for feature in visible_features:
        props = feature["properties"]
        geom = shape(feature["geometry"])

        csv_rows.append({
            "name": props.get("name", ""),
            "description": props.get("description", ""),
            "group": props.get("group", ""),
            "color": props.get("color", ""),
            "label": props.get("label", ""),
            "label_dx": props.get("label_dx", 0),
            "label_dy": props.get("label_dy", 0),
            "geometry": geom.wkt,
        })

    csv_buffer = io.StringIO()
    pd.DataFrame(csv_rows).to_csv(csv_buffer, index=False)

    left, right = st.columns(2)

    with left:
        st.markdown("#### GeoJSON")
        st.write("Geometri ve özellikler korunur.")
        st.download_button(
            "⬇️ GeoJSON indir",
            data=geojson_bytes,
            file_name="hazar_ogur_atlas.geojson",
            mime="application/geo+json",
            use_container_width=True,
            disabled=not visible_features,
        )

    with right:
        st.markdown("#### CSV")
        st.write("Tablo verilerini Excel veya başka araçlarda aç.")
        st.download_button(
            "⬇️ CSV indir",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="hazar_ogur_atlas.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=not visible_features,
        )

    st.info(
        "CSV dosyasındaki geometry alanı WKT biçimindedir. "
        "Bu uygulama CSV yüklerken WKT ve GeoJSON geometri metnini "
        "ve ayrıca start_lon/start_lat/end_lon/end_lat veya lon/lat "
        "koordinat sütunlarını destekler."
    )


# ------------------------------------------------------------
# HAKKINDA
# ------------------------------------------------------------

with tab_about:
    st.markdown("### ⓘ Hazar–Oğur Atlası hakkında")

    st.markdown(
        """
        Bu uygulama, coğrafi özellikleri etkileşimli harita üzerinde
        incelemek için hazırlanmış bağımsız bir Streamlit prototipidir.

        **Özellikler**
        - OpenStreetMap varsayılan taban haritası
        - İsteğe bağlı koyu ve açık alternatif haritalar
        - Nokta, çizgi ve poligon geometrileri
        - Renkli etiketler ve tekilleştirilmiş lejant
        - Arama, grup ve geometri filtreleri
        - GeoJSON, JSON ve CSV yükleme
        - CSV ve GeoJSON dışa aktarma

        **Bilimsel doğrulama notu**

        Haritadaki adlar, açıklamalar ve güzergâhlar örnek veri kümesinden
        gelir. Tarihî doğruluk, kaynakça, tarihlendirme ve koordinatların
        güvenilirliği ayrıca doğrulanmalıdır. Harita çizimi tek başına
        tarihî bir iddiayı kanıtlamaz.
        """
    )

    st.markdown(f"**Uygulama sürümü:** {APP_VERSION}")


# ============================================================
# 10. ALT BİLGİ
# ============================================================

st.markdown(
    """
    <div class="footer">
        <b>Hazar–Oğur Atlası</b> · Streamlit + Folium + Shapely
        <br>
        Harita verisi ve atıf: © OpenStreetMap contributors.
        <br>
        OpenStreetMap standart döşemeleri için kullanım politikalarına uyulmalıdır.
    </div>
    """,
    unsafe_allow_html=True,
)
