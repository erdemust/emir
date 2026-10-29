
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
# DOSYA YOLLARI VE SABİTLER
# ============================================================

MODULE_DIR = Path(__file__).resolve().parent
DATA_FILE = MODULE_DIR / "hazar_ogur.geojson"

SUPPORTED_EXTENSIONS = {".geojson", ".json", ".csv"}

DEFAULT_CRS = "EPSG:4326"

DEFAULT_COLOR = "#5470C6"


# ============================================================
# HATA SINIFI
# ============================================================

class DataValidationError(ValueError):
    """Veri dosyası beklenen yapıya sahip olmadığında oluşturulur."""


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def _normalise_column_names(
    df: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Sütun adlarını boşluksuz ve tutarlı hâle getirir."""

    df = df.copy()
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Aynı sütun adının tekrarlanmasını engelle.
    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated()].tolist()
        raise DataValidationError(
            f"Tekrarlanan sütun adları: {duplicates}"
        )

    return df


def _normalise_gdf(
    df: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    GeoDataFrame alanlarını uygulama genelinde tutarlı hâle getirir.

    Korunan temel alanlar:
      name, description, group, color, label, geometry

    Uyumluluk alanları:
      nombre, descripcion, grupo, tipo_geometria
    """

    if not isinstance(df, gpd.GeoDataFrame):
        raise DataValidationError(
            "Girdi bir GeoDataFrame olmalıdır."
        )

    df = _normalise_column_names(df)

    if df.empty:
        raise DataValidationError(
            "Veri dosyası boş; en az bir kayıt gerekli."
        )

    # Farklı kaynaklardan gelen alan adlarını eşleştir.
    aliases = {
        "name": ("nombre", "title", "baslik", "başlık"),
        "description": (
            "descripcion",
            "açıklama",
            "aciklama",
            "details",
        ),
        "group": ("grupo", "category", "kategori"),
        "color": ("renk",),
        "label": ("etiket",),
    }

    for canonical, alternatives in aliases.items():
        if canonical not in df.columns:
            for alternative in alternatives:
                if alternative in df.columns:
                    df = df.rename(
                        columns={alternative: canonical}
                    )
                    break

    # İsim alanı zorunludur.
    if "name" not in df.columns:
        df["name"] = [
            f"Kayıt {i + 1}"
            for i in range(len(df))
        ]

    df["name"] = (
        df["name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    empty_names = df["name"].eq("")
    if empty_names.any():
        df.loc[empty_names, "name"] = [
            f"Kayıt {i + 1}"
            for i in range(int(empty_names.sum()))
        ]

    # İsteğe bağlı alanlar için güvenli varsayılanlar.
    if "description" not in df.columns:
        df["description"] = ""

    if "group" not in df.columns:
        df["group"] = "Sınıflandırılmamış"

    if "color" not in df.columns:
        df["color"] = DEFAULT_COLOR

    if "label" not in df.columns:
        df["label"] = df["name"]

    df["description"] = (
        df["description"].fillna("").astype(str)
    )
    df["group"] = (
        df["group"]
        .fillna("Sınıflandırılmamış")
        .astype(str)
    )
    df["color"] = (
        df["color"]
        .fillna(DEFAULT_COLOR)
        .astype(str)
    )
    df["label"] = (
        df["label"]
        .fillna("")
        .astype(str)
    )

    # GeoJSON geometrileri bulunmalıdır.
    if "geometry" not in df.columns:
        raise DataValidationError(
            "Geometri alanı bulunamadı. "
            "GeoJSON içinde geometry alanı olmalı."
        )

    if df.geometry.isna().any():
        count = int(df.geometry.isna().sum())
        raise DataValidationError(
            f"{count} kayıtta geometri eksik."
        )

    if df.geometry.is_empty.any():
        count = int(df.geometry.is_empty.sum())
        raise DataValidationError(
            f"{count} kayıtta geometri boş."
        )

    if df.crs is None:
        df = df.set_crs(DEFAULT_CRS, allow_override=True)

    # Harita katmanları için uyumluluk sütunları.
    df["nombre"] = df["name"]
    df["descripcion"] = df["description"]
    df["grupo"] = df["group"]
    df["tipo_geometria"] = df.geometry.geom_type

    # Genişlik ve uzunluk gibi geometrik ölçümler için değil,
    # yalnızca coğrafi gösterim için WGS84 kullanılır.
    return df


# ============================================================
# GEOJSON OKUMA
# ============================================================

def _read_geojson_bytes(
    content: bytes,
) -> gpd.GeoDataFrame:
    """GeoJSON içeriğini doğrulayarak GeoDataFrame'e dönüştürür."""

    try:
        document: Any = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataValidationError(
            f"GeoJSON geçerli UTF-8 JSON değil: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise DataValidationError(
            "GeoJSON kök nesnesi bir JSON nesnesi olmalıdır."
        )

    if document.get("type") == "FeatureCollection":
        features = document.get("features")

        if not isinstance(features, list):
            raise DataValidationError(
                "FeatureCollection içinde features dizisi bulunmalıdır."
            )

        for index, feature in enumerate(features):
            if not isinstance(feature, dict):
                raise DataValidationError(
                    f"{index + 1}. özellik geçerli bir nesne değil."
                )

            if feature.get("type") != "Feature":
                raise DataValidationError(
                    f"{index + 1}. özellik type='Feature' olmalıdır."
                )

            geometry = feature.get("geometry")
            if geometry is not None:
                try:
                    shape(geometry)
                except Exception as exc:
                    raise DataValidationError(
                        f"{index + 1}. özelliğin geometrisi geçersiz."
                    ) from exc

        if not features:
            raise DataValidationError(
                "FeatureCollection içinde kayıt bulunamadı."
            )

    elif document.get("type") == "Feature":
        document = {
            "type": "FeatureCollection",
            "features": [document],
        }

    else:
        raise DataValidationError(
            "Dosya bir FeatureCollection veya Feature olmalıdır."
        )

    try:
        return gpd.GeoDataFrame.from_features(
            document["features"],
            crs=DEFAULT_CRS,
        )
    except Exception as exc:
        raise DataValidationError(
            f"GeoJSON GeoDataFrame'e dönüştürülemedi: {exc}"
        ) from exc


def _read_geojson_path(
    path: Path,
) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Varsayılan GeoJSON bulunamadı: {path}"
        )

    if not path.is_file():
        raise DataValidationError(
            f"Veri yolu bir dosya değil: {path}"
        )

    return _read_geojson_bytes(path.read_bytes())


# ============================================================
# CSV OKUMA
# ============================================================

def _read_csv_bytes(
    content: bytes,
) -> gpd.GeoDataFrame:
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise DataValidationError(
            f"CSV dosyası okunamadı: {exc}"
        ) from exc

    df = _normalise_column_names(
        gpd.GeoDataFrame(df)
    )

    # WKT geometri sütunu varsa kullan.
    if "geometry" in df.columns:
        try:
            df["geometry"] = df["geometry"].apply(
                lambda value: (
                    wkt.loads(value)
                    if isinstance(value, str) and value.strip()
                    else value
                )
            )
        except Exception as exc:
            raise DataValidationError(
                f"CSV geometry sütununda geçersiz WKT var: {exc}"
            ) from exc

        return gpd.GeoDataFrame(
            df,
            geometry="geometry",
            crs=DEFAULT_CRS,
        )

    # Alternatif: longitude/latitude veya lon/lat sütunları.
    lower_to_original = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    longitude_key = next(
        (
            lower_to_original[key]
            for key in ("longitude", "lon", "lng", "boylam")
            if key in lower_to_original
        ),
        None,
    )

    latitude_key = next(
        (
            lower_to_original[key]
            for key in ("latitude", "lat", "enlem")
            if key in lower_to_original
        ),
        None,
    )

    if longitude_key is None or latitude_key is None:
        raise DataValidationError(
            "CSV dosyasında geometry (WKT) veya "
            "longitude/latitude sütunları gerekli."
        )

    try:
        longitude = pd.to_numeric(
            df[longitude_key], errors="raise"
        )
        latitude = pd.to_numeric(
            df[latitude_key], errors="raise"
        )
    except Exception as exc:
        raise DataValidationError(
            "Boylam ve enlem sayısal değerlerden oluşmalıdır."
        ) from exc

    if (
        longitude.isna().any()
        or latitude.isna().any()
        or (~longitude.between(-180, 180)).any()
        or (~latitude.between(-90, 90)).any()
    ):
        raise DataValidationError(
            "Koordinatlar geçersiz. Boylam -180..180, "
            "enlem -90..90 aralığında olmalıdır."
        )

    from shapely.geometry import Point

    geometry = [
        Point(float(lon), float(lat))
        for lon, lat in zip(longitude, latitude)
    ]

    return gpd.GeoDataFrame(
        df,
        geometry=geometry,
        crs=DEFAULT_CRS,
    )


# ============================================================
# DIŞA AÇIK YÜKLEME FONKSİYONLARI
# ============================================================

def load_default_data() -> gpd.GeoDataFrame:
    """
    modules/hazar_ogur.geojson dosyasını yükler.

    Argüman almaz. Kullanım:
        gdf = load_default_data()
    """

    try:
        data = _read_geojson_path(DATA_FILE)
        return _normalise_gdf(data)
    except (FileNotFoundError, DataValidationError):
        raise
    except Exception as exc:
        raise DataValidationError(
            f"Varsayılan veri yüklenemedi: {exc}"
        ) from exc


def validate_and_load_uploaded_file(
    uploaded_file,
) -> gpd.GeoDataFrame:
    """
    Streamlit dosya yükleme nesnesini okur.

    Desteklenen dosyalar: .geojson, .json, .csv
    """

    if uploaded_file is None:
        raise DataValidationError(
            "Yüklenecek dosya seçilmedi."
        )

    filename = Path(
        str(getattr(uploaded_file, "name", ""))
    ).name

    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise DataValidationError(
            "Desteklenmeyen dosya biçimi. "
            "GeoJSON, JSON veya CSV kullanın."
        )

    content = uploaded_file.getvalue()

    if not content:
        raise DataValidationError(
            "Yüklenen dosya boş."
        )

    if suffix in {".geojson", ".json"}:
        data = _read_geojson_bytes(content)
    else:
        data = _read_csv_bytes(content)

    return _normalise_gdf(data)


def export_geojson(
    gdf: gpd.GeoDataFrame,
) -> str:
    """GeoDataFrame'i GeoJSON metnine dönüştürür."""

    data = _normalise_gdf(gdf)

    return data.to_json(
        drop_id=False,
        ensure_ascii=False,
    )


def export_csv(
    gdf: gpd.GeoDataFrame,
) -> str:
    """Geometriyi WKT biçiminde içeren CSV üretir."""

    data = _normalise_gdf(gdf).copy()
    data["geometry"] = data.geometry.to_wkt()

    return data.to_csv(index=False)


def get_data_summary(
    gdf: gpd.GeoDataFrame,
) -> dict[str, Any]:
    """Arayüzde kullanılabilecek temel veri özeti."""

    data = _normalise_gdf(gdf)

    return {
        "record_count": int(len(data)),
        "geometry_types": sorted(
            data.geometry.geom_type.dropna().unique().tolist()
        ),
        "groups": sorted(
            data["group"].dropna().unique().tolist()
        ),
        "crs": str(data.crs),
        "columns": data.columns.tolist(),
    }
