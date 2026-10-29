
from __future__ import annotations

import csv
import html
import io
import json
import math
import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from branca.element import Element
from shapely import wkt
from shapely.geometry import shape, mapping
from streamlit_folium import st_folium


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hazar–Oğur Tarihsel Coğrafya",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "modules" / "hazar_ogur.geojson"

DEFAULT_COLOR = "#64748b"


# ============================================================
# GÖMÜLÜ VARSAYILAN VERİ
# GeoJSON dosyası bulunamazsa uygulama yine açılır.
# ============================================================

DEFAULT_FEATURES = [
    {
        "type": "Feature",
        "properties": {
            "name": "1. Ujur / Uygur",
            "description": "Orkhon -> Jetisu",
            "color": "#2563eb",
            "label_dx": 1.5,
            "label_dy": 0.8,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[102, 47], [75, 45]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "2. Tauris",
            "description": "Kirim (yerel)",
            "color": "#059669",
            "label_dx": 0.9,
            "label_dy": -1.7,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [34, 45],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "3. Avar",
            "description": "Kafkasya -> Pannonia",
            "color": "#dc2626",
            "label_dx": 0.9,
            "label_dy": 0.6,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[47, 42], [19, 47]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "4. Uauz / Oguz",
            "description": "Aral/Hazar -> Anadolu",
            "color": "#d97706",
            "label_dx": 0.9,
            "label_dy": -1.5,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[60, 43], [35, 39]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "5. Bizal / Barsil",
            "description": "Volga-Don / K. Kafkasya",
            "color": "#7c3aed",
            "label_dx": 1.0,
            "label_dy": 1.2,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [42, 48],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "6. Tarna",
            "description": "Dagistan / Tarku",
            "color": "#db2777",
            "label_dx": 1.0,
            "label_dy": -1.4,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [47.5, 42.9],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "7. Khazar",
            "description": "Asagi Volga / Itil",
            "color": "#4f46e5",
            "label_dx": 1.6,
            "label_dy": 0.7,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [48, 46],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "8. Janur / Zagur",
            "description": "Azak / Kuban",
            "color": "#0891b2",
            "label_dx": -7.2,
            "label_dy": 0.9,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [39, 45.2],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "9. Bulgar",
            "description": "Kuban -> Volga",
            "color": "#ea580c",
            "label_dx": 1.0,
            "label_dy": 1.0,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[39, 46.8], [49, 55]],
        },
    },
    {
        "type": "Feature",
        "properties": {
            "name": "10. Sabir / Suvar",
            "description": "Bati Sibirya -> Kafkasya",
            "color": "#16a34a",
            "label_dx": 1.0,
            "label_dy": -1.4,
            "group": "Sınıflandırılmamış",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[75, 55], [47, 43]],
        },
    },
]


# ============================================================
# VERİ YÜKLEME VE NORMALİZASYON
# ============================================================

def safe_color(value):
    color = str(value or DEFAULT_COLOR).strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color
    return DEFAULT_COLOR


def safe_offset(value, default=0.0):
    try:
        number = float(html.unescape(str(value)).replace("*", "").strip())
        if math.isfinite(number):
            return max(-20.0, min(20.0, number))
    except (TypeError, ValueError):
        pass
    return default


def normalize_properties(properties):
    props = dict(properties or {})

    aliases = {
        "nombre": "name",
        "descripcion": "description",
        "descripción": "description",
        "grupo": "group",
        "categoria": "group",
        "tipo_geometria": "geometry_type",
    }

    for old, new in aliases.items():
        if new not in props and old in props:
            props[new] = props[old]

    props["name"] = str(props.get("name") or "İsimsiz kayıt")
    props["description"] = str(props.get("description") or "")
    props["group"] = str(props.get("group") or "Sınıflandırılmamış")
    props["color"] = safe_color(props.get("color"))
    props["label_dx"] = safe_offset(props.get("label_dx"), 0.5)
    props["label_dy"] = safe_offset(props.get("label_dy"), 0.5)

    return props


def normalize_feature(feature):
    if not isinstance(feature, dict):
        raise ValueError("Her kayıt bir GeoJSON Feature olmalıdır.")

    geometry = feature.get("geometry")
    if not geometry:
        raise ValueError("Bir kaydın geometry alanı eksik.")

    geom = shape(geometry)
    if geom.is_empty:
        raise ValueError("Boş geometri bulundu.")

    if geom.geom_type not in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError(f"Desteklenmeyen geometri: {geom.geom_type}")

    return {
        "type": "Feature",
        "properties": normalize_properties(feature.get("properties")),
        "geometry": mapping(geom),
    }


def normalize_collection(data):
    if data.get("type") == "Feature":
        features = [data]
    elif data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    else:
        raise ValueError("GeoJSON Feature veya FeatureCollection olmalıdır.")

    if not features:
        raise ValueError("Veri kümesinde kayıt bulunamadı.")

    return {
        "type": "FeatureCollection",
        "features": [normalize_feature(f) for f in features],
    }


def load_default_data():
    # Depodaki dosya varsa onu kullan; yoksa gömülü örnek veriye dön.
    if DATA_FILE.is_file():
        try:
            with DATA_FILE.open("r", encoding="utf-8-sig") as file:
                return normalize_collection(json.load(file))
        except Exception as exc:
            st.warning(
                f"Varsayılan GeoJSON okunamadı; gömülü örnek veri kullanılacak. "
                f"Ayrıntı: {exc}"
            )

    return normalize_collection({
        "type": "FeatureCollection",
        "features": DEFAULT_FEATURES,
    })


def load_uploaded_data(uploaded_file):
    raw = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        frame = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")

        # CSV başlıklarındaki HTML ve Markdown kalıntılarını düzelt.
        frame.columns = [
            html.unescape(str(col)).strip().lstrip("*").strip()
            for col in frame.columns
        ]

        rename = {}
        for col in frame.columns:
            lower = col.casefold()
            if lower == "nombre":
                rename[col] = "name"
            elif lower in {"descripcion", "descripción"}:
                rename[col] = "description"
            elif lower == "grupo":
                rename[col] = "group"
            elif lower in {"tipo_geometria", "tipo_geometría"}:
                rename[col] = "geometry_type"
        frame = frame.rename(columns=rename)

        if "geometry" not in frame.columns:
            raise ValueError(
                "CSV dosyasında WKT geometri içeren 'geometry' sütunu gerekli."
            )

        features = []
        for row_number, row in frame.iterrows():
            geometry_text = str(row["geometry"]).strip()
            if not geometry_text or geometry_text.lower() == "nan":
                raise ValueError(f"{row_number + 2}. satırın geometrisi boş.")

            geom = wkt.loads(geometry_text)
            properties = row.drop(labels=["geometry"]).to_dict()
            properties = {
                key: None if pd.isna(value) else value
                for key, value in properties.items()
            }

            features.append({
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geom),
            })

        return normalize_collection({
            "type": "FeatureCollection",
            "features": features,
        })

    data = json.loads(raw.decode("utf-8-sig"))
    return normalize_collection(data)


# ============================================================
# HARİTA
# ============================================================

def geometry_coordinates(geometry):
    """Bounds için koordinatları [lon, lat] çiftleri olarak döndürür."""
    geom = shape(geometry)
    result = []

    def visit(obj):
        if isinstance(obj, (list, tuple)):
            if (
                len(obj) >= 2
                and isinstance(obj[0], (int, float))
                and isinstance(obj[1], (int, float))
            ):
                result.append([float(obj[0]), float(obj[1])])
            else:
                for item in obj:
                    visit(item)

    visit(geom.__geo_interface__.get("coordinates", []))
    return result


def make_label(feature):
    props = feature["properties"]
    geom = shape(feature["geometry"])

    if geom.geom_type == "Point":
        lon, lat = geom.x, geom.y
    else:
        point = geom.interpolate(0.5, normalized=True) if geom.geom_type == "LineString" else geom.representative_point()
        lon, lat = point.x, point.y

    dx = props["label_dx"]
    dy = props["label_dy"]

    # Büyük ofsetler koordinat cinsindendir, piksel cinsinden değildir.
    return [lat + dy, lon + dx]


def create_map(features, tile_choice="CartoDB Positron"):
    tile_map = {
        "CartoDB Positron": "CartoDB positron",
        "OpenStreetMap": "OpenStreetMap",
        "Esri Uydu": "Esri.WorldImagery",
    }

    fmap = folium.Map(
        location=[45, 45],
        zoom_start=4,
        tiles=tile_map.get(tile_choice, "CartoDB positron"),
        control_scale=True,
    )

    all_coords = []
    legend_items = []

    for feature in features:
        props = feature["properties"]
        geometry = feature["geometry"]
        geom = shape(geometry)

        name = props["name"]
        description = props["description"]
        color = props["color"]

        all_coords.extend(geometry_coordinates(geometry))

        popup = folium.Popup(
            f"<b>{html.escape(name)}</b><br>"
            f"{html.escape(description)}<br>"
            f"<small>{html.escape(geom.geom_type)}</small>",
            max_width=350,
        )

        if geom.geom_type == "Point":
            lon, lat = geom.x, geom.y
            folium.CircleMarker(
                [lat, lon],
                radius=7,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=name,
                popup=popup,
            ).add_to(fmap)

        elif geom.geom_type == "MultiPoint":
            for point in geom.geoms:
                folium.CircleMarker(
                    [point.y, point.x],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    tooltip=name,
                    popup=popup,
                ).add_to(fmap)

        elif geom.geom_type == "LineString":
            latlon = [[lat, lon] for lon, lat in geom.coords]
            folium.PolyLine(
                latlon,
                color=color,
                weight=4,
                opacity=0.9,
                tooltip=name,
                popup=popup,
            ).add_to(fmap)

        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                folium.PolyLine(
                    [[lat, lon] for lon, lat in line.coords],
                    color=color,
                    weight=4,
                    opacity=0.9,
                    tooltip=name,
                    popup=popup,
                ).add_to(fmap)

        elif geom.geom_type in {"Polygon", "MultiPolygon"}:
            folium.GeoJson(
                feature,
                style_function=lambda _f, c=color: {
                    "color": c,
                    "weight": 2,
                    "fillColor": c,
                    "fillOpacity": 0.25,
                },
                tooltip=name,
                popup=popup,
            ).add_to(fmap)

        # Etiket
        label_latlon = make_label(feature)
        label_html = (
            '<div style="'
            f'color:{color};'
            'font-size:12px;'
            'font-weight:700;'
            'white-space:nowrap;'
            'text-shadow:1px 1px 2px white,'
            '-1px -1px 2px white;'
            '">'
            f'{html.escape(name)}'
            '</div>'
        )
        folium.Marker(
            label_latlon,
            icon=folium.DivIcon(html=label_html),
            interactive=False,
        ).add_to(fmap)

        legend_items.append(
            '<div style="display:flex;align-items:center;gap:8px;margin:6px 0;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};border:1px solid #555;border-radius:50%;'
            f'flex-shrink:0;"></span>'
            f'<span>{html.escape(name)}</span>'
            '</div>'
        )

    if all_coords:
        lons = [coord[0] for coord in all_coords]
        lats = [coord[1] for coord in all_coords]
        if min(lons) != max(lons) or min(lats) != max(lats):
            fmap.fit_bounds([
                [min(lats), min(lons)],
                [max(lats), max(lons)],
            ], padding=(30, 30))
        else:
            fmap.location = [lats[0], lons[0]]
            fmap.zoom_start = 6

    legend_html = f"""
    <div style="
        position:fixed;
        bottom:22px;
        left:22px;
        z-index:9999;
        background:rgba(255,255,255,.97);
        color:#222;
        padding:12px 14px;
        border:1px solid #aaa;
        border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,.25);
        max-height:40vh;
        max-width:300px;
        overflow-y:auto;
        font-size:12px;
    ">
      <div style="font-weight:bold;margin-bottom:8px;">
        Hazar–Oğur toplulukları
      </div>
      {''.join(legend_items)}
    </div>
    """
    fmap.get_root().html.add_child(Element(legend_html))

    return fmap


# ============================================================
# DIŞA AKTARMA
# ============================================================

def export_geojson(features):
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        ensure_ascii=False,
        indent=2,
    )


def export_csv(features):
    rows = []
    for feature in features:
        props = dict(feature["properties"])
        props["geometry"] = wkt.dumps(shape(feature["geometry"]))
        props["geometry_type"] = shape(feature["geometry"]).geom_type
        rows.append(props)

    if not rows:
        return ""

    return pd.DataFrame(rows).to_csv(index=False)


# ============================================================
# UYGULAMA ARAYÜZÜ
# ============================================================

st.title("🗺️ Hazar–Oğur Tarihsel-Coğrafi İnceleme")
st.caption(
    "Etkileşimli harita, geometrik kayıtlar, arama, filtreleme "
    "ve GeoJSON/CSV dışa aktarma."
)

if "features" not in st.session_state:
    st.session_state.features = load_default_data()["features"]

with st.sidebar:
    st.header("⚙️ Kontroller")

    tile_choice = st.selectbox(
        "Harita tabanı",
        ["CartoDB Positron", "OpenStreetMap", "Esri Uydu"],
    )

    uploaded_file = st.file_uploader(
        "GeoJSON, JSON veya CSV yükle",
        type=["geojson", "json", "csv"],
    )

    if st.button(
        "Yüklenen veriyi kullan",
        disabled=uploaded_file is None,
        use_container_width=True,
    ):
        try:
            st.session_state.features = load_uploaded_data(uploaded_file)["features"]
            st.success("Veri yüklendi.")
            st.rerun()
        except Exception as exc:
            st.error(f"Dosya yüklenemedi: {exc}")

    if st.button("Varsayılan verilere dön", use_container_width=True):
        st.session_state.features = load_default_data()["features"]
        st.rerun()

    st.divider()
    st.subheader("Filtreler")

    all_features = st.session_state.features
    groups = sorted({
        f["properties"]["group"] for f in all_features
    })
    selected_groups = st.multiselect(
        "Kategori",
        options=groups,
        default=groups,
    )

    search_text = st.text_input("Ad veya açıklama ara")
    geom_types = sorted({
        shape(f["geometry"]).geom_type for f in all_features
    })
    selected_types = st.multiselect(
        "Geometri türü",
        options=geom_types,
        default=geom_types,
    )

    show_table = st.checkbox("Veri tablosunu göster", value=True)

features = []
query = search_text.strip().casefold()

for feature in st.session_state.features:
    props = feature["properties"]
    geom_type = shape(feature["geometry"]).geom_type

    if selected_groups and props["group"] not in selected_groups:
        continue
    if selected_types and geom_type not in selected_types:
        continue
    if query:
        searchable = (
            props["name"] + " " +
            props["description"] + " " +
            props["group"]
        ).casefold()
        if query not in searchable:
            continue

    features.append(feature)

col1, col2, col3 = st.columns(3)
col1.metric("Toplam kayıt", len(st.session_state.features))
col2.metric("Filtrelenen kayıt", len(features))
col3.metric("Geometri türü", len({
    shape(f["geometry"]).geom_type for f in features
}))

tab_map, tab_data, tab_export = st.tabs([
    "🗺️ Harita",
    "📋 Veriler",
    "📥 Dışa aktar",
])

with tab_map:
    if not features:
        st.warning("Filtrelerle eşleşen kayıt yok.")
    else:
        try:
            fmap = create_map(features, tile_choice)
            st_folium(
                fmap,
                height=700,
                use_container_width=True,
                returned_objects=[],
                key="hazar_ogur_map",
            )
        except Exception as exc:
            st.error(f"Harita oluşturulamadı: {exc}")

with tab_data:
    if not features:
        st.info("Gösterilecek veri yok.")
    elif show_table:
        table_rows = []
        for feature in features:
            props = feature["properties"]
            geom = shape(feature["geometry"])
            table_rows.append({
                "Ad": props["name"],
                "Açıklama": props["description"],
                "Grup": props["group"],
                "Geometri": geom.geom_type,
                "Renk": props["color"],
                "label_dx": props["label_dx"],
                "label_dy": props["label_dy"],
            })
        st.dataframe(
            pd.DataFrame(table_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Kayıt ayrıntıları")
        for feature in features:
            props = feature["properties"]
            with st.expander(props["name"]):
                st.write(props["description"])
                st.json(props)
                st.caption(
                    "Geometri: " + shape(feature["geometry"]).geom_type
                )

with tab_export:
    if not features:
        st.info("Dışa aktarılacak kayıt yok.")
    else:
        st.download_button(
            "GeoJSON indir",
            data=export_geojson(features).encode("utf-8"),
            file_name="hazar_ogur.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )

        st.download_button(
            "CSV indir",
            data=export_csv(features).encode("utf-8-sig"),
            file_name="hazar_ogur.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()
st.caption(
    "Araştırma ve görselleştirme prototipi. "
    "Haritadaki çizgiler şematik güzergâh gösterimleridir."
)
