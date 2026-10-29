from pathlib import Path
import textwrap, zipfile, os

root = Path("/mnt/data/hazar_ogur_streamlit")
(root / "modules").mkdir(parents=True, exist_ok=True)
(root / "tests").mkdir(parents=True, exist_ok=True)

files = {
"app.py": r'''
from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium

from modules.data_loader import (
    load_default_data,
    validate_and_load_uploaded_file,
    export_geojson,
    export_csv,
)
from modules.history_data import HISTORICAL_NOTES
from modules.map_builder import create_map

st.set_page_config(
    page_title="Hazar ve Ogur — Tarihsel Coğrafya",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Hazar ve Ogur: Tarihsel-Coğrafi İnceleme")
st.caption(
    "Folium + GeoPandas + Shapely | Varsayılan koordinat sistemi: EPSG:4326"
)

st.warning(
    "Yöntem notu: Varsayılan çizgiler ve noktalar şematik görselleştirmelerdir. "
    "Kaynaklarla doğrulanmış tarihsel göç güzergâhları olarak değerlendirilmemelidir. "
    "Bir çizginin haritada gösterilmesi, güzergâhın tarihsel kanıtı değildir."
)

if "gdf" not in st.session_state:
    st.session_state.gdf = load_default_data()

with st.sidebar:
    st.header("⚙️ Harita ve veri ayarları")
    tile_choice = st.selectbox(
        "Altlık harita",
        ["CartoDB Positron", "OpenStreetMap", "Altlık harita yok"],
        index=0,
    )
    show_lines = st.checkbox("Güzergâh çizgileri", value=True)
    show_points = st.checkbox("Başlangıç/bitiş noktaları", value=True)
    show_labels = st.checkbox("Etiketler", value=True)
    st.divider()
    st.subheader("📤 Kendi verinizi yükleyin")
    uploaded_file = st.file_uploader(
        "GeoJSON, JSON veya CSV",
        type=["geojson", "json", "csv"],
        help=(
            "GeoJSON geometrileri veya koordinat sütunları içeren CSV yükleyin. "
            "CSV için gerekli alanlar aşağıdaki README'de açıklanmıştır."
        ),
    )
    if uploaded_file is not None:
        # Aynı dosya yeniden rerun olduğunda sürekli yüklememek için imza.
        signature = (uploaded_file.name, uploaded_file.size)
        if st.session_state.get("uploaded_signature") != signature:
            new_gdf, message = validate_and_load_uploaded_file(uploaded_file)
            if new_gdf is not None:
                st.session_state.gdf = new_gdf
                st.session_state.uploaded_signature = signature
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)
    if st.button("Varsayılan örnek veriye dön", use_container_width=True):
        st.session_state.gdf = load_default_data()
        st.session_state.pop("uploaded_signature", None)
        st.rerun()

base_gdf = st.session_state.gdf.copy()

left, right = st.sidebar.columns(2)
query = st.sidebar.text_input("Ada göre ara", "")
geom_options = sorted(base_gdf["tipo_geometria"].dropna().unique().tolist()) if not base_gdf.empty else []
selected_geoms = st.sidebar.multiselect(
    "Geometri türü", options=geom_options, default=geom_options
)

filtered_gdf = base_gdf
if query:
    filtered_gdf = filtered_gdf[
        filtered_gdf["nombre"].astype(str).str.contains(query, case=False, na=False)
    ]
if selected_geoms:
    filtered_gdf = filtered_gdf[filtered_gdf["tipo_geometria"].isin(selected_geoms)]
else:
    filtered_gdf = filtered_gdf.iloc[0:0].copy()

tab_map, tab_notes, tab_data = st.tabs(
    ["🗺️ Etkileşimli harita", "📚 Tarihsel notlar ve kaynaklar", "📥 Veri ve dışa aktarma"]
)

with tab_map:
    st.caption("Haritayı yakınlaştırın; bir işaret veya çizgiye tıklayarak öznitelikleri görün.")
    if filtered_gdf.empty:
        st.info("Filtrelere uyan kayıt yok. Sol panelde filtreleri değiştirin.")
    else:
        map_obj = create_map(
            filtered_gdf,
            selected_tile=tile_choice,
            show_lines=show_lines,
            show_points=show_points,
            show_labels=show_labels,
        )
        st_folium(map_obj, width=None, height=600, returned_objects=[])

    m1, m2, m3 = st.columns(3)
    m1.metric("Filtrelenen kayıt", len(filtered_gdf))
    m2.metric(
        "Çizgi",
        int((filtered_gdf["tipo_geometria"] == "LineString").sum()) if not filtered_gdf.empty else 0,
    )
    m3.metric(
        "Nokta",
        int((filtered_gdf["tipo_geometria"] == "Point").sum()) if not filtered_gdf.empty else 0,
    )

with tab_notes:
    st.header("Tarihsel yorum ve kaynak kullanımı")
    st.info(
        "Bu bölüm, doğrulanmış güzergâh kataloğu değil; adlandırma, kronoloji ve "
        "kaynak eleştirisi için başlangıç notlarıdır. Her iddia, özgün kaynak ve "
        "modern literatür üzerinden ayrıca kontrol edilmelidir."
    )
    for group, info in HISTORICAL_NOTES.items():
        with st.expander(group):
            st.markdown(f"**Kapsam:** {info['context']}")
            st.markdown(f"**Etimoloji / adlandırma:** {info['etymology']}")
            st.markdown(f"**Kanıt durumu:** {info['evidence_status']}")
            st.markdown("**Araştırma kaynakları ve kontrol noktaları:**")
            for source in info["sources"]:
                st.markdown(f"- {source}")

with tab_data:
    st.header("Kayıt tablosu ve dışa aktarma")
    st.write(f"Filtrelenmiş kayıt sayısı: **{len(filtered_gdf)}**")
    if not filtered_gdf.empty:
        display_df = filtered_gdf.drop(columns="geometry", errors="ignore")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(filtered_gdf.drop(columns="geometry", errors="ignore"), use_container_width=True)

    c1, c2 = st.columns(2)
    c1.download_button(
        "📄 GeoJSON indir",
        data=export_geojson(filtered_gdf),
        file_name="hazar_ogur_filtrelenmis.geojson",
        mime="application/geo+json",
        use_container_width=True,
    )
    c2.download_button(
        "📊 CSV indir (WKT geometriyle)",
        data=export_csv(filtered_gdf),
        file_name="hazar_ogur_filtrelenmis.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption(
        "GeoJSON geometrileri korur. CSV dışa aktarımında geometri geometry_wkt "
        "sütununda WKT biçiminde saklanır."
    )
''',
"modules/__init__.py": "",
"modules/history_data.py": r'''
"""Araştırma başlangıç notları; güzergâh kanıtı veya kesin etimoloji değildir."""

HISTORICAL_NOTES = {
    "Hazar (Khazar)": {
        "context": (
            "Hazarlar, özellikle erken ve orta Orta Çağ Avrasya'sının kuzey Karadeniz, "
            "Kafkasya ve aşağı Volga çevresindeki siyasi tarihi bağlamında incelenir. "
            "Bu uygulamadaki tekil koordinat, tarihsel alanın sınırını temsil etmez."
        ),
        "etymology": (
            "Adın kökeni ve farklı dillerdeki biçimleri için tarihsel dilbilim "
            "literatürü ve birincil kaynaklardaki yazımlar karşılaştırılmalıdır."
        ),
        "evidence_status": (
            "Bağlam notu. Haritadaki nokta şematiktir; kesin merkez, sınır veya "
            "hareket rotası iddiası değildir."
        ),
        "sources": [
            "Golden, Peter B. (1992), An Introduction to the History of the Turkic Peoples. "
            "Wiesbaden: Harrassowitz. Genel tarihsel bağlam için araştırma başlangıcı; "
            "tek başına bu haritadaki çizgileri doğrulamaz.",
            "Birincil kaynaklarda geçen ad biçimleri, tarih, yazım varyantı ve pasaj "
            "numarasıyla ayrı bir kaynak kaydına eklenmelidir.",
        ],
    },
    "Ogur / Bulgar": {
        "context": (
            "Ogur/Oğur ve Bulgar adları, erken Orta Çağ bozkır tarihi ve Türk dillerinin "
            "tarihî çeşitlenmesi tartışmalarında ele alınır. Terimler farklı kaynaklarda "
            "ve dönemlerde aynı kapsamı göstermeyebilir."
        ),
        "etymology": (
            "Adların etimolojisi ve gruplar arasındaki ilişki, yalnızca benzer yazımlara "
            "dayandırılmamalı; dilsel, kronolojik ve tarihsel bağlam birlikte incelenmelidir."
        ),
        "evidence_status": (
            "Sınıflandırma ve adlandırma araştırma konusudur. Haritadaki oklar "
            "kanıtlanmış toplu göçleri temsil etmez."
        ),
        "sources": [
            "Golden, Peter B. (1992), An Introduction to the History of the Turkic Peoples. "
            "Wiesbaden: Harrassowitz. Genel çerçeve için başlangıç kaynağı.",
            "Birincil kronikler ve modern araştırmalar, her ayrı iddia için sayfa/pasaj "
            "ve tarih bilgisiyle doğrulanmalıdır.",
        ],
    },
    "Uygur / Ujur": {
        "context": (
            "Uygur adı farklı tarihsel dönemler ve siyasi oluşumlar için kullanılmıştır. "
            "Bu uygulamadaki çizgi, tek bir tarihsel hareketi kanıtlamaz."
        ),
        "etymology": (
            "Ujur/Uygur biçimlerinin eşitlenmesi, yazım varyantları ve kaynak bağlamı "
            "incelenmeden kesin kabul edilmemelidir."
        ),
        "evidence_status": (
            "Şematik örnek kayıt. Başlangıç/bitiş koordinatları kaynaklandırılmış "
            "tarihsel veri değildir."
        ),
        "sources": [
            "Golden, Peter B. (1992), An Introduction to the History of the Turkic Peoples. "
            "Wiesbaden: Harrassowitz. Genel tarihsel bağlam için.",
            "Ad biçimlerini doğrulamak için tarihli birincil metin ve uzman sözlük "
            "kaydı ayrıca eklenmelidir.",
        ],
    },
    "Avar": {
        "context": (
            "Avar adı farklı tarihsel bağlamlarda kullanılmış olabilir; kronoloji ve "
            "kaynağın kullandığı adlandırma belirleyicidir."
        ),
        "etymology": "Adın kökeni ve farklı Avar topluluklarıyla ilişkilendirilmesi tartışmalı olabilir.",
        "evidence_status": (
            "Kafkasya–Pannonia çizgisi yalnızca görsel şemadır; güzergâh ve zaman "
            "dizisini kanıtlayan veri olarak kullanılmamalıdır."
        ),
        "sources": [
            "Golden, Peter B. (1992), An Introduction to the History of the Turkic Peoples. "
            "Genel Avrasya tarihi için başvuru noktası; belirli rota için doğrudan kanıt değildir.",
        ],
    },
    "Sabir / Suvar": {
        "context": (
            "Sabir ve Suvar adlarının tarihsel kaynaklarda kullanımı, kronoloji ve "
            "ad eşleştirmeleri bakımından ayrıca değerlendirilmelidir."
        ),
        "etymology": "Adların birbirleriyle ilişkisi, kaynak biçimleri ve dilsel kanıtlarla sınanmalıdır.",
        "evidence_status": "Bati Sibirya–Kafkasya çizgisi şematiktir, doğrulanmış rota değildir.",
        "sources": [
            "Golden, Peter B. (1992), An Introduction to the History of the Turkic Peoples. "
            "Genel bağlam için başlangıç kaynağı.",
            "Her iddia için birincil kaynak pasajı, tarih ve modern yorum ayrı alanlarda tutulmalıdır.",
        ],
    },
    "Tauris, Barsil, Tarna, Zagur": {
        "context": (
            "Bu adlar farklı kaynaklarda farklı yazımlarla görülebilir. Uygulamadaki "
            "etiketler, doğrulanmış etnik veya coğrafi eşitleme anlamına gelmez."
        ),
        "etymology": (
            "Yazım benzerliği tek başına etimolojik veya etnik özdeşlik kurmaya yetmez. "
            "Kaynak dili, tarih, aktarım zinciri ve uzman sözlükler kontrol edilmelidir."
        ),
        "evidence_status": (
            "Bu örnek kayıtların bazıları nokta geometrisiyle gösterilir; nokta, "
            "sınır veya yerleşim merkezi için kesin koordinat iddiası değildir."
        ),
        "sources": [
            "Kaynak ekleme kuralı: eser yazarı, tam başlık, yayın yılı, yayınevi, sayfa/pasaj "
            "ve ilgili özgün ad biçimi kaydedilmeden iddia doğrulanmış sayılmamalıdır.",
        ],
    },
}
''',
"modules/data_loader.py": r'''
from __future__ import annotations

import json
from io import BytesIO, StringIO
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import LineString, Point, shape

CRS = "EPSG:4326"

# Başlangıç/bitiş koordinatları görsel örnektir; tarihsel iddia değildir.
DEFAULT_ROUTES = [
    ("1. Ujur / Uygur", 102.0, 47.0, 75.0, 45.0, "#2563eb", "Orkhon -> Jetisu"),
    ("2. Tauris", 34.0, 45.0, 34.0, 45.0, "#059669", "Kirim (şematik nokta)"),
    ("3. Avar", 47.0, 42.0, 19.0, 47.0, "#dc2626", "Kafkasya -> Pannonia (şematik)"),
    ("4. Uauz / Oguz", 60.0, 43.0, 35.0, 39.0, "#d97706", "Aral/Hazar -> Anadolu (şematik)"),
    ("5. Bizal / Barsil", 42.0, 48.0, 42.0, 48.0, "#7c3aed", "Volga-Don / Kuzey Kafkasya (şematik nokta)"),
    ("6. Tarna", 47.5, 42.9, 47.5, 42.9, "#db2777", "Dağıstan / Tarku (şematik nokta)"),
    ("7. Khazar", 48.0, 46.0, 48.0, 46.0, "#4f46e5", "Aşağı Volga / İtil (şematik nokta)"),
    ("8. Janur / Zagur", 39.0, 45.2, 39.0, 45.2, "#0891b2", "Azak / Kuban (şematik nokta)"),
    ("9. Bulgar", 39.0, 46.8, 49.0, 55.0, "#ea580c", "Kuban -> Volga (şematik)"),
    ("10. Sabir / Suvar", 75.0, 55.0, 47.0, 43.0, "#16a34a", "Batı Sibirya -> Kafkasya (şematik)"),
]

REQUIRED_ROUTE_COLUMNS = {
    "nombre", "start_lon", "start_lat", "end_lon", "end_lat"
}


def _validate_coordinates(lon: Any, lat: Any) -> tuple[float, float]:
    try:
        lon_f, lat_f = float(lon), float(lat)
    except (TypeError, ValueError) as exc:
        raise ValueError("Boylam ve enlem sayısal olmalıdır.") from exc
    if not (-180 <= lon_f <= 180):
        raise ValueError(f"Boylam -180 ile 180 arasında olmalı: {lon_f}")
    if not (-90 <= lat_f <= 90):
        raise ValueError(f"Enlem -90 ile 90 arasında olmalı: {lat_f}")
    return lon_f, lat_f


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "name": "nombre",
        "title": "nombre",
        "longitude": "lon",
        "latitude": "lat",
        "start_longitude": "start_lon",
        "start_latitude": "start_lat",
        "end_longitude": "end_lon",
        "end_latitude": "end_lat",
        "description": "descripcion",
    }
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df.rename(columns=rename)


def _geometry_type(geom) -> str:
    return geom.geom_type if geom is not None else "Unknown"


def _make_gdf(records: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    if not records:
        return gpd.GeoDataFrame(
            {
                "nombre": pd.Series(dtype="object"),
                "descripcion": pd.Series(dtype="object"),
                "tipo_geometria": pd.Series(dtype="object"),
                "geometry": gpd.GeoSeries([], crs=CRS),
            },
            geometry="geometry",
            crs=CRS,
        )
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=CRS)
    gdf["nombre"] = gdf["nombre"].fillna("Adsız kayıt").astype(str)
    if "descripcion" not in gdf:
        gdf["descripcion"] = ""
    gdf["descripcion"] = gdf["descripcion"].fillna("").astype(str)
    gdf["tipo_geometria"] = gdf.geometry.map(_geometry_type)
    return gdf


def load_default_data() -> gpd.GeoDataFrame:
    records = []
    for name, slon, slat, elon, elat, color, description in DEFAULT_ROUTES:
        start = _validate_coordinates(slon, slat)
        end = _validate_coordinates(elon, elat)
        geom = Point(start) if start == end else LineString([start, end])
        records.append({
            "nombre": name,
            "descripcion": description,
            "renk": color,
            "veri_durumu": "Şematik örnek; tarihsel rota doğrulaması değildir",
            "start_lon": slon,
            "start_lat": slat,
            "end_lon": elon,
            "end_lat": elat,
            "geometry": geom,
        })
    return _make_gdf(records)


def _read_geojson(raw: bytes) -> gpd.GeoDataFrame:
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Dosya geçerli UTF-8 GeoJSON/JSON değil.") from exc
    if obj.get("type") not in {"FeatureCollection", "Feature"}:
        raise ValueError("GeoJSON kökü FeatureCollection veya Feature olmalıdır.")
    features = obj.get("features", []) if obj["type"] == "FeatureCollection" else [obj]
    records = []
    for i, feature in enumerate(features):
        if feature.get("type") != "Feature":
            raise ValueError(f"{i + 1}. öğe GeoJSON Feature değil.")
        geom_obj = feature.get("geometry")
        if geom_obj is None:
            raise ValueError(f"{i + 1}. özelliğin geometry alanı boş.")
        geom = shape(geom_obj)
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"{i + 1}. özelliğin geometrisi boş veya geçersiz.")
        props = feature.get("properties") or {}
        name = props.get("nombre", props.get("name", props.get("title", f"Kayıt {i + 1}")))
        desc = props.get("descripcion", props.get("description", ""))
        records.append({**props, "nombre": str(name), "descripcion": str(desc), "geometry": geom})
    if not records:
        raise ValueError("GeoJSON içinde hiç Feature bulunamadı.")
    gdf = _make_gdf(records)
    # GeoJSON RFC 7946 koordinatları WGS84 kabul edilir.
    gdf = gdf.set_crs(CRS, allow_override=True)
    return gdf


def _read_csv(raw: bytes) -> gpd.GeoDataFrame:
    try:
        df = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
    except Exception as exc:
        raise ValueError(f"CSV okunamadı: {exc}") from exc
    if df.empty:
        raise ValueError("CSV dosyası boş.")
    df = _normalise_columns(df)

    records = []
    if "geometry_wkt" in df.columns or "wkt" in df.columns:
        geom_col = "geometry_wkt" if "geometry_wkt" in df.columns else "wkt"
        for idx, row in df.iterrows():
            try:
                geom = wkt.loads(str(row[geom_col]))
            except Exception as exc:
                raise ValueError(f"{idx + 2}. satırdaki WKT geometrisi okunamadı.") from exc
            if geom.is_empty or not geom.is_valid:
                raise ValueError(f"{idx + 2}. satırda boş/geçersiz geometri var.")
            records.append({
                **row.drop(labels=[geom_col]).to_dict(),
                "nombre": row.get("nombre", f"Kayıt {idx + 1}"),
                "descripcion": row.get("descripcion", ""),
                "geometry": geom,
            })
    elif REQUIRED_ROUTE_COLUMNS.issubset(df.columns):
        for idx, row in df.iterrows():
            slon, slat = _validate_coordinates(row["start_lon"], row["start_lat"])
            elon, elat = _validate_coordinates(row["end_lon"], row["end_lat"])
            geom = Point((slon, slat)) if (slon, slat) == (elon, elat) else LineString([(slon, slat), (elon, elat)])
            records.append({
                **row.to_dict(),
                "nombre": str(row["nombre"]),
                "descripcion": str(row.get("descripcion", "")),
                "geometry": geom,
            })
    elif {"lon", "lat"}.issubset(df.columns):
        for idx, row in df.iterrows():
            lon, lat = _validate_coordinates(row["lon"], row["lat"])
            records.append({
                **row.to_dict(),
                "nombre": str(row.get("nombre", f"Nokta {idx + 1}")),
                "descripcion": str(row.get("descripcion", "")),
                "geometry": Point((lon, lat)),
            })
    else:
        raise ValueError(
            "CSV şeması tanınmadı. 'start_lon,start_lat,end_lon,end_lat' "
            "veya 'lon,lat' ya da 'geometry_wkt' sütunları gerekli."
        )
    return _make_gdf(records)


def validate_and_load_uploaded_file(uploaded_file):
    """Streamlit UploadedFile benzeri nesneyi doğrular; (GeoDataFrame, mesaj) döndürür."""
    try:
        raw = uploaded_file.getvalue()
        suffix = uploaded_file.name.lower().rsplit(".", 1)[-1] if "." in uploaded_file.name else ""
        if suffix in {"geojson", "json"}:
            gdf = _read_geojson(raw)
        elif suffix == "csv":
            gdf = _read_csv(raw)
        else:
            return None, "Desteklenmeyen dosya türü. GeoJSON, JSON veya CSV kullanın."
        if gdf.crs is None:
            gdf = gdf.set_crs(CRS)
        # Web haritası için yalnızca coğrafi koordinat sistemi kabul edilir.
        if gdf.crs.to_epsg() != 4326:
            return None, f"CRS EPSG:4326 olmalı; bulunan CRS: {gdf.crs}."
        if gdf.geometry.isna().any() or gdf.geometry.is_empty.any():
            return None, "Geometri sütununda boş kayıt var."
        if (~gdf.geometry.is_valid).any():
            return None, "Geometri sütununda geçersiz geometri var."
        return gdf, f"{len(gdf)} kayıt yüklendi ve temel doğrulamadan geçti."
    except Exception as exc:
        return None, f"Dosya doğrulama/yükleme hatası: {exc}"


def export_geojson(gdf: gpd.GeoDataFrame) -> bytes:
    """GeoJSON FeatureCollection olarak dışa aktarır; boş veri de desteklenir."""
    if gdf.empty:
        payload = {"type": "FeatureCollection", "features": []}
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")
    out = gdf.to_crs(CRS) if gdf.crs and gdf.crs.to_epsg() != 4326 else gdf
    return out.to_json(drop_id=True).encode("utf-8")


def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """Öznitelikleri ve geometriyi geometry_wkt sütunuyla dışa aktarır."""
    data = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore")).copy()
    if "geometry" in gdf:
        data["geometry_wkt"] = [
            geom.wkt if geom is not None else "" for geom in gdf.geometry
        ]
    return data.to_csv(index=False).encode("utf-8-sig")
''',
"modules/map_builder.py": r'''
from __future__ import annotations

import folium
import geopandas as gpd
from folium.features import GeoJsonTooltip


TILES = {
    "CartoDB Positron": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap",
}


def create_map(
    gdf: gpd.GeoDataFrame,
    selected_tile: str = "CartoDB Positron",
    show_lines: bool = True,
    show_points: bool = True,
    show_labels: bool = True,
) -> folium.Map:
    if gdf.empty:
        center = [45.0, 45.0]
        fmap = folium.Map(location=center, zoom_start=3, tiles=None)
        if selected_tile in TILES:
            folium.TileLayer(TILES[selected_tile], name=selected_tile, control=True).add_to(fmap)
        folium.Marker(center, tooltip="Filtrelere uyan kayıt yok").add_to(fmap)
        return fmap

    work = gdf.to_crs("EPSG:4326") if gdf.crs and gdf.crs.to_epsg() != 4326 else gdf
    bounds = work.total_bounds  # minx, miny, maxx, maxy
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    fmap = folium.Map(location=center, zoom_start=4, tiles=None, control_scale=True)

    if selected_tile in TILES:
        folium.TileLayer(TILES[selected_tile], name=selected_tile, control=True).add_to(fmap)

    for _, row in work.iterrows():
        geom = row.geometry
        name = str(row.get("nombre", "Adsız kayıt"))
        desc = str(row.get("descripcion", ""))
        color = str(row.get("renk", "#2563eb"))
        properties = {
            "Ad": name,
            "Açıklama": desc,
            "Geometri": geom.geom_type,
            "Veri durumu": str(row.get("veri_durumu", "Kaynak doğrulaması ayrıca yapılmalı")),
        }

        if geom.geom_type in {"LineString", "MultiLineString"} and show_lines:
            folium.GeoJson(
                geom.__geo_interface__,
                name=name,
                style_function=lambda _feature, c=color: {
                    "color": c, "weight": 4, "opacity": 0.85
                },
                tooltip=folium.Tooltip(
                    f"<b>{name}</b><br>{desc}<br><i>Şematik çizgi; doğrulanmış rota değildir.</i>",
                    sticky=True,
                ),
            ).add_to(fmap)

        if geom.geom_type in {"Point", "MultiPoint"} and show_points:
            points = list(geom.geoms) if geom.geom_type == "MultiPoint" else [geom]
            for point in points:
                folium.CircleMarker(
                    location=[point.y, point.x],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_opacity=0.85,
                    tooltip=f"{name}: {desc}",
                ).add_to(fmap)

        if geom.geom_type in {"LineString", "MultiLineString"} and show_points:
            coords = list(geom.coords) if geom.geom_type == "LineString" else []
            if coords:
                for label, coord, symbol in [
                    ("Başlangıç", coords[0], "●"),
                    ("Bitiş", coords[-1], "◆"),
                ]:
                    folium.CircleMarker(
                        location=[coord[1], coord[0]],
                        radius=4,
                        color=color,
                        fill=True,
                        fill_opacity=1,
                        tooltip=f"{name} — {label}",
                    ).add_to(fmap)

        if show_labels and geom.geom_type == "Point":
            folium.Marker(
                [geom.y, geom.x],
                tooltip=name,
                icon=folium.DivIcon(
                    html=(
                        '<div style="font-size:11px;font-weight:600;'
                        f'color:{color};white-space:nowrap">{name}</div>'
                    )
                ),
            ).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    if len(work) == 1:
        fmap.location = center
        fmap.zoom_start = 5
    else:
        fmap.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(20, 20))
    return fmap
''',
"tests/test_data_loader.py": r'''
import io
import json

import pytest

from modules.data_loader import (
    load_default_data,
    validate_and_load_uploaded_file,
    export_geojson,
    export_csv,
)


class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self):
        return self._data


def test_default_data_has_ten_records_and_wgs84():
    gdf = load_default_data()
    assert len(gdf) == 10
    assert gdf.crs.to_epsg() == 4326
    assert set(gdf["tipo_geometria"]) == {"Point", "LineString"}


def test_valid_csv_route_loads():
    data = b"nombre,start_lon,start_lat,end_lon,end_lat\nTest,10,20,11,21\n"
    gdf, message = validate_and_load_uploaded_file(FakeUpload("sample.csv", data))
    assert gdf is not None, message
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "LineString"


def test_invalid_longitude_rejected():
    data = b"nombre,start_lon,start_lat,end_lon,end_lat\nTest,999,20,11,21\n"
    gdf, message = validate_and_load_uploaded_file(FakeUpload("sample.csv", data))
    assert gdf is None
    assert "Boylam" in message or "doğrulama" in message


def test_geojson_loads():
    obj = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Test noktası", "description": "örnek"},
            "geometry": {"type": "Point", "coordinates": [29.0, 41.0]},
        }],
    }
    gdf, message = validate_and_load_uploaded_file(
        FakeUpload("sample.geojson", json.dumps(obj).encode("utf-8"))
    )
    assert gdf is not None, message
    assert gdf.iloc[0]["nombre"] == "Test noktası"
    assert gdf.iloc[0].geometry.x == 29.0


def test_bad_geojson_returns_error_not_exception():
    gdf, message = validate_and_load_uploaded_file(FakeUpload("bad.geojson", b"{bad"))
    assert gdf is None
    assert "hatası" in message.lower()


def test_empty_exports_are_valid():
    empty = load_default_data().iloc[0:0].copy()
    geojson = json.loads(export_geojson(empty).decode("utf-8"))
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"] == []
    csv_data = export_csv(empty).decode("utf-8-sig")
    assert "geometry_wkt" in csv_data
''',
"requirements.txt": r'''
streamlit>=1.40,<2
streamlit-folium>=0.24,<1
folium>=0.18,<1
geopandas>=1.0,<2
shapely>=2.0,<3
pandas>=2.2,<4
pytest>=8,<10
''',
".gitignore": r'''
.venv/
__pycache__/
.pytest_cache/
.streamlit/secrets.toml
*.py[cod]
''',
"README.md": r'''
# Hazar ve Ogur — birleşik Streamlit uygulaması

Folium etkileşimli haritası, filtreler, tarihsel notlar ve GeoJSON/CSV içe-dışa aktarımını tek uygulamada birleştirir.

## 1. Kurulum

Python 3.11 veya 3.12 önerilir. Ubuntu/Debian üzerinde:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
cd hazar_ogur_streamlit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Çalıştırma

```bash
streamlit run app.py
```

Streamlit'in gösterdiği yerel URL'yi tarayıcıda açın (genellikle `http://localhost:8501`).

## 3. Testler

```bash
pytest -q
```

Bu testler veri yükleme/doğrulama ve dışa aktarma işlevlerini kontrol eder; canlı harita sağlayıcısının erişilebilirliğini veya tarihsel iddiaları doğrulamaz.

## 4. Veri biçimleri

### GeoJSON

`FeatureCollection` veya tek `Feature` kabul edilir. Her Feature için geometri boş olmamalı ve geçerli olmalıdır. GeoJSON koordinatları WGS84/EPSG:4326 olarak ele alınır.

### CSV — çizgi / rota benzeri geometri

Gerekli sütunlar:

```csv
nombre,start_lon,start_lat,end_lon,end_lat,descripcion
Örnek kayıt,29.0,41.0,30.0,42.0,"Şematik örnek"
```

Alternatif olarak nokta CSV'si:

```csv
nombre,lon,lat,descripcion
Örnek nokta,29.0,41.0,"Şematik örnek"
```

Daha önce dışa aktarılan CSV'deki `geometry_wkt` sütunu da okunur. Koordinatlar boylam/enlem sınırları açısından denetlenir. CSV içindeki CRS bilgisi otomatik çıkarılamadığından koordinatlar EPSG:4326 kabul edilir; başka CRS'deki koordinatları dönüştürmeden yüklemeyin.

## 5. Kaynak ve tarihsel doğruluk ilkeleri

- Varsayılan çizgiler, tarihsel olarak doğrulanmış göç rotaları değildir; görselleştirme örnekleridir.
- Bir işaretin haritada bulunması, yerleşim merkezi, sınır veya göç rotası için kanıt sayılmaz.
- `HISTORICAL_NOTES` içindeki bibliyografik maddeler genel araştırma başlangıçlarıdır. Her özel iddia için birincil kaynak pasajı, tarih, sayfa ve modern akademik yorum ayrı ayrı eklenmelidir.
- Etimoloji ve etnik özdeşlik, yalnızca ad benzerliğinden çıkarılmamalıdır.
- Uygulama, kaynakların kanıtlamadığı bir rotayı “doğrulanmış” olarak etiketlemez.

## 6. Proje ağacı

```text
hazar_ogur_streamlit/
├── app.py
├── requirements.txt
├── README.md
├── modules/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── history_data.py
│   └── map_builder.py
└── tests/
    └── test_data_loader.py
```

## 7. Sınırlamalar

- Harita altlıkları internet bağlantısı gerektirir.
- GeoJSON dışa aktarımı EPSG:4326 koordinatlarını hedefler.
- Büyük ve karmaşık dosyalar için ek dosya boyutu sınırı, ayrıntılı CRS seçimi ve geometrileri onarma iş akışı eklenmelidir.
- Bu sürüm akademik veri doğrulama sistemi değil; kaynaklandırma ve doğrulama için ihtiyatlı bir görselleştirme iskeletidir.
''',
}

for rel, content in files.items():
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

zip_path = Path("/mnt/data/hazar_ogur_streamlit_project.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in root.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to(root.parent))

print(f"Proje oluşturuldu: {root}")
print(f"ZIP: {zip_path}")
print("Dosyalar:")
for p in sorted(root.rglob("*")):
    if p.is_file():
        print("-", p.relative_to(root))
