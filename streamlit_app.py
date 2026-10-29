from pathlib import Path

app_code = r'''from __future__ import annotations

import json
from typing import Any

import folium
import pandas as pd
import streamlit as st
from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry
from streamlit_folium import st_folium


# ============================================================
# HAZAR–OĞUR ATLASI | Tek dosyalı Streamlit uygulaması
# Başlangıç haritası: OpenStreetMap
# ============================================================

st.set_page_config(
    page_title="Hazar–Oğur Atlası",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Görsel tema ----------
st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp {
        background:
            radial-gradient(ellipse at 10% 0%, rgba(34, 72, 120, .22), transparent 35%),
            #0b1120;
        color: #e5e7eb;
    }
    [data-testid="stSidebar"] {
        background: #0e1728;
        border-right: 1px solid #243247;
    }
    .block-container { padding-top: 1.6rem; padding-bottom: 2rem; }
    .eyebrow {
        color: #7dd3fc; font-size: .78rem; font-weight: 800;
        letter-spacing: .18em; text-transform: uppercase;
    }
    .hero-title {
        font-size: clamp(2rem, 4vw, 3.2rem); font-weight: 850;
        line-height: 1.12; letter-spacing: -.04em; color: #f8fafc;
        margin: .35rem 0 .65rem;
    }
    .hero-subtitle { color: #a8b5c8; font-size: 1.04rem; max-width: 850px; }
    .chip-row { display:flex; gap:.55rem; flex-wrap:wrap; margin:1.05rem 0 1.2rem; }
    .chip {
        border:1px solid #334155; background:#111c2e; color:#cbd5e1;
        border-radius:999px; padding:.35rem .7rem; font-size:.78rem;
    }
    .metric-label {
        color:#93a4ba; font-size:.75rem; font-weight:800; letter-spacing:.12em;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #121e31, #0e1728);
        border: 1px solid #26364d; padding: 1rem 1.1rem;
        border-radius: 14px; min-height: 112px;
    }
    div[data-testid="stMetricLabel"] { color:#a8b5c8; }
    div[data-testid="stMetricValue"] { color:#f8fafc; }
    div[data-testid="stMetricDelta"] { color:#7dd3fc; }
    .section-title {
        font-size:1.08rem; font-weight:750; color:#eaf2ff;
        margin:.4rem 0 .7rem;
    }
    .small-muted { color:#94a3b8; font-size:.86rem; }
    .stButton > button, .stDownloadButton > button {
        border-radius:9px; border:1px solid #334155;
    }
    div[data-testid="stDataFrame"] {
        border:1px solid #26364d; border-radius:12px; overflow:hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Örnek veriler ----------
# Koordinatlar GeoJSON standardına göre [boylam, enlem] sırasındadır.
SAMPLE_FEATURES: list[dict[str, Any]] = [
    {
        "name": "Ujur / Uygur",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "LineString", "coordinates": [[102, 47], [75, 45]]},
        "color": "#2563eb",
        "description": "Orhun bölgesinden Jetisu yönüne uzanan örnek güzergâh.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Tauris",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "Point", "coordinates": [34, 45]},
        "color": "#059669",
        "description": "Kırım çevresinde gösterilen örnek konum.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Avar",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "LineString", "coordinates": [[47, 42], [19, 47]]},
        "color": "#dc2626",
        "description": "Kafkasya'dan Pannonia yönüne uzanan örnek güzergâh.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Uauz / Oğuz",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "LineString", "coordinates": [[60, 43], [35, 39]]},
        "color": "#d97706",
        "description": "Aral-Hazar çevresinden Anadolu yönüne uzanan örnek güzergâh.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Bizal / Barsil",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "Point", "coordinates": [42, 48]},
        "color": "#7c3aed",
        "description": "Örnek konum kaydı.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Tarna",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "Point", "coordinates": [47.5, 42.9]},
        "color": "#db2777",
        "description": "Örnek konum kaydı.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Khazar / Hazar",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "Point", "coordinates": [48, 46]},
        "color": "#4f46e5",
        "description": "Hazar çevresinde gösterilen örnek konum.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Janur / Zagur",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "Point", "coordinates": [39, 45.2]},
        "color": "#0891b2",
        "description": "Örnek konum kaydı.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Bulgar",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "LineString", "coordinates": [[39, 46.8], [49, 55]]},
        "color": "#ea580c",
        "description": "Kuzeydoğu yönüne uzanan örnek güzergâh.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
    {
        "name": "Sabir / Suvar",
        "group": "Sınıflandırılmamış",
        "geometry": {"type": "LineString", "coordinates": [[75, 55], [47, 43]]},
        "color": "#16a34a",
        "description": "Batı yönüne uzanan örnek güzergâh.",
        "period": "Belirtilmemiş",
        "source": "Örnek veri",
    },
]


def geometry_from_geojson(value: Any) -> BaseGeometry:
    """GeoJSON geometry nesnesini doğrula ve Shapely geometrisine çevir."""
    if not isinstance(value, dict) or not value.get("type"):
        raise ValueError("Geometri alanı geçerli bir GeoJSON geometry nesnesi olmalıdır.")
    geom = shape(value)
    if geom.is_empty:
        raise ValueError("Boş geometri kabul edilmiyor.")
    if not geom.is_valid:
        raise ValueError("Geometri geçersiz; GeoJSON koordinatlarını kontrol edin.")
    if geom.geom_type not in {
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection",
    }:
        raise ValueError(f"Desteklenmeyen geometri tipi: {geom.geom_type}")
    return geom


def normalize_record(
    name: Any,
    group: Any,
    geometry: Any,
    color: Any = "#38bdf8",
    description: Any = "",
    period: Any = "Belirtilmemiş",
    source: Any = "Yüklenen dosya",
) -> dict[str, Any]:
    """Kayıt alanlarını normalize eder ve geometriyi doğrular."""
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Her kaydın name/ad alanı dolu olmalıdır.")
    geom = geometry_from_geojson(geometry)
    clean_color = str(color or "#38bdf8").strip()
    if not (clean_color.startswith("#") and len(clean_color) in (4, 7)):
        clean_color = "#38bdf8"
    return {
        "name": clean_name,
        "group": str(group or "Sınıflandırılmamış").strip() or "Sınıflandırılmamış",
        "geometry": geom,
        "color": clean_color,
        "description": str(description or ""),
        "period": str(period or "Belirtilmemiş"),
        "source": str(source or "Yüklenen dosya"),
    }


def load_geojson_records(data: Any, source_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """FeatureCollection veya tek Feature içeren GeoJSON/JSON yükle."""
    if not isinstance(data, dict):
        raise ValueError("JSON kök nesnesi bir nesne olmalıdır.")

    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif data.get("type") == "Feature":
        features = [data]
    elif data.get("type") in {
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection",
    }:
        features = [{"type": "Feature", "properties": {}, "geometry": data}]
    elif isinstance(data.get("records"), list):
        features = data["records"]
    else:
        raise ValueError(
            "JSON biçimi tanınmadı. FeatureCollection, Feature veya records listesi kullanın."
        )

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, feature in enumerate(features, start=1):
        try:
            if not isinstance(feature, dict):
                raise ValueError("Kayıt nesne biçiminde değil.")
            props = feature.get("properties") or feature
            geom = feature.get("geometry", props.get("geometry"))
            record = normalize_record(
                name=props.get("name", props.get("ad", f"Kayıt {index}")),
                group=props.get("group", props.get("grup", "Sınıflandırılmamış")),
                geometry=geom,
                color=props.get("color", "#38bdf8"),
                description=props.get("description", props.get("aciklama", "")),
                period=props.get("period", props.get("donem", "Belirtilmemiş")),
                source=props.get("source", source_name),
            )
            records.append(record)
        except Exception as exc:
            errors.append(f"Kayıt {index}: {exc}")
    return records, errors


def load_csv_records(file_bytes: bytes, source_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    """CSV dosyasını oku. geometry sütunu GeoJSON geometry JSON'u içermelidir."""
    import io

    df = pd.read_csv(io.BytesIO(file_bytes))
    # Sütun isimlerini esnek eşleştir.
    columns = {str(c).strip().lower(): c for c in df.columns}
    geom_col = columns.get("geometry") or columns.get("geometri")
    name_col = columns.get("name") or columns.get("ad") or columns.get("title")
    if geom_col is None or name_col is None:
        raise ValueError("CSV en az 'name' ve 'geometry' sütunlarını içermelidir.")

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, row in df.iterrows():
        try:
            raw_geom = row[geom_col]
            if pd.isna(raw_geom):
                raise ValueError("geometry boş.")
            geom_dict = json.loads(str(raw_geom))
            record = normalize_record(
                name=row[name_col],
                group=row[columns.get("group") or columns.get("grup")] if (
                    columns.get("group") or columns.get("grup")
                ) else "Sınıflandırılmamış",
                geometry=geom_dict,
                color=row[columns.get("color")] if columns.get("color") else "#38bdf8",
                description=row[columns.get("description") or columns.get("aciklama")] if (
                    columns.get("description") or columns.get("aciklama")
                ) else "",
                period=row[columns.get("period") or columns.get("donem")] if (
                    columns.get("period") or columns.get("donem")
                ) else "Belirtilmemiş",
                source=source_name,
            )
            records.append(record)
        except Exception as exc:
            errors.append(f"Satır {index + 2}: {exc}")
    return records, errors


def record_to_geojson_feature(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "name": record["name"],
            "group": record["group"],
            "color": record["color"],
            "description": record["description"],
            "period": record["period"],
            "source": record["source"],
        },
        "geometry": mapping(record["geometry"]),
    }


def build_map(records: list[dict[str, Any]], basemap: str = "OpenStreetMap") -> folium.Map:
    """Folium haritası. İlk katman daima OpenStreetMap olarak oluşturulur."""
    # OSM gerçekten başlangıç katmanıdır; alternatifler kontrol panelinden seçilebilir.
    map_object = folium.Map(
        location=[45.0, 45.0],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
        zoom_control=True,
    )

    if basemap != "OpenStreetMap":
        # Kullanıcı alternatif seçerse onu ekleyip görünür katman seçimini kontrol paneline bırak.
        if basemap == "CartoDB Dark":
            folium.TileLayer(
                tiles="CartoDB dark_matter",
                name="CartoDB Dark",
                overlay=False,
                control=True,
            ).add_to(map_object)
        elif basemap == "CartoDB Light":
            folium.TileLayer(
                tiles="CartoDB positron",
                name="CartoDB Light",
                overlay=False,
                control=True,
            ).add_to(map_object)

    for record in records:
        geom = record["geometry"]
        color = record["color"]
        name = record["name"]
        popup_html = (
            "<div style='min-width:190px;font-family:Arial,sans-serif'>"
            f"<h4 style='margin:0 0 6px;color:#0f172a'>{name}</h4>"
            f"<div><b>Grup:</b> {record['group']}</div>"
            f"<div><b>Geometri:</b> {geom.geom_type}</div>"
            f"<div><b>Dönem:</b> {record['period']}</div>"
            f"<p style='margin:7px 0 0'>{record['description']}</p>"
            f"<small>Kaynak: {record['source']}</small>"
            "</div>"
        )

        if geom.geom_type == "Point":
            lon, lat = geom.x, geom.y
            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=name,
                popup=folium.Popup(popup_html, max_width=320),
            ).add_to(map_object)
        else:
            folium.GeoJson(
                data=mapping(geom),
                name=name,
                style_function=lambda _feature, c=color: {
                    "color": c,
                    "weight": 4,
                    "opacity": 0.9,
                    "fillColor": c,
                    "fillOpacity": 0.18,
                },
                tooltip=folium.Tooltip(name),
                popup=folium.Popup(popup_html, max_width=320),
            ).add_to(map_object)

    folium.LayerControl(collapsed=True).add_to(map_object)

    # Harita görünümünü kayıtların sınırlarına göre ayarla.
    if records:
        bounds = [r["geometry"].bounds for r in records if not r["geometry"].is_empty]
        if bounds:
            minx = min(b[0] for b in bounds)
            miny = min(b[1] for b in bounds)
            maxx = max(b[2] for b in bounds)
            maxy = max(b[3] for b in bounds)
            if minx != maxx or miny != maxy:
                map_object.fit_bounds([[miny, minx], [maxy, maxx]], padding=(24, 24))

    return map_object


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        geom = record["geometry"]
        centroid = geom.centroid
        rows.append(
            {
                "Ad": record["name"],
                "Grup": record["group"],
                "Geometri": geom.geom_type,
                "Boylam (merkez)": round(centroid.x, 6),
                "Enlem (merkez)": round(centroid.y, 6),
                "Dönem": record["period"],
                "Açıklama": record["description"],
                "Kaynak": record["source"],
                "GeoJSON geometri": json.dumps(mapping(geom), ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


# ---------- Oturum durumu ----------
if "atlas_records" not in st.session_state:
    st.session_state.atlas_records = [
        normalize_record(
            item["name"], item["group"], item["geometry"], item["color"],
            item["description"], item["period"], item["source"]
        )
        for item in SAMPLE_FEATURES
    ]
if "load_messages" not in st.session_state:
    st.session_state.load_messages = []


# ---------- Başlık ----------
st.markdown('<div class="eyebrow">HISTORICAL GEOGRAPHY · INTERACTIVE ATLAS</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">🌍 Hazar–Oğur Atlası</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Tarihî coğrafya kayıtlarını keşfet, güzergâhları karşılaştır, '
    'verileri filtrele ve dışa aktar.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="chip-row">'
    '<span class="chip">● OpenStreetMap</span>'
    '<span class="chip">● GeoJSON</span>'
    '<span class="chip">● CSV</span>'
    '<span class="chip">● Dark interface</span>'
    '</div>',
    unsafe_allow_html=True,
)


# ---------- Kenar çubuğu: veri ve filtreler ----------
all_records = st.session_state.atlas_records
all_groups = sorted({r["group"] for r in all_records})
all_geom_types = sorted({r["geometry"].geom_type for r in all_records})

with st.sidebar:
    st.markdown("## 🧭 Atlas kontrolü")
    st.caption("Veriyi yükle, ara ve harita katmanlarını filtrele.")

    upload = st.file_uploader(
        "Veri dosyası yükle",
        type=["geojson", "json", "csv"],
        help="GeoJSON FeatureCollection/Feature veya name + geometry sütunlu CSV.",
    )
    import_mode = st.radio(
        "Yükleme yöntemi",
        ["Mevcut kayıtlara ekle", "Kayıtların yerine koy"],
        index=0,
    )
    if st.button("Dosyayı içe aktar", use_container_width=True, disabled=upload is None):
        try:
            raw_bytes = upload.getvalue()
            if upload.name.lower().endswith(".csv"):
                loaded, errors = load_csv_records(raw_bytes, upload.name)
            else:
                parsed = json.loads(raw_bytes.decode("utf-8-sig"))
                loaded, errors = load_geojson_records(parsed, upload.name)

            if not loaded:
                st.error("Geçerli kayıt bulunamadı.")
            else:
                if import_mode == "Kayıtların yerine koy":
                    st.session_state.atlas_records = loaded
                else:
                    st.session_state.atlas_records = st.session_state.atlas_records + loaded
                st.success(f"{len(loaded)} kayıt içe aktarıldı.")
            if errors:
                with st.expander(f"{len(errors)} kayıt atlandı — ayrıntılar"):
                    for message in errors[:100]:
                        st.warning(message)
                    if len(errors) > 100:
                        st.caption(f"İlk 100 hata gösterildi; toplam {len(errors)} hata.")
            st.rerun()
        except Exception as exc:
            st.error(f"Dosya okunamadı: {exc}")

    st.divider()
    st.markdown("### Filtreler")
    search_text = st.text_input("Kayıt ara", placeholder="Örn. Hazar, Avar, Oğuz")
    selected_groups = st.multiselect("Grup", options=all_groups, default=all_groups)
    selected_geometries = st.multiselect(
        "Geometri türü",
        options=all_geom_types,
        default=all_geom_types,
    )
    st.divider()
    basemap = st.selectbox(
        "Harita katmanı",
        ["OpenStreetMap", "CartoDB Dark", "CartoDB Light"],
        index=0,
        help="İlk açılışta OpenStreetMap seçilidir.",
    )
    show_labels = st.checkbox("Harita etiketlerini göster", value=True)
    st.caption("Not: Haritadaki tarihî güzergâhlar örnek/temsili kayıtlardır; akademik kaynak doğrulaması ayrıca yapılmalıdır.")
    if st.button("Örnek verilere dön", use_container_width=True):
        st.session_state.atlas_records = [
            normalize_record(
                item["name"], item["group"], item["geometry"], item["color"],
                item["description"], item["period"], item["source"]
            )
            for item in SAMPLE_FEATURES
        ]
        st.rerun()


# ---------- Filtreleme ----------
filtered_records = []
needle = search_text.strip().casefold()
for record in st.session_state.atlas_records:
    if record["group"] not in selected_groups:
        continue
    if record["geometry"].geom_type not in selected_geometries:
        continue
    haystack = " ".join(
        [record["name"], record["group"], record["description"], record["period"], record["source"]]
    ).casefold()
    if needle and needle not in haystack:
        continue
    filtered_records.append(record)

shown_count = len(filtered_records)
point_count = sum(
    record["geometry"].geom_type in ("Point", "MultiPoint")
    for record in filtered_records
)
route_count = sum(
    record["geometry"].geom_type in ("LineString", "MultiLineString")
    for record in filtered_records
)
area_count = sum(
    record["geometry"].geom_type in ("Polygon", "MultiPolygon")
    for record in filtered_records
)

m1, m2, m3 = st.columns(3)
m1.metric("GÖSTERİLEN KAYIT", shown_count, help="Aktif filtrelerden sonra kalan kayıt sayısı.")
m2.metric("NOKTA", point_count, help="Point ve MultiPoint geometri kayıtları.")
m3.metric("GÜZERGÂH", route_count, help="LineString ve MultiLineString geometri kayıtları.")

if area_count:
    st.caption(f"Ek olarak {area_count} alan/poligon kaydı gösteriliyor.")
if not filtered_records:
    st.info("Aktif filtrelerle eşleşen kayıt yok. Kenar çubuğundaki filtreleri değiştirin veya temizleyin.")


# ---------- Sekmeler ----------
tab_map, tab_data, tab_export, tab_about = st.tabs(
    ["🗺️ Etkileşimli harita", "📋 Veri tablosu", "⇩ Dışa aktar", "ⓘ Hakkında"]
)

with tab_map:
    left, right = st.columns([4, 1])
    with left:
        st.markdown('<div class="section-title">Tarihî coğrafya görünümü</div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            f'<div class="small-muted" style="text-align:right;padding-top:.45rem">'
            f'{shown_count} kayıt görünür</div>',
            unsafe_allow_html=True,
        )

    if filtered_records:
        atlas_map = build_map(filtered_records, basemap)
        map_data = st_folium(
            atlas_map,
            height=610,
            use_container_width=True,
            returned_objects=["last_object_clicked", "bounds"],
            key="hazar_ogur_atlas_map",
        )
        if map_data and map_data.get("last_object_clicked"):
            clicked = map_data["last_object_clicked"]
            if isinstance(clicked, dict) and clicked.get("lat") is not None:
                st.caption(
                    f"Son tıklanan koordinat: enlem {clicked.get('lat'):.5f}, "
                    f"boylam {clicked.get('lng', 0):.5f}"
                )
    else:
        st.markdown(
            '<div style="height:250px;border:1px dashed #334155;border-radius:14px;'
            'display:flex;align-items:center;justify-content:center;color:#94a3b8">'
            'Gösterilecek kayıt yok.</div>',
            unsafe_allow_html=True,
        )
    st.caption("Harita ilk açılışta OpenStreetMap kullanır. İnternet bağlantısı gerekir.")

with tab_data:
    st.markdown('<div class="section-title">Filtrelenmiş kayıtlar</div>', unsafe_allow_html=True)
    if filtered_records:
        table_df = records_to_dataframe(filtered_records).drop(columns=["GeoJSON geometri"])
        st.dataframe(table_df, use_container_width=True, hide_index=True)
    else:
        st.info("Tabloda gösterilecek kayıt yok.")

with tab_export:
    st.markdown('<div class="section-title">Filtrelenmiş veriyi dışa aktar</div>', unsafe_allow_html=True)
    st.write("Aşağıdaki indirmeler yalnızca aktif filtrelerden geçen kayıtları içerir.")
    if filtered_records:
        export_df = records_to_dataframe(filtered_records)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
        features = [record_to_geojson_feature(r) for r in filtered_records]
        geojson_obj = {
            "type": "FeatureCollection",
            "name": "Hazar-Ogur-Atlas",
            "features": features,
        }
        geojson_bytes = json.dumps(
            geojson_obj, ensure_ascii=False, indent=2
        ).encode("utf-8")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇ CSV indir",
                data=csv_bytes,
                file_name="hazar_ogur_atlas.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇ GeoJSON indir",
                data=geojson_bytes,
                file_name="hazar_ogur_atlas.geojson",
                mime="application/geo+json",
                use_container_width=True,
            )
        st.caption(f"Hazır: {len(filtered_records)} kayıt.")
    else:
        st.info("Dışa aktarılacak kayıt yok.")

with tab_about:
    st.markdown('<div class="section-title">Proje hakkında</div>', unsafe_allow_html=True)
    st.write(
        "Hazar–Oğur Atlası; tarihî coğrafya kayıtlarını harita üzerinde incelemek, "
        "geometri türlerine göre filtrelemek ve verileri standart biçimlerde dışa aktarmak "
        "için hazırlanmış bir Streamlit arayüzüdür."
    )
    st.markdown("**Desteklenen biçimler**")
    st.markdown("- GeoJSON: `FeatureCollection`, `Feature` veya tek geometri\n- JSON: GeoJSON yapısı ya da `records` listesi\n- CSV: `name` ve JSON biçiminde `geometry` sütunları")
    st.warning(
        "Uygulamayla birlikte gelen 10 kayıt örnek amaçlıdır. Tarihî güzergâhların "
        "kesinliği veya akademik geçerliliği doğrulanmış kabul edilmemelidir."
    )
    st.markdown("**Geometri sayımı**")
    st.write(
        "Nokta sayacı Point/MultiPoint kayıtlarını; güzergâh sayacı LineString/"
        "MultiLineString kayıtlarını sayar. Poligonlar bu iki sayaca dahil edilmez."
    )

st.markdown("---")
st.markdown(
    '<div class="small-muted">Hazar–Oğur Atlası · Streamlit + Folium + OpenStreetMap</div>',
    unsafe_allow_html=True,
)
'''
requirements = """streamlit>=1.36
pandas>=2.0
folium>=0.16
streamlit-folium>=0.22
shapely>=2.0
"""
Path("/mnt/data/app.py").write_text(app_code, encoding="utf-8")
Path("/mnt/data/requirements.txt").write_text(requirements, encoding="utf-8")
print("Created /mnt/data/app.py")
print("Created /mnt/data/requirements.txt")
