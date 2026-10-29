# modules/history_data.py

HISTORICAL_NOTES = {
    "Para": {
        "etymology": "Término asociado a divisiones o confederaciones periféricas en fuentes iranias/túrquicas.",
        "context": "Contexto socio-político de grupos esteparios pre-islámicos.",
        "sources": ["Golden, P. B. (1992). An Introduction to the History of the Turkic Peoples."]
    },
    "Hazar (Khazars)": {
        "etymology": "Del túrquico *qaz-* (vagar, nómada). Hipótesis alternativas señalan orígenes de títulos de mando.",
        "context": "Gran Khaganato Jázaro (ss. VII-X) caracterizado por el comercio transcontinental y pluralismo religioso.",
        "sources": ["Dunlop, D. M. (1954). The History of the Jewish Khazars.", "Golden, P. B. (2007). The World of the Khazars."]
    },
    "Ogur (Oghur)": {
        "etymology": "Del proto-túrquico *oq* (flecha / tribu), indicando 'organización de tribus/flechas' (ej. On-Ogur = 10 flechas).",
        "context": "Grupo lingüístico y tribal túrquico r-oriental (búlgaros de la estepa, onoguros, utiguros).",
        "sources": ["Róna-Tas, A. (1999). Hungarians and Europe in the Early Middle Ages."]
    }
}

SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "nombre": "Atil (Capital Jázara)",
                "grupo": "Hazar (Khazars)",
                "tipo_geometria": "Punto Histórico",
                "descripcion": "Centro comercial y capital de la confederación jázara en el delta del Volga."
            },
            "geometry": {
                "type": "Point",
                "coordinates": [48.03, 46.35]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "nombre": "Ruta Comercial del Volga-Don",
                "grupo": "Hazar (Khazars)",
                "tipo_geometria": "Ruta / Corredor",
                "descripcion": "Corredor mercantil clave que conectaba el Jaganato con el Imperio Bizantino y el Califato Abbasí."
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [48.03, 46.35],
                    [44.51, 48.70],
                    [39.72, 47.23]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "nombre": "Región de Asentamiento Onoguro",
                "grupo": "Ogur (Oghur)",
                "tipo_geometria": "Zona / Polígono",
                "descripcion": "Área de influencia de las tribus Ogur al norte del Mar Negro y Kubán."
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [35.0, 45.0],
                    [40.0, 45.0],
                    [42.0, 48.0],
                    [36.0, 48.0],
                    [35.0, 45.0]
                ]]
            }
        }
    ]
}