from __future__ import annotations
import json
from io import BytesIO, StringIO
from pathlib import Path
import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely import wkt

CRS = "EPSG:4326"
DATA_FILE = Path(__file__).resolve().parent / "hazar_ogur.geojson"


def _normalise_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise ValueError("Geçerli bir GeoDataFrame gerekli.")

    gdf = gdf.copy()

    if gdf.empty:
        return gpd.GeoDataFrame(
            {
                "nombre": pd.Series(dtype="object"),
                "descripcion": pd.Series(dtype="object"),
                "grupo": pd.Series(dtype="object"),
                "tipo_geometria": pd.Series(dtype="object"),
                "geometry": gpd.GeoSeries([], crs=CRS),
            },
            geometry="geometry",
            crs=CRS,
        )

    if gdf.crs is None:
        gdf = gdf.set_crs(CRS)
    else:
        gdf = gdf.to_crs(CRS)

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    if gdf.empty:
        raise ValueError("Dosyada geçerli geometri bulunamadı.")

    # GeoJSON alan adlarını uygulamanın kullandığı adlarla eşleştir.
    aliases = {
        "name": "nombre",
        "description": "descripcion",
    }

    for source, target in aliases.items():
        if target not in gdf.columns and source in gdf.columns:
            gdf[target] = gdf[source]

    if "nombre" not in gdf.columns:
        gdf["nombre"] = [
            f"Registro {i + 1}" for i in range(len(gdf))
        ]

    if "descripcion" not in gdf.columns:
        gdf["descripcion"] = ""

    if "grupo" not in gdf.columns:
        gdf["grupo"] = "General"

    gdf["nombre"] = gdf["nombre"].fillna("").astype(str)
    gdf["descripcion"] = gdf["descripcion"].fillna("").astype(str)
    gdf["grupo"] = gdf["grupo"].fillna("General").astype(str)
    gdf["tipo_geometria"] = gdf.geometry.geom_type

    minx, miny, maxx, maxy = gdf.total_bounds
    if minx < -180 or maxx > 180 or miny < -90 or maxy > 90:
        raise ValueError("Koordinatlar EPSG:4326 aralığının dışında.")

    return gdf.reset_index(drop=True)


def load_default_data() -> gpd.GeoDataFrame:
    """Depodaki modules/hazar_ogur.geojson dosyasını yükler."""
    if not DATA_FILE.is_file():
        raise FileNotFoundError(
            f"Varsayılan GeoJSON bulunamadı: {DATA_FILE}"
        )

    try:
        gdf = gpd.read_file(DATA_FILE)
        return _normalise_gdf(gdf)
    except Exception as exc:
        raise ValueError(
            f"Varsayılan GeoJSON yüklenemedi: {exc}"
        ) from exc


def validate_and_load_uploaded_file(
    uploaded_file,
) -> tuple[gpd.GeoDataFrame | None, str]:
    """GeoJSON, JSON veya koordinat/WKT içeren CSV dosyasını yükler."""
    if uploaded_file is None:
        return None, "Dosya seçilmedi."

    filename = uploaded_file.name.lower()
    content = uploaded_file.getvalue()

    if not content:
        return None, "Dosya boş."

    try:
        if filename.endswith((".geojson", ".json")):
            data = json.loads(content.decode("utf-8-sig"))

            if data.get("type") == "FeatureCollection":
                gdf = gpd.read_file(
                    BytesIO(content), driver="GeoJSON"
                )
            elif data.get("type") == "Feature":
                gdf = gpd.GeoDataFrame.from_features(
                    [data], crs=CRS
                )
            else:
                return None, "Geçerli bir GeoJSON Feature veya FeatureCollection gerekli."

        elif filename.endswith(".csv"):
            df = pd.read_csv(StringIO(content.decode("utf-8-sig")))
            df.columns = [str(c).strip().lower() for c in df.columns]

            if df.empty:
                return None, "CSV dosyasında kayıt yok."

            if "geometry_wkt" in df.columns:
                geometries = df["geometry_wkt"].apply(
                    lambda value: (
                        wkt.loads(value)
                        if pd.notna(value) and str(value).strip()
                        else None
                    )
                )
                attributes = df.drop(columns=["geometry_wkt"])
                gdf = gpd.GeoDataFrame(
                    attributes, geometry=geometries, crs=CRS
                )
            else:
                lon_col = next(
                    (c for c in ("lon", "lng", "longitude", "longitud")
                     if c in df.columns),
                    None,
                )
                lat_col = next(
                    (c for c in ("lat", "latitude", "latitud")
                     if c in df.columns),
                    None,
                )

                if lon_col is None or lat_col is None:
                    return None, (
                        "CSV için lon/lat, longitude/latitude veya "
                        "geometry_wkt sütunları gerekli."
                    )

                df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
                df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")

                valid = (
                    df[lon_col].between(-180, 180)
                    & df[lat_col].between(-90, 90)
                )
                if not valid.all():
                    return None, "CSV'de geçersiz koordinatlar var."

                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(
                        df[lon_col], df[lat_col]
                    ),
                    crs=CRS,
                )
        else:
            return None, "Yalnızca .geojson, .json ve .csv desteklenir."

        gdf = _normalise_gdf(gdf)
        return gdf, f"{len(gdf)} kayıt başarıyla yüklendi."

    except Exception as exc:
        return None, f"Dosya işlenemedi: {exc}"


def export_geojson(gdf: gpd.GeoDataFrame) -> bytes:
    """GeoJSON çıktısı üretir."""
    export_gdf = gdf.to_crs(CRS) if gdf.crs else gdf.set_crs(CRS)
    return export_gdf.to_json().encode("utf-8")


def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """Öznitelikleri ve geometriyi WKT biçiminde CSV'ye aktarır."""
    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore")).copy()
    if "geometry" in gdf.columns:
        df["geometry_wkt"] = [
            geom.wkt if geom is not None else ""
            for geom in gdf.geometry
        ]

    return df.to_csv(index=False).encode("utf-8-sig")
