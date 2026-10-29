# modules/map_builder.py

import folium
from folium.plugins import Fullscreen, MiniMap

TILE_PROVIDERS = {
    "CartoDB Positron (Recomendado)": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
    },
    "OpenStreetMap": {
        "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    },
    "Sin Mapa de Fondo": {
        "tiles": "",
        "attr": ""
    }
}

def create_map(gdf, selected_tile="CartoDB Positron (Recomendado)"):
    """Construye un mapa con Folium basado en el GeoDataFrame filtrado."""
    # Coordenadas centradas por defecto en la región póntico-caspia
    center = [46.5, 43.0]
    zoom = 5

    tile_info = TILE_PROVIDERS.get(selected_tile, TILE_PROVIDERS["CartoDB Positron (Recomendado)"])

    if selected_tile == "Sin Mapa de Fondo":
        m = folium.Map(location=center, zoom_start=zoom, tiles=None)
    else:
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles=tile_info["tiles"],
            attr=tile_info["attr"]
        )

    # Añadir elementos geoespaciales
    if not gdf.empty:
        geojson = folium.GeoJson(
            gdf,
            name="Datos Históricos",
            style_function=lambda feature: {
                "fillColor": "#1f77b4" if feature["geometry"]["type"] == "Polygon" else "#ff7f0e",
                "color": "#2ca02c" if feature["geometry"]["type"] == "LineString" else "#1f77b4",
                "weight": 3,
                "fillOpacity": 0.4,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["nombre", "grupo", "tipo_geometria"],
                aliases=["Nombre:", "Grupo:", "Tipo:"],
                localize=True
            ),
            popup=folium.GeoJsonPopup(
                fields=["nombre", "grupo", "tipo_geometria", "descripcion"],
                aliases=["Nombre:", "Grupo:", "Tipo de Geometría:", "Descripción:"],
                labels=True
            )
        )
        geojson.add_to(m)

    # Plugins del mapa
    Fullscreen().add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    return m