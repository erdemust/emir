
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point, shape


MODULE_DIR = Path(__file__).resolve().parent
DATA_FILE = MODULE_DIR / "hazar_ogur.geojson"
DEFAULT_CRS = "EPSG:4326"
DEFAULT_COLOR = "#5470C6"


class DataValidationError(ValueError):
    """Veri doğrulama hatası."""


def _normalise_gdf(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Alan adlarını standartlaştırır ve geometriyi doğrular."""

    if not isinstance(gdf, gpd.GeoDataFrame):
        raise DataValidationError(
            "Veri GeoDataFrame biçiminde olmalıdır."
        )

    gdf = gdf.copy()
    gdf.columns = [str(c).strip() for c in gdf.columns]

    if gdf.columns.duplicated().any():
        raise DataValidationError(
            "Dosyada yinelenen sütun adları var."
        )

    aliases = {
        "name": ("nombre", "title", "baslik", "başlık"),
        "description": ("descripcion", "aciklama", "açıklama"),
        "group": ("grupo", "category", "kategori"),
        "color": ("renk",),
        "label": ("etiket",),
    }

    for canonical, alternatives in aliases.items():
        if canonical not in gdf.columns:
            for alternative in alternatives:
                if alternative in gdf.columns:
                    gdf = gdf.rename(
                        columns={alternative: canonical}
                    )
                    break

    if "geometry" not in gdf.columns:
        raise DataValidationError(
            "Geometri sütunu bulunamadı."
        )

    if gdf.empty:
        raise DataValidationError("Veri kümesi boş.")

    if gdf.geometry.isna().any():
        raise DataValidationError(
            "Bazı kayıtlarda geometri eksik."
        )

    if gdf.geometry.is_empty.any():
        raise DataValidationError(
            "Bazı kayıtlarda geometri boş."
        )

    if gdf.crs is None:
        gdf = gdf.set_crs(DEFAULT_CRS)

    defaults = {
        "name": "",
        "description": "",
        "group": "Sınıflandırılmamış",
        "color": DEFAULT_COLOR,
        "label": "",
    }

    for column, default in defaults.items():
        if column not in gdf.columns:
            gdf[column] = default

    gdf["name"] = gdf["name"].fillna("").astype(str)
    gdf["description"] = (
        gdf["description"].fillna("").astype(str)
    )
    gdf["group"] = (
        gdf["group"].fillna("Sınıflandırılmamış").astype(str)
    )
    gdf["color"] = (
        gdf["color"].fillna(DEFAULT_COLOR).astype(str)
    )
    gdf["label"] = (
        gdf["label"].fillna("").astype(str)
    )

    for index in gdf.index:
        if not gdf.at[index, "name"].strip():
            gdf.at[index, "name"] = f"Kayıt {index + 1}"

    empty_labels = gdf["label"].str.strip().eq("")
    gdf.loc[empty_labels, "label"] = gdf.loc[
        empty_labels, "name"
    ]

    gdf["nombre"] = gdf["name"]
    gdf["descripcion"] = gdf["description"]
    gdf["grupo"] = gdf["group"]
    gdf["tipo_geometria"] = gdf.geometry.geom_type

    return gdf


def _read_geojson(content: bytes) -> gpd.GeoDataFrame:
    try:
        document: Any = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataValidationError(
            f"JSON/GeoJSON okunamadı: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise DataValidationError(
            "GeoJSON kök değeri nesne olmalıdır."
        )

    if document.get("type") == "Feature":
        document = {
            "type": "FeatureCollection",
            "features": [document],
        }

    if document.get("type") != "FeatureCollection":
        raise DataValidationError(
            "GeoJSON Feature veya FeatureCollection olmalıdır."
        )

    features = document.get("features")

    if not isinstance(features, list) or not features:
        raise DataValidationError(
            "GeoJSON içinde features kayıtları bulunamadı."
        )

    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict):
            raise DataValidationError(
                f"{index}. kayıt geçerli bir nesne değil."
            )

        if feature.get("type") != "Feature":
            raise DataValidationError(
                f"{index}. kaydın türü Feature olmalıdır."
            )

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            raise DataValidationError(
                f"{index}. kaydın geometrisi eksik."
            )

        try:
            shape(geometry)
        except Exception as exc:
            raise DataValidationError(
                f"{index}. kaydın geometrisi geçersiz."
            ) from exc

    try:
        gdf = gpd.GeoDataFrame.from_features(
            features,
            crs=DEFAULT_CRS,
        )
    except Exception as exc:
        raise DataValidationError(
            f"GeoJSON GeoDataFrame'e dönüştürülemedi: {exc}"
        ) from exc

    return gdf


def load_default_data() -> gpd.GeoDataFrame:
    """modules/hazar_ogur.geojson dosyasını yükler."""

    if not DATA_FILE.is_file():
        raise FileNotFoundError(
            f"Varsayılan veri dosyası bulunamadı: {DATA_FILE}"
        )

    return _normalise_gdf(
        _read_geojson(DATA_FILE.read_bytes())
    )


def _read_csv(content: bytes) -> gpd.GeoDataFrame:
    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise DataValidationError(
            f"CSV dosyası okunamadı: {exc}"
        ) from exc

    df.columns = [str(c).strip() for c in df.columns]

    if "geometry" in df.columns:
        try:
            geometries = df["geometry"].apply(
                lambda value: (
                    wkt.loads(value)
                    if isinstance(value, str) and value.strip()
                    else None
                )
            )
        except Exception as exc:
            raise DataValidationError(
                f"CSV içindeki WKT geometrisi geçersiz: {exc}"
            ) from exc

        df = df.drop(columns=["geometry"])
        return gpd.GeoDataFrame(
            df,
            geometry=geometries,
            crs=DEFAULT_CRS,
        )

    lookup = {
        str(column).lower(): column
        for column in df.columns
    }

    lon_column = next(
        (
            lookup[key]
            for key in ("longitude", "lon", "lng", "boylam")
            if key in lookup
        ),
        None,
    )
    lat_column = next(
        (
            lookup[key]
            for key in ("latitude", "lat", "enlem")
            if key in lookup
        ),
        None,
    )

    if lon_column is None or lat_column is None:
        raise DataValidationError(
            "CSV içinde geometry (WKT) veya boylam/enlem sütunları gerekli."
        )

    lon = pd.to_numeric(df[lon_column], errors="coerce")
    lat = pd.to_numeric(df[lat_column], errors="coerce")

    if (
        lon.isna().any()
        or lat.isna().any()
        or (~lon.between(-180, 180)).any()
        or (~lat.between(-90, 90)).any()
    ):
        raise DataValidationError(
            "CSV koordinatları geçersiz."
        )

    geometry = [
        Point(float(x), float(y))
        for x, y in zip(lon, lat)
    ]

    return gpd.GeoDataFrame(
        df,
        geometry=geometry,
        crs=DEFAULT_CRS,
    )


def validate_and_load_uploaded_file(uploaded_file) -> gpd.GeoDataFrame:
    """Streamlit tarafından yüklenen GeoJSON, JSON veya CSV dosyasını okur."""

    if uploaded_file is None:
        raise DataValidationError("Dosya seçilmedi.")

    suffix = Path(
        str(getattr(uploaded_file, "name", ""))
    ).suffix.lower()

    if suffix not in {".geojson", ".json", ".csv"}:
        raise DataValidationError(
            "Yalnızca GeoJSON, JSON ve CSV destekleniyor."
        )

    content = uploaded_file.getvalue()

    if not content:
        raise DataValidationError("Yüklenen dosya boş.")

    if suffix in {".geojson", ".json"}:
        gdf = _read_geojson(content)
    else:
        gdf = _read_csv(content)

    return _normalise_gdf(gdf)


def export_geojson(gdf: gpd.GeoDataFrame) -> str:
    """GeoDataFrame'i GeoJSON metnine dönüştürür."""

    data = _normalise_gdf(gdf).to_crs(DEFAULT_CRS)
    return data.to_json(drop_id=False, ensure_ascii=False)


def export_csv(gdf: gpd.GeoDataFrame) -> str:
    """Geometriyi WKT olarak içeren CSV üretir."""

    data = _normalise_gdf(gdf).copy()
    data["geometry"] = data.geometry.to_wkt()
    return data.to_csv(index=False)


def get_data_summary(
    gdf: gpd.GeoDataFrame,
) -> dict[str, Any]:
    """Veri kümesinin özetini döndürür."""

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
