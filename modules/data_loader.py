from __future__ import annotations
import html
import json
import re
from pathlib import Path
import folium
from branca.element import Element


def _safe_color(value: object) -> str:
    color = str(value or "#64748b").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color
    return "#64748b"


def create_map_from_geojson(
    geojson_path: str | Path,
    height: int = 650,
) -> folium.Map:
    """GeoJSON özelliklerinden renkli harita, etiket ve lejant oluşturur."""
    path = Path(geojson_path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("type") != "FeatureCollection":
        raise ValueError("Dosya bir GeoJSON FeatureCollection olmalıdır.")

    features = data.get("features", [])
    if not features:
        raise ValueError("GeoJSON içinde gösterilecek kayıt bulunamadı.")

    bounds = []
    legend_items = []

    fmap = folium.Map(
        location=[45.0, 45.0],
        zoom_start=4,
        tiles="CartoDB positron",
        control_scale=True,
    )

    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not geometry:
            continue

        name = str(props.get("name", "İsimsiz kayıt"))
        description = str(props.get("description", ""))
        color = _safe_color(props.get("color"))

        # GeoJSON koordinatları [longitude, latitude] sırasındadır.
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")

        popup_html = (
            f"<b>{html.escape(name)}</b><br>"
            f"{html.escape(description)}"
        )

        if geom_type == "Point":
            lon, lat = coords
            bounds.append([lat, lon])

            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=name,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(fmap)

            # Nokta etiketini verilen ofsetlerle yerleştir.
            dx = float(props.get("label_dx", 0.5))
            dy = float(props.get("label_dy", 0.5))

            folium.Marker(
                location=[lat + dy, lon + dx],
                icon=folium.DivIcon(
                    html=(
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
                ),
                interactive=False,
            ).add_to(fmap)

        elif geom_type == "LineString":
            # GeoJSON: [lon, lat] -> Folium: [lat, lon]
            latlon = [[lat, lon] for lon, lat in coords]
            bounds.extend(latlon)

            folium.PolyLine(
                locations=latlon,
                color=color,
                weight=4,
                opacity=0.85,
                tooltip=name,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(fmap)

            # Çizgi etiketi, iki uç noktanın orta noktasına yerleştirilir.
            mid = len(latlon) // 2
            lat, lon = latlon[mid]

            dx = float(props.get("label_dx", 0.5))
            dy = float(props.get("label_dy", 0.5))

            folium.Marker(
                location=[lat + dy, lon + dx],
                icon=folium.DivIcon(
                    html=(
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
                ),
                interactive=False,
            ).add_to(fmap)

        else:
            # Desteklenmeyen geometri türlerini sessizce yanlış çizme.
            raise ValueError(
                f"Desteklenmeyen geometri türü: {geom_type!r} ({name})"
            )

        legend_items.append(
            f"""
            <div style="display:flex;align-items:center;gap:8px;margin:6px 0;">
              <span style="
                display:inline-block;
                width:12px;height:12px;
                border-radius:50%;
                background:{color};
                border:1px solid #555;
                flex-shrink:0;
              "></span>
              <span>{html.escape(name)}</span>
            </div>
            """
        )

    if bounds:
        fmap.fit_bounds(bounds, padding=(25, 25))

    legend_html = f"""
    <div style="
      position:fixed;
      bottom:25px;
      left:25px;
      z-index:9999;
      background:rgba(255,255,255,0.96);
      color:#222;
      padding:12px 14px;
      border:1px solid #aaa;
      border-radius:8px;
      box-shadow:0 2px 8px rgba(0,0,0,.25);
      max-height:40vh;
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
    fmap.get_root().header.add_child(
        Element(
            f"<style>html,body{{height:{int(height)}px;}}</style>"
        )
    )

    return fmap
