# modules/data_loader.py

import json
import pandas as pd
import geopandas as gpd

def load_default_data(json_data):
    """Carga los datos iniciales por defecto."""
    return gpd.GeoDataFrame.from_features(json_data["features"], crs="EPSG:4326")

def validate_and_load_uploaded_file(uploaded_file):
    """Valida y convierte archivos subidos (.geojson o .csv)."""
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".geojson") or filename.endswith(".json"):
            data = json.load(uploaded_file)
            gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
            
            # Asegurar columnas mínimas
            if "nombre" not in gdf.columns:
                gdf["nombre"] = "Elemento sin nombre"
            if "tipo_geometria" not in gdf.columns:
                gdf["tipo_geometria"] = gdf.geometry.type
            if "grupo" not in gdf.columns:
                gdf["grupo"] = "General"
                
            return gdf, "GeoJSON cargado correctamente."

        elif filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            # Buscar columnas de latitud y longitud
            lat_col = next((col for col in df.columns if col.lower() in ["lat", "latitude", "latitud"]), None)
            lon_col = next((col for col in df.columns if col.lower() in ["lon", "lng", "longitude", "longitud"]), None)
            
            if not lat_col or not lon_col:
                return None, "Error en CSV: No se encontraron columnas de latitud y longitud (ej. 'lat', 'lon')."
            
            gdf = gpd.GeoDataFrame(
                df, 
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), 
                crs="EPSG:4326"
            )
            if "nombre" not in gdf.columns:
                gdf["nombre"] = "Punto CSV"
            if "tipo_geometria" not in gdf.columns:
                gdf["tipo_geometria"] = "Punto"
            if "grupo" not in gdf.columns:
                gdf["grupo"] = "General"

            return gdf, "CSV cargado y convertido a geometrías de punto."

    except Exception as e:
        return None, f"Error al procesar el archivo: {str(e)}"