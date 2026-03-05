"""
Logica de extracao de dados de vegetacao a partir de PDFs de paisagismo.
Modulo compartilhado entre generate_map.py e api/extract.py (Vercel serverless).
"""

import re
import math

# --- Banco de especies ---

SPECIES = {
    # Arvores
    "PLRU": {"name": "Plumeria rubra", "common": "Jasmim-manga", "type": "arvore"},
    "PHDA": {"name": "Phoenix dactylifera", "common": "Tamareira", "type": "arvore"},
    "NEDE": {"name": "Neodypsis decaryi", "common": "Palmeira-triangulo", "type": "arvore"},
    # Arbustos
    "ALGP": {"name": "Alpinia giant pink shell", "common": "Alpinia rosa gigante", "type": "arbusto"},
    "ALMA": {"name": "Alocasia macrorrhizos", "common": "Alocasia", "type": "arbusto"},
    "ALZE": {"name": "Alpinia zerumbet variegata", "common": "Alpinia variegata", "type": "arbusto"},
    "CALU": {"name": "Calathea lutea", "common": "Calateia charuto", "type": "arbusto"},
    "CHLU": {"name": "Chrysalidocarpus lutescens", "common": "Areca s/ folhas embaixo", "type": "arbusto"},
    "CYLA": {"name": "Cyrtostachys lakka", "common": "Laka", "type": "arbusto"},
    "DRAR": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "DRAV": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "DRAT": {"name": "Dracaena arborea", "common": "Dracena arborea", "type": "arbusto"},
    "HEBI": {"name": "Heliconia bihai", "common": "Heliconia alta", "type": "arbusto"},
    "HIND": {"name": "Heliconia indica", "common": "Heliconia", "type": "arbusto"},
    "PHRO": {"name": "Phoenix roebelinii", "common": "Tamareira ana", "type": "arbusto"},
    "PLRE": {"name": "Pleomele reflexa", "common": "Pleomele", "type": "arbusto"},
    "PLRV": {"name": "Pleomele reflexa variegata", "common": "Pleomele variegata", "type": "arbusto"},
    "THGR": {"name": "Thunbergia grandiflora", "common": "Tumbergia", "type": "arbusto"},
    "ZAFU": {"name": "Zamia furfuracea", "common": "Zamia", "type": "arbusto"},
    "CLFL": {"name": "Clusia fluminensis", "common": "Clusia", "type": "arbusto"},
    "PURE": {"name": "Plumeria rubra", "common": "Plumeria", "type": "arbusto"},
}

# Forracoes: mapeamento cor -> identificacao
FORRACOES_COLOR_MAP = {
    (0.576, 0.400, 0.898): {"label": "PESE(BZ) + CAAR", "codes": ["PESE", "CAAR"]},
    (0.886, 0.976, 0.886): {"label": "ARRE", "codes": ["ARRE"]},
    (0.529, 0.769, 0.667): {"label": "WEPA + PHBI", "codes": ["WEPA", "PHBI"]},
    (0.306, 0.475, 0.651): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.761, 1.000, 0.878): {"label": "WEPA + PHDN", "codes": ["WEPA", "PHDN"]},
    (0.965, 0.886, 0.435): {"label": "CAAR + DIEN", "codes": ["CAAR", "DIEN"]},
    (0.706, 0.682, 0.592): {"label": "CAAR + PHIB", "codes": ["CAAR", "PHIB"]},
    (0.651, 0.788, 0.827): {"label": "EVGL", "codes": ["EVGL"]},
    (1.000, 0.867, 0.820): {"label": "CAAR + PHRN", "codes": ["CAAR", "PHRN"]},
    (0.922, 0.612, 0.259): {"label": "NERV", "codes": ["NERV"]},
    (0.871, 0.616, 0.529): {"label": "WEPA + THWI", "codes": ["WEPA", "THWI"]},
    (0.690, 0.847, 0.690): {"label": "OPJB(VD)", "codes": ["OPJB"]},
    # Cores identificadas pela analise do PDF PINI-PSG-PE-0504-LAZ-R00
    (0.384, 0.443, 0.294): {"label": "MOIR + CAAR", "codes": ["MOIR", "CAAR"]},
    (1.000, 1.000, 0.000): {"label": "MOIR + CAAR", "codes": ["MOIR", "CAAR"]},
    (1.000, 0.000, 0.000): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.867, 0.000, 0.000): {"label": "WEPA + CLFL", "codes": ["WEPA", "CLFL"]},
    (0.867, 0.431, 0.000): {"label": "WEPA + PHBI", "codes": ["WEPA", "PHBI"]},
}

COLOR_PALETTE = [
    "#E91E63", "#4CAF50", "#2196F3", "#FF9800", "#9C27B0",
    "#00BCD4", "#F44336", "#8BC34A", "#3F51B5", "#FFEB3B",
    "#795548", "#607D8B", "#FF5722", "#009688", "#673AB7",
    "#CDDC39", "#03A9F4", "#E040FB", "#76FF03", "#FF6D00",
]


def color_distance(c1, c2):
    """Distancia euclidiana entre duas cores RGB (0-1)."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def match_forracao_color(fill_color):
    """Encontra a forracao mais proxima pela cor de preenchimento."""
    best_match = None
    best_dist = float("inf")
    for ref_color, info in FORRACOES_COLOR_MAP.items():
        dist = color_distance(fill_color, ref_color)
        if dist < best_dist:
            best_dist = dist
            best_match = (ref_color, info)
    if best_dist < 0.15:
        return best_match
    return None


def _extract_text_labels(page, valid_codes):
    """Extrai todos os labels de texto com coordenadas transformadas."""
    mediabox_w = page.mediabox.width
    labels = []
    text_dict = page.get_text("dict")

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                base_code = re.sub(r'\([^)]*\)', '', text).strip()
                if base_code in valid_codes:
                    bbox = span["bbox"]
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    rendered_x = cy
                    rendered_y = mediabox_w - cx
                    labels.append({
                        "code": base_code,
                        "x": round(rendered_x, 1),
                        "y": round(rendered_y, 1),
                    })

    return labels


def extract_positions(page, plant_type):
    """Extrai posicoes dos rotulos de plantas do PDF por tipo (arvores)."""
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    margin_pct = 0.05
    margin_x = rendered_w * margin_pct
    margin_y = rendered_h * margin_pct

    valid_codes = {code for code, info in SPECIES.items() if info["type"] == plant_type}
    labels = _extract_text_labels(page, valid_codes)

    plant_data = {}
    for l in labels:
        if (l["x"] < margin_x or l["x"] > rendered_w - margin_x or
                l["y"] < margin_y or l["y"] > rendered_h - margin_y):
            continue
        code = l["code"]
        if code not in plant_data:
            plant_data[code] = []
        plant_data[code].append({"x": l["x"], "y": l["y"]})

    return plant_data


def extract_shrub_positions(page):
    """Extrai posicoes de arbustos detectando simbolos triangulares no PDF."""
    mediabox_w = page.mediabox.width
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    margin_pct = 0.03
    margin_x = rendered_w * margin_pct
    margin_y = rendered_h * margin_pct

    valid_codes = {code for code, info in SPECIES.items() if info["type"] == "arbusto"}
    labels = _extract_text_labels(page, valid_codes)

    if not labels:
        return {}

    drawings = page.get_drawings()
    triangles = []
    for d in drawings:
        fill = d.get("fill")
        if fill is None:
            continue
        r, g, b = fill
        if not (r < 0.1 and g < 0.1 and b < 0.1):
            continue
        rect = d.get("rect")
        if not rect:
            continue
        w = abs(rect.x1 - rect.x0)
        h = abs(rect.y1 - rect.y0)
        if w > 20 or h > 20 or w < 3 or h < 3:
            continue

        cx_raw = (rect.x0 + rect.x1) / 2
        cy_raw = (rect.y0 + rect.y1) / 2
        tx = cy_raw
        ty = mediabox_w - cx_raw

        if tx < margin_x or tx > rendered_w - margin_x:
            continue
        if ty < margin_y or ty > rendered_h - margin_y:
            continue

        triangles.append({"x": round(tx, 1), "y": round(ty, 1)})

    if not triangles:
        return {}

    def dist(a, b):
        return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)

    plant_data = {}
    for tri in triangles:
        nearest = min(labels, key=lambda l: dist(l, tri))
        d = dist(nearest, tri)
        if d > 500:
            continue
        code = nearest["code"]
        if code not in plant_data:
            plant_data[code] = []
        plant_data[code].append({"x": tri["x"], "y": tri["y"]})

    return plant_data


def extract_ground_cover_areas(page):
    """Extrai areas de forracao do PDF baseado nas cores dos desenhos."""
    mediabox_w = page.mediabox.width
    rendered_w = page.rect.width
    rendered_h = page.rect.height

    drawings = page.get_drawings()
    areas_by_label = {}

    for d in drawings:
        fill = d.get("fill")
        if not fill:
            continue
        if all(c < 0.1 for c in fill):
            continue
        if all(c > 0.95 for c in fill):
            continue

        match = match_forracao_color(fill)
        if not match:
            continue

        ref_color, info = match
        label = info["label"]

        if label not in areas_by_label:
            areas_by_label[label] = {
                "ref_color": ref_color,
                "paths": [],
            }

        raw_points = []
        for item in d.get("items", []):
            op = item[0]
            if op == "l":
                p1, p2 = item[1], item[2]
                raw_points.append((p1.x, p1.y))
                raw_points.append((p2.x, p2.y))
            elif op == "re":
                rect = item[1]
                raw_points.append((rect.x0, rect.y0))
                raw_points.append((rect.x1, rect.y0))
                raw_points.append((rect.x1, rect.y1))
                raw_points.append((rect.x0, rect.y1))
            elif op == "c":
                p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                raw_points.extend([(p1.x, p1.y), (p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y)])
            elif op == "qu":
                for p in item[1:]:
                    raw_points.append((p.x, p.y))

        if not raw_points:
            continue

        path_points = [(ry, mediabox_w - rx) for rx, ry in raw_points]

        if all(px < 0 or px > rendered_w or py < 0 or py > rendered_h
               for px, py in path_points):
            continue

        areas_by_label[label]["paths"].append(path_points)

    return areas_by_label


def assign_colors(data, plant_type):
    """Atribui cores da paleta para cada especie/area detectada."""
    color_map = {}
    if plant_type == "forracao":
        for label in sorted(data.keys()):
            ref_color = data[label]["ref_color"]
            r, g, b = ref_color
            color_map[label] = "#{:02x}{:02x}{:02x}".format(
                int(r * 255), int(g * 255), int(b * 255)
            )
    else:
        for i, code in enumerate(sorted(data.keys())):
            color_map[code] = COLOR_PALETTE[i % len(COLOR_PALETTE)]
    return color_map
