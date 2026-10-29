
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from modules.data_loader import (
    DataValidationError,
    export_csv,
    export_geojson,
    get_data_summary,
    load_default_data,
    validate_and_load_uploaded_file,
)


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hazar ve Oğur | Tarihsel-Coğrafi İnceleme",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SABİTLER
# ============================================================

APP_DIR = Path(__file__).resolve().parent
MODULE_DIR = APP_DIR / "modules"
DATA_FILE = MODULE_DIR / "hazar_ogur.geojson"

DEFAULT_COLOR = "#5470C6"


# ============================================================
# OTURUM VE VERİ YÜKLEME
# ============================================================

def initialise_session() -> None:
    """İlk açılışta varsayılan veriyi yükler."""

    if "gdf" not in st.session_state:
        try:
            st.session_state.gdf = load_default_data()
            st.session_state.data_source = str(DATA_FILE)
            st.session_state.load_error = None
        except Exception as exc:
            st.session_state.gdf = None
            st.session_state.data_source = None
            st.session_state.load_error = str(exc)


def reset_data() -> None:
    """Veriyi varsayılan GeoJSON dosyasından yeniden yükler."""

    st.session_state.gdf = load_default_data()
    st.session_state.data_source = str(DATA_FILE)
    st.session_state.load_error = None


initialise_session()


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def get_column(
    df: pd.DataFrame,
    candidates: tuple[str, ...],
) -> str | None:
    """Mevcut sütunlar arasından ilk eşleşeni döndürür."""

    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def display_dataframe(
    gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Geometri sütununu kullanıcı dostu tabloya dönüştürür."""

    table = pd.DataFrame(gdf.drop(columns=["geometry"]).copy())

    # Harita ve CSV dışa aktarma için geometri korunur;
    # ekrandaki tabloda geometri nesnesi gösterilmez.
    return table


def filtered_data(
    gdf: gpd.GeoDataFrame,
    selected_groups: list[str],
    search_text: str,
) -> gpd.GeoDataFrame:
    """Grup ve metin filtrelerini uygular."""

    result = gdf.copy()

    if selected_groups and "group" in result.columns:
        result = result[
            result["group"].isin(selected_groups)
        ]

    query = search_text.strip().casefold()

    if query:
        searchable_columns = [
            column
            for column in (
                "name",
                "description",
                "group",
                "label",
            )
            if column in result.columns
        ]

        if searchable_columns:
            mask = pd.Series(
                False,
                index=result.index,
                dtype=bool,
            )

            for column in searchable_columns:
                mask |= (
                    result[column]
                    .fillna("")
                    .astype(str)
                    .str.casefold()
                    .str.contains(query, regex=False)
                )

            result = result[mask]

    return result


def build_map(
    gdf: gpd.GeoDataFrame,
):
    """
    Folium haritası üretir; karma geometri türlerini, kayıt renklerini,
    etiket ofsetlerini ve otomatik lejantı destekler.
    """
    import html
    import re

    try:
        import folium
        from folium.features import GeoJsonTooltip
        from branca.element import Element
        from streamlit_folium import st_folium
    except ImportError as exc:
        raise RuntimeError(
            "İnteraktif harita için folium, branca ve "
            "streamlit-folium paketleri kurulmalıdır."
        ) from exc

    if gdf.empty:
        raise ValueError("Haritada gösterilecek kayıt yok.")
    if "geometry" not in gdf.columns:
        raise ValueError("Veri kümesinde geometry sütunu bulunamadı.")

    geographic = gdf.copy()
    if geographic.crs is None:
        # GeoJSON koordinatları WGS84'dür; diğer kaynaklar için
        # CRS tahmini yapmak güvenli olmadığından açık hata ver.
        raise ValueError(
            "Koordinat sistemi tanımlanmamış. Veriye doğru CRS (ör. EPSG:4326) atanmalı."
        )

    geographic = geographic.to_crs("EPSG:4326")
    geographic = geographic[
        geographic.geometry.notna() & ~geographic.geometry.is_empty
    ].copy()
    if geographic.empty:
        raise ValueError("Geçerli geometri içeren kayıt bulunamadı.")

    minx, miny, maxx, maxy = geographic.total_bounds
    if not all(pd.notna(v) for v in (minx, miny, maxx, maxy)):
        raise ValueError("Harita sınırları hesaplanamadı.")

    fmap = folium.Map(
        location=[(miny + maxy) / 2, (minx + maxx) / 2],
        zoom_start=4,
        control_scale=True,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    def safe_color(value: object) -> str:
        color = str(value or DEFAULT_COLOR).strip()
        return color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else DEFAULT_COLOR

    def safe_text(value: object, fallback: str = "") -> str:
        if value is None or pd.isna(value):
            return fallback
        return html.escape(str(value))

    legend_items: list[str] = []
    tooltip_fields = [
        field for field in ("name", "description", "group", "period", "source_status")
        if field in geographic.columns
    ]

    for _, row in geographic.iterrows():
        geom = row.geometry
        name_raw = row.get("name", row.get("label", "Kayıt"))
        name = str(name_raw) if pd.notna(name_raw) else "Kayıt"
        description = row.get("description", "")
        color = safe_color(row.get("color", DEFAULT_COLOR))
        name_html = safe_text(name, "Kayıt")
        description_html = safe_text(description)

        popup_html = (
            '<div style="min-width:190px;max-width:320px">'
            f'<div style="font-weight:700;color:{color};margin-bottom:5px">{name_html}</div>'
            f'<div>{description_html}</div>'
            '</div>'
        )
        popup = folium.Popup(popup_html, max_width=350)

        # Her geometri türünü ayrı ele alarak karma FeatureCollection'ı destekle.
        if geom.geom_type in ("Point", "MultiPoint"):
            points = list(geom.geoms) if geom.geom_type == "MultiPoint" else [geom]
            for point in points:
                folium.CircleMarker(
                    location=[point.y, point.x],
                    radius=6,
                    color=color,
                    weight=2,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    tooltip=name,
                    popup=popup,
                ).add_to(fmap)

            # Etiket ofsetleri derece cinsindendir; yalnızca etiketin yerini etkiler.
            point = points[0]
            try:
                dx = float(row.get("label_dx", 0.5))
                dy = float(row.get("label_dy", 0.5))
            except (TypeError, ValueError):
                dx, dy = 0.5, 0.5

            folium.Marker(
                location=[point.y + dy, point.x + dx],
                icon=folium.DivIcon(
                    icon_size=(260, 24),
                    icon_anchor=(0, 12),
                    html=(
                        '<div style="'
                        f'color:{color};font-size:12px;font-weight:700;'
                        'white-space:nowrap;'
                        'text-shadow:-1px -1px 2px white,1px 1px 2px white;'
                        '">'
                        f'{name_html}</div>'
                    ),
                ),
                interactive=False,
            ).add_to(fmap)

        else:
            # GeoJSON özelliğini koruyarak çizgi/poligon biçimlerini çiz.
            feature = {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "description": "" if pd.isna(description) else str(description),
                    "group": str(row.get("group", "")),
                    "color": color,
                },
                "geometry": json.loads(gpd.GeoSeries([geom], crs="EPSG:4326").to_json())[
                    "features"
                ][0]["geometry"],
            }

            tooltip = None
            if tooltip_fields:
                feature["properties"].update({
                    field: (
                        "" if pd.isna(row.get(field)) else str(row.get(field))
                    )
                    for field in tooltip_fields
                })
                tooltip = GeoJsonTooltip(
                    fields=tooltip_fields,
                    aliases=[field.replace("_", " ").title() for field in tooltip_fields],
                    sticky=True,
                    localize=True,
                )

            layer = folium.GeoJson(
                data=feature,
                name=name,
                style_function=lambda feature, c=color: {
                    "color": c,
                    "weight": 3,
                    "opacity": 0.9,
                    "fillColor": c,
                    "fillOpacity": 0.18,
                },
                tooltip=tooltip,
                popup=folium.GeoJsonPopup(
                    fields=["name", "description"],
                    aliases=["Ad", "Açıklama"],
                    labels=True,
                    localize=True,
                ),
            )
            layer.add_to(fmap)

            # Çizgi etiketi yaklaşık orta konuma yerleştirilir.
            if geom.geom_type in ("LineString", "MultiLineString"):
                anchor = geom.interpolate(0.5, normalized=True) if geom.geom_type == "LineString" else geom.centroid
            elif geom.geom_type in ("Polygon", "MultiPolygon"):
                anchor = geom.representative_point()
            else:
                anchor = geom.centroid

            try:
                dx = float(row.get("label_dx", 0.5))
                dy = float(row.get("label_dy", 0.5))
            except (TypeError, ValueError):
                dx, dy = 0.5, 0.5

            folium.Marker(
                location=[anchor.y + dy, anchor.x + dx],
                icon=folium.DivIcon(
                    icon_size=(280, 24),
                    icon_anchor=(0, 12),
                    html=(
                        '<div style="'
                        f'color:{color};font-size:12px;font-weight:700;'
                        'white-space:nowrap;'
                        'text-shadow:-1px -1px 2px white,1px 1px 2px white;'
                        '">'
                        f'{name_html}</div>'
                    ),
                ),
                interactive=False,
            ).add_to(fmap)

        legend_items.append(
            '<div style="display:flex;align-items:center;gap:8px;margin:5px 0;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'border-radius:50%;background:{color};border:1px solid #555;'
            f'flex-shrink:0"></span>'
            f'<span>{name_html}</span></div>'
        )

    legend_html = (
        '<div style="position:fixed;bottom:22px;left:22px;z-index:9999;'
        'background:rgba(255,255,255,.96);color:#222;padding:12px 14px;'
        'border:1px solid #aaa;border-radius:8px;'
        'box-shadow:0 2px 8px rgba(0,0,0,.22);'
        'max-height:38vh;overflow-y:auto;max-width:310px;'
        'font-size:12px;line-height:1.35">'
        '<div style="font-weight:700;margin-bottom:8px">'
        'Hazar–Oğur toplulukları ve güzergâhlar</div>'
        + "".join(legend_items)
        + "</div>"
    )
    fmap.get_root().html.add_child(Element(legend_html))

    # Birden fazla kayıtta tüm veri görünür alana sığdırılır.
    if len(geographic) > 1 and minx != maxx and miny != maxy:
        fmap.fit_bounds([[miny, minx], [maxy, maxx]], padding=(25, 25))
    else:
        fmap.location = [(miny + maxy) / 2, (minx + maxx) / 2]
        fmap.zoom_start = 5

    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap, st_folium


# ============================================================
# BAŞLIK
# ============================================================

st.title("🗺️ Hazar ve Oğur")
st.subheader("Tarihsel-Coğrafi İnceleme")

st.markdown(
    """
    Bu uygulama, tarihsel adlandırmaların ve coğrafi kayıtların
    harita üzerinde incelenmesi için hazırlanmıştır.
    """
)

st.warning(
    "Bilimsel uyarı: Varsayılan GeoJSON içindeki şematik "
    "noktalar, tarihsel göç rotalarının veya kesin yerleşim "
    "alanlarının kanıtı değildir. Tarihsel yorumlar için "
    "birincil kaynak ve akademik yayın doğrulaması gerekir."
)


# ============================================================
# VERİ YÜKLEME HATASI
# ============================================================

if st.session_state.gdf is None:
    st.error(
        "Varsayılan veri yüklenemedi. "
        "Dosya yolunu ve GeoJSON içeriğini kontrol edin."
    )

    if st.session_state.load_error:
        st.code(st.session_state.load_error)

    st.info(
        "Beklenen dosya: modules/hazar_ogur.geojson"
    )

    st.stop()


# ============================================================
# KENAR ÇUBUĞU
# ============================================================

with st.sidebar:
    st.header("⚙️ Kontroller")

    st.caption("Veri kaynağı")
    st.code(
        str(st.session_state.data_source or DATA_FILE),
        language=None,
    )

    st.divider()

    st.subheader("Dosya yükle")

    uploaded_file = st.file_uploader(
        "GeoJSON, JSON veya CSV seç",
        type=["geojson", "json", "csv"],
        help=(
            "Yüklenen veri bu oturumda geçerli veri kümesinin "
            "yerini alır. Sayfa yenilenince varsayılan veri "
            "yeniden yüklenebilir."
        ),
    )

    if st.button(
        "Yüklenen dosyayı uygula",
        use_container_width=True,
        disabled=uploaded_file is None,
    ):
        try:
            new_gdf = validate_and_load_uploaded_file(
                uploaded_file
            )

            st.session_state.gdf = new_gdf
            st.session_state.data_source = uploaded_file.name
            st.session_state.load_error = None

            st.success("Dosya yüklendi.")
            st.rerun()

        except Exception as exc:
            st.error(f"Dosya yüklenemedi: {exc}")

    st.divider()

    if st.button(
        "↩️ Varsayılan verilere dön",
        use_container_width=True,
    ):
        try:
            reset_data()
            st.rerun()
        except Exception as exc:
            st.error(f"Varsayılan veri yüklenemedi: {exc}")

    st.divider()

    st.subheader("Filtreler")

    current_gdf = st.session_state.gdf

    if "group" in current_gdf.columns:
        available_groups = sorted(
            current_gdf["group"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    else:
        available_groups = []

    selected_groups = st.multiselect(
        "Topluluk / kategori",
        options=available_groups,
        default=available_groups,
    )

    search_text = st.text_input(
        "Metin ara",
        placeholder="Örn. Hazar, Bulgar, Oğuz...",
    )

    show_table = st.checkbox(
        "Veri tablosunu göster",
        value=True,
    )

    show_details = st.checkbox(
        "Kayıt ayrıntılarını göster",
        value=True,
    )


# ============================================================
# FİLTRELENMİŞ VERİ
# ============================================================

gdf = st.session_state.gdf

try:
    visible_gdf = filtered_data(
        gdf=gdf,
        selected_groups=selected_groups,
        search_text=search_text,
    )
except Exception as exc:
    st.error(f"Filtreleme hatası: {exc}")
    st.stop()


# ============================================================
# ÖZET METRİKLERİ
# ============================================================

try:
    summary = get_data_summary(gdf)
except Exception as exc:
    st.error(f"Veri özeti oluşturulamadı: {exc}")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Toplam kayıt",
    summary["record_count"],
)

col2.metric(
    "Filtrelenmiş kayıt",
    len(visible_gdf),
)

col3.metric(
    "Geometri türü",
    ", ".join(summary["geometry_types"]) or "—",
)

col4.metric(
    "Kategori sayısı",
    len(summary["groups"]),
)

st.caption(
    f"Koordinat sistemi: {summary['crs']} · "
    f"Veri kaynağı: {st.session_state.data_source}"
)


# ============================================================
# HARİTA
# ============================================================

st.header("📍 Etkileşimli harita")

if visible_gdf.empty:
    st.warning(
        "Seçili filtrelerle eşleşen kayıt bulunamadı."
    )
else:
    try:
        fmap, st_folium = build_map(visible_gdf)

        st_folium(
            fmap,
            use_container_width=True,
            height=600,
            returned_objects=[],
            key="hazar_ogur_map",
        )

    except Exception as exc:
        st.error(
            "Harita oluşturulamadı. requirements.txt "
            "dosyasında folium ve streamlit-folium paketlerini "
            "kontrol edin."
        )
        st.exception(exc)


# ============================================================
# VERİ TABLOSU
# ============================================================

if show_table:
    st.header("📋 Veri kayıtları")

    if visible_gdf.empty:
        st.info("Gösterilecek tablo kaydı yok.")
    else:
        table = display_dataframe(visible_gdf)

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# KAYIT AYRINTILARI
# ============================================================

if show_details:
    st.header("🔎 Kayıt ayrıntıları")

    if visible_gdf.empty:
        st.info("Ayrıntı gösterilecek kayıt yok.")
    else:
        name_column = get_column(
            visible_gdf,
            ("name", "nombre", "label"),
        )

        if name_column is None:
            st.info("Kayıt adı sütunu bulunamadı.")
        else:
            names = visible_gdf[name_column].astype(str).tolist()

            selected_name = st.selectbox(
                "İncelenecek kayıt",
                options=names,
            )

            selected_rows = visible_gdf[
                visible_gdf[name_column].astype(str)
                == selected_name
            ]

            if not selected_rows.empty:
                record = selected_rows.iloc[0]

                st.subheader(selected_name)

                description = record.get(
                    "description",
                    record.get("descripcion", ""),
                )

                if description:
                    st.write(str(description))

                detail_col1, detail_col2 = st.columns(2)

                with detail_col1:
                    st.markdown("**Kategori**")
                    st.write(
                        str(
                            record.get(
                                "group",
                                record.get("grupo", "Belirtilmemiş"),
                            )
                        )
                    )

                    st.markdown("**Dönem**")
                    st.write(
                        str(record.get("period", "Belirtilmemiş"))
                    )

                with detail_col2:
                    st.markdown("**Kaynak durumu**")
                    st.write(
                        str(
                            record.get(
                                "source_status",
                                "Belirtilmemiş",
                            )
                        )
                    )

                    st.markdown("**Geometri türü**")
                    st.write(
                        str(record.geometry.geom_type)
                    )

                with st.expander("Tüm özellikler"):
                    properties = record.drop(
                        labels=["geometry"],
                        errors="ignore",
                    ).to_dict()

                    st.json(properties)


# ============================================================
# DIŞA AKTARMA
# ============================================================

st.header("📥 Veriyi dışa aktar")

if visible_gdf.empty:
    st.info(
        "Dışa aktarılacak kayıt yok. Filtreleri değiştirin."
    )
else:
    export_col1, export_col2 = st.columns(2)

    try:
        geojson_text = export_geojson(visible_gdf)

        with export_col1:
            st.download_button(
                label="GeoJSON indir",
                data=geojson_text.encode("utf-8"),
                file_name="hazar_ogur_filtered.geojson",
                mime="application/geo+json",
                use_container_width=True,
            )

        csv_text = export_csv(visible_gdf)

        with export_col2:
            st.download_button(
                label="CSV indir",
                data=csv_text.encode("utf-8-sig"),
                file_name="hazar_ogur_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(f"Dışa aktarma hatası: {exc}")


# ============================================================
# ALT BİLGİ
# ============================================================

st.divider()

st.caption(
    "Hazar ve Oğur | Tarihsel-Coğrafi İnceleme — "
    "Şematik veriyle araştırma ve görselleştirme prototipi."
)
